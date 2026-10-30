"""Post-evaluation repair: exact evidence binding != semantic truth or authority.

Every returned item is an UNVERIFIED model suggestion. Unsupported wording is
not silently relabeled. Source-local failures do not erase unrelated candidates.
This module has no network, sender authentication or shipment-write capability.
"""
from collections import Counter
import copy
import math
from provider import ProviderError,parse,sources
from evidence_policy import VERSION,assessment,validate_evidence,CONDITION,NEGATED_ACCEPT,UNTRUSTED

FIELDS={'messageId','kind','confidence','explanation','question'}
KINDS=('propose','accept','received','reject','withdraw','unclear')


def bind_proposal(proposal,source):
    doc=next(iter(sources([source]).values()))
    if not isinstance(proposal,dict) or set(proposal)!=FIELDS:raise ProviderError('Malformed model suggestion fields')
    if proposal['messageId']!=doc['id'] or proposal['kind'] not in KINDS:raise ProviderError('Unknown source or model kind')
    confidence=proposal['confidence'];question=proposal['question']
    if type(confidence) not in (int,float) or not math.isfinite(confidence) or not 0<=confidence<=1:raise ProviderError('Invalid model confidence')
    if not isinstance(proposal['explanation'],str) or len(proposal['explanation'])>200:raise ProviderError('Invalid model explanation')
    if question is not None and (not isinstance(question,str) or not 1<=len(question.strip())<=500 or len(question)>500):raise ProviderError('Invalid model clarification')
    versions=set(VERSION.findall(doc['body']));version=next(iter(versions)) if len(versions)==1 else None
    row={key:proposal[key] for key in ('messageId','kind','confidence','explanation')}
    row.update(version=version,quote=doc['body'],evidenceSHA256=doc['sha256'])
    questions=[] if question is None else [question]
    reasons=[];allowed,needs_question=assessment(doc['body'])
    try:validate_evidence(row,doc['body'],questions)
    except ValueError:reasons.append('literal-policy-does-not-establish-model-interpretation')
    if version is None:reasons.append('missing-or-competing-literal-version')
    if proposal['kind']=='unclear' or needs_question:reasons.append('source-specific-clarification-required')
    # These are lexical caution indicators only, not semantic proofs. They may
    # fire on harmless wording, and absence of a hit is not a safety guarantee.
    if CONDITION.search(doc['body']):reasons.append('conditional-language-caution')
    if NEGATED_ACCEPT.search(doc['body']):reasons.append('nonacceptance-language-caution')
    if UNTRUSTED.search(doc['body']):reasons.append('quoted-or-instruction-language-caution')
    # Crucially, NO model acceptance suggestion is promotable by this intake.
    # A separate human assessment can report an operator's own interpretation,
    # not authenticate a counterparty or alter the authored three-party fixture.
    # A natural-language word list cannot prove unconditional assent.
    if proposal['kind']=='accept':reasons.append('acceptance-needs-independent-confirmation')
    return dict(sourceId=doc['id'],observation=row,modelProposal=copy.deepcopy(proposal),
        binding=dict(status='verified',sourceSHA256=doc['sha256'],sourceSpan=dict(start=0,end=len(doc['body']),unit='unicode-codepoints'),
            quoteOrigin='complete-original-source',versionOrigin='sole-literal-source-token' if version else 'unresolved',identityVerified=False,sourceAuthenticity='not-established'),
        semanticStatus='unverified',reviewEligibility='clarification-required' if reasons else 'manual-approval-permitted',
        reviewReasons=reasons,questions=questions)


def validate_candidate(candidate,source):
    if not isinstance(candidate,dict) or not isinstance(candidate.get('modelProposal'),dict):raise ProviderError('Canonical bound suggestion required')
    canonical=bind_proposal(candidate['modelProposal'],source)
    if candidate!=canonical:raise ProviderError('Suggestion binding or review metadata changed')
    return canonical


def bind_suggestions(raw,messages):
    docs=sources(messages);data=parse(raw) if isinstance(raw,(str,bytes)) else raw
    if not isinstance(data,dict) or set(data)!={'observations'} or not isinstance(data['observations'],list) or len(data['observations'])>30:raise ProviderError('Bounded model observation array required')
    ids=[r.get('messageId') for r in data['observations'] if isinstance(r,dict) and isinstance(r.get('messageId'),str)]
    counts=Counter(ids);by_id={r['messageId']:r for r in data['observations'] if isinstance(r,dict) and isinstance(r.get('messageId'),str)}
    candidates=[];rejections=[];unbound=[]
    for index,row in enumerate(data['observations']):
        ident=row.get('messageId') if isinstance(row,dict) else None
        if not isinstance(ident,str) or ident not in docs:unbound.append(dict(rowIndex=index,reason='unknown-or-missing-source-id'))
    for ident,doc in docs.items():
        if counts[ident]!=1:
            rejections.append(dict(sourceId=ident,sourceSHA256=doc['sha256'],reason='missing-model-observation' if counts[ident]==0 else 'duplicate-model-observation'))
            continue
        try:candidate=bind_proposal(by_id[ident],doc)
        except ProviderError as exc:
            rejections.append(dict(sourceId=ident,sourceSHA256=doc['sha256'],reason=str(exc)));continue
        candidates.append(candidate)
    return dict(candidates=candidates,sourceRejections=rejections,unboundRows=unbound,
        mechanicalBatchStatus='complete' if not rejections and not unbound else 'partial',
        semanticStatus='unverified',interpretationOnly=True,agreementChanged=False,
        classificationContract='source-bound-classification-v1',reviewContract='unverified-source-review-v1',
        notice='Exact source binding is integrity only. These are unverified model suggestions, not validated intent, sender identity, shipment acceptance or dispatch authority.')
