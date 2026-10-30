"""Post-evaluation unverified-advisory review, never shipment authorization.

The original model proposal is immutable evidence of what the producer said.
A human assessment is a separate record, not a correction of model predictions,
not a held-out score, and never a modification of the agreement reducer.
"""
from contextlib import contextmanager
import copy
import json
import re
import sqlite3
from uuid import uuid4
from review_workspace import ReviewStore,now

ID=re.compile(r'[A-Za-z0-9_-]{1,80}')
NONACCEPT_KINDS=frozenset(('propose','received','reject','withdraw','unclear'))
ACCEPT_CONFIRMATIONS=frozenset(('sourceReviewed','conditionsQuotesChecked','localInterpretationOnlyAcknowledged'))
MODES=frozenset(('injected-test','mock','live','recorded-replay'))


def checked_candidate(candidate,source):
    # Import lazily so the isolated store can be imported without initializing
    # any producer or doing inference. The intake recomputes mechanical binding
    # and review eligibility instead of trusting client-supplied flags.
    from advisory_intake import validate_candidate
    return validate_candidate(candidate,source)


class AdvisoryReviewStore(ReviewStore):
    @contextmanager
    def connect(self):
        connection=sqlite3.connect(str(self.path),timeout=5)
        try:
            with connection:yield connection
        finally:connection.close()

    def ingest(self,source,candidate,mode='injected-test',real=False):
        if mode not in MODES or type(real) is not bool:raise ValueError('Explicit advisory provenance required')
        if mode in ('mock','injected-test') and real:raise ValueError('Test/mock provenance cannot claim real inference')
        if mode=='live' and not real:raise ValueError('Live provenance must be explicit')
        if not isinstance(source,dict):raise ValueError('Saved source revision required')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            stored=self.source(source.get('id'),db)
            if any(source.get(key)!=stored[key] for key in ('id','body','senderLabel','sha256','revisionId')):
                raise ValueError('Source changed or differs from the saved revision')
            canonical=checked_candidate(candidate,stored)
            if canonical.get('binding',{}).get('status')!='verified':raise ValueError('Mechanically rejected candidates cannot enter human approval')
            if db.execute('SELECT count(*) FROM proposals').fetchone()[0]>=1000:raise ValueError('Proposal limit reached')
            observation=copy.deepcopy(canonical['observation'])
            question=canonical['modelProposal']['question']
            item=dict(proposalId=str(uuid4()),sourceId=stored['id'],sourceRevision=stored['revisionId'],sourceSHA256=stored['sha256'],
                mode=mode,realInference=real,recordedReplay=mode == 'recorded-replay',
                createdAt=now(),observation=observation,questions=[] if question is None else [question],candidate=copy.deepcopy(canonical),
                reviewEligibility=canonical['reviewEligibility'],proposalOnly=True,semanticVerified=False,modelUnverified=True,
                agreementChanged=False,scope='unverified-advisory',sourceIdentityVerified=False)
            db.execute('INSERT INTO proposals VALUES(?,?,?)',(item['proposalId'],stored['revisionId'],json.dumps(item)))
            return item

    def _request(self,data,assessment=False):
        fields={'actionId','proposalId','sourceRevision','sourceSHA256','version','quote','note',
                'humanKind' if assessment else 'decision'}
        if not isinstance(data,dict):raise ValueError('Exact source-bound review schema required')
        human_accept=assessment and data.get('humanKind')=='accept'
        if human_accept:fields=fields|ACCEPT_CONFIRMATIONS
        if set(data)!=fields:raise ValueError('Exact source-bound review schema required')
        if not isinstance(data['actionId'],str) or not ID.fullmatch(data['actionId']):raise ValueError('Stable review action ID required')
        if not isinstance(data['proposalId'],str) or not 1<=len(data['proposalId'])<=80:raise ValueError('Bounded proposal ID required')
        if not isinstance(data['note'],str) or not data['note'].strip() or len(data['note'])>1000:raise ValueError('Meaningful bounded review reason required')
        if assessment:
            if not isinstance(data['humanKind'],str) or data['humanKind'] not in NONACCEPT_KINDS|{'accept'}:
                raise ValueError('Explicit human interpretation kind required')
            if human_accept:
                if any(data[key] is not True for key in ACCEPT_CONFIRMATIONS):
                    raise ValueError('Human acceptance interpretation requires three explicit true confirmations')
                if len(data['note'].strip())<12:
                    raise ValueError('Human acceptance interpretation requires a reason of 12 to 1000 characters')
        elif data['decision'] not in ('approve','reject','needs_clarification'):
            raise ValueError('Explicit review decision required')
        return json.dumps(data,sort_keys=True)

    def _current_review(self,db,data):
        row=db.execute('SELECT data FROM proposals WHERE id=?',(data['proposalId'],)).fetchone()
        if not row:raise ValueError('Unknown advisory proposal')
        proposal=json.loads(row[0])
        if proposal.get('scope')!='unverified-advisory' or not isinstance(proposal.get('candidate'),dict):
            raise ValueError('Legacy proposals require a new advisory intake before review')
        source=self.source(proposal['sourceId'],db)
        if (data['sourceRevision']!=source['revisionId'] or data['sourceRevision']!=proposal['sourceRevision']
                or data['sourceSHA256']!=source['sha256'] or data['sourceSHA256']!=proposal['sourceSHA256']):
            raise ValueError('Stale source/proposal: review the current revision')
        candidate=checked_candidate(proposal['candidate'],source)
        if candidate.get('binding',{}).get('status')!='verified':raise ValueError('Mechanically rejected candidate cannot be reviewed')
        observation=candidate['observation']
        if proposal['observation']!=observation or proposal['reviewEligibility']!=candidate['reviewEligibility']:
            raise ValueError('Stored proposal differs from recomputed source binding')
        if data['version']!=observation['version'] or data['quote']!=source['body'] or data['quote']!=observation['quote']:
            raise ValueError('Version/complete quote differs from the reviewed source')
        return proposal,source,candidate,observation

    @staticmethod
    def _accept_binding(candidate,observation):
        # Human reporting is a separate interpretation, never model approval.
        # Even that report must name exactly the sole literal source version.
        if observation['version'] is None or candidate['binding'].get('versionOrigin')!='sole-literal-source-token':
            raise ValueError('Human acceptance interpretation requires a sole literal source version')

    def _record(self,data,assessment=False):
        serialized=self._request(data,assessment)
        human_accept=assessment and data['humanKind']=='accept'
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            old=db.execute('SELECT request,data FROM decisions WHERE action=?',(data['actionId'],)).fetchone()
            if old:
                if old[0]!=serialized:raise ValueError('Action ID already used for a different review')
                if human_accept:
                    # Do not return a historical acceptance as if it remains
                    # current: identical retries still rebind the whole source.
                    _,_,candidate,observation=self._current_review(db,data)
                    self._accept_binding(candidate,observation)
                return json.loads(old[1])
            if db.execute('SELECT count(*) FROM decisions').fetchone()[0]>=1000:raise ValueError('Audit limit reached')
            proposal,source,candidate,observation=self._current_review(db,data)
            if human_accept:self._accept_binding(candidate,observation)
            if not assessment and data['decision']=='approve':
                if candidate['reviewEligibility']!='manual-approval-permitted' or observation['kind'] in ('unclear','accept') or observation['version'] is None:
                    raise ValueError('Unverified/high-risk interpretation requires clarification, not model approval')
            item=dict(auditId=str(uuid4()),actionId=data['actionId'],proposalId=proposal['proposalId'],
                sourceId=source['id'],sourceRevision=source['revisionId'],sourceSHA256=source['sha256'],
                version=observation['version'],quote=observation['quote'],kind=observation['kind'],modelKind=observation['kind'],
                decision='human_assessment' if assessment else data['decision'],note=data['note'],createdAt=now(),
                scope='human-assessment-only' if assessment else 'interpretation-only',
                agreementChanged=False,semanticVerified=False,modelUnverified=True,synthetic=True,sourceIdentityVerified=False)
            if assessment:
                item.update(humanKind=data['humanKind'],humanReported=True,reviewerIdentityVerified=False,acceptanceAuthority='none')
            if human_accept:
                item.update({key:True for key in ACCEPT_CONFIRMATIONS})
                item.update(interpretationAuthority='local-reviewer-only',noAuthenticatedCounterpartyAgreement=True)
            db.execute('INSERT INTO decisions(action,request,data) VALUES(?,?,?)',(data['actionId'],serialized,json.dumps(item)))
            return item

    def decide(self,data):return self._record(data)
    def assess(self,data):return self._record(data,assessment=True)

    def snapshot(self):
        result=super().snapshot();current={source['id']:source for source in result['sources']}
        for proposal in result['proposals']:
            proposal['appliesToCurrentSource']=proposal['sourceRevision']==current[proposal['sourceId']]['revisionId']
        result.update(advisoryOnly=True,modelAccuracy=None,semanticApprovalIsShipmentAuthority=False)
        return result
