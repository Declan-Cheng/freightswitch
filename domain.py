"""Evidence-linked typed event reducer. No model, message sending or dispatch authority.

Fixtures are manually authored typed messages; arbitrary natural language is not
silently parsed as fact. Source hashes/literal references are structural checks,
not authentication or proof that a human meant what a model inferred.
"""
import copy
import hashlib
import json
import re
from datetime import datetime
from fixtures import SHIPMENT, PARTIES

KINDS={'propose','accept','received','reject','withdraw'}
ID=re.compile(r'^[A-Za-z0-9_-]{1,80}$')


def stamp(value):
    if not isinstance(value,str):raise ValueError('Missing timestamp')
    result=datetime.fromisoformat(value)
    if result.utcoffset() is None:raise ValueError('Timezone required')
    return result


def proof(msg):
    return dict(messageId=msg['id'],sha256=msg['sha256'],quote=msg['body'])


def evaluate(messages):
    if not isinstance(messages,list) or len(messages)>150:raise ValueError('Provide at most150 messages')
    issues=[];evidence=[];by_id={};invalid=set();rows=[];versions={};order=[]
    def issue(code,text,m=None,question=None):
        item=dict(code=code,text=text,question=question,evidence=[proof(m)] if m and isinstance(m.get('body'),str) and isinstance(m.get('sha256'),str) else [],version=m.get('version') if m else None,sentAt=m.get('sentAt') if m else None)
        if item not in issues:issues.append(item)
    for original in messages:
        if not isinstance(original,dict):issue('INVALID_MESSAGE','A message envelope is invalid.',question='Provide the original message and sender.');continue
        m=copy.deepcopy(original);ident=m.get('id')
        if not isinstance(ident,str) or not ID.fullmatch(ident):issue('INVALID_ID','A stable message ID is missing.',question='Which original message is this?');continue
        if ident in by_id:
            if by_id[ident]!=m:invalid.add(ident);issue('DUPLICATE_CONFLICT','The same message ID has conflicting content.',m,'Which original content belongs to '+ident+'?')
        else:by_id[ident]=m
    for ident,m in by_id.items():
        if ident in invalid:continue
        if m.get('shipment')!=SHIPMENT:issue('SHIPMENT_REFERENCE','Shipment identity is unresolved.',m,'Does this message refer to '+SHIPMENT+'?');continue
        if m.get('party') not in PARTIES or m.get('identityVerified') is not True:
            issue('IDENTITY','Sender identity is not verified.',m,'Who sent '+ident+': customer, dispatcher or driver?');continue
        body=m.get('body');sha=m.get('sha256')
        if not isinstance(body,str) or len(body)>12000 or hashlib.sha256(body.encode()).hexdigest()!=sha:
            issue('SOURCE_INTEGRITY','Source body/hash is missing or changed.',question='Provide the unchanged source message '+ident+'.');continue
        if m.get('kind') not in KINDS:issue('INTENT','Message intent is unresolved.',m,'Is this a proposal, acceptance, rejection, receipt or withdrawal?');continue
        version=m.get('version')
        if not isinstance(version,str) or not re.fullmatch(r'v[1-9][0-9]{0,2}',version) or SHIPMENT not in body or not re.search(r'(?<![A-Za-z0-9])'+re.escape(version)+r'(?![A-Za-z0-9])',body):
            issue('VERSION_REFERENCE','A shipment/version reference is incomplete.',m,'Which exact request version does '+ident+' address?');continue
        try:sent=stamp(m.get('sentAt'))
        except (ValueError,TypeError,OverflowError):issue('TIME','Message time or timezone is ambiguous.',m,'What is the sent time and timezone for '+ident+'?');continue
        # Authority-changing typed claims must match the supported fixture
        # grammar in their original source, not merely mention desired values.
        verbs={'propose':'I propose','accept':'I explicitly accept','reject':'I reject','withdraw':'I withdraw'}
        if m['kind'] in verbs:
            expected=verbs[m['kind']]+' shipment '+SHIPMENT+' / '+version+'.'
            if m.get('ref'):expected+=' Request '+str(m['ref'])+'.'
            if m['kind'] in ('propose','accept') and isinstance(m.get('details'),dict) and set(m['details'])=={'address','time'}:
                expected+=' Deliver to '+str(m['details']['address'])+' at '+str(m['details']['time'])+'.'
            if m.get('supersedes'):expected+=' This supersedes message '+str(m['supersedes'])+'.'
            if body!=expected:
                issue('INTENT_EVIDENCE','Authority claim is outside the reviewed literal source grammar.',m,'Does the sender explicitly '+m['kind']+' the exact request, without qualifications?');continue
        m['_sent']=sent;rows.append(m);evidence.append(proof(m))
    rows.sort(key=lambda m:(m['_sent'],m['id']))
    evidence=[proof(m) for m in rows]
    # Simultaneous state-changing messages are not ordered by an arbitrary ID.
    groups={}
    for m in rows:
        if m['kind']!='received':groups.setdefault((m['_sent'],m['version'],m['party']),[]).append(m)
    simultaneous=set()
    for group in groups.values():
        if len(group)>1:
            for m in group:simultaneous.add(m['id']);issue('AMBIGUOUS_ORDER','Simultaneous statements cannot be safely ordered.',m,'Which statement supersedes the other at this time?')
    agreement=None;initial=None;latest_ack={};transitions=[]
    for m in rows:
        if m['id'] in simultaneous:continue
        kind=m['kind'];v=m['version'];entry=versions.get(v)
        if kind=='propose':
            if m['party']!='customer':issue('PROPOSER','Only the verified customer can propose this demo shipment change.',m,'Can the customer confirm this requested change?');continue
            if entry:issue('VERSION_CONFLICT','A version has more than one proposal.',m,'Which proposal is the canonical '+v+'?');continue
            details=m.get('details')
            if not isinstance(details,dict) or set(details)!={'address','time'} or not isinstance(details.get('address'),str) or not details['address'].strip() or len(details['address'])>300:
                issue('INCOMPLETE_INSTRUCTION','A proposed instruction is incomplete.',m,'What are the exact warehouse/gate and delivery time with timezone?');continue
            try:delivery=stamp(details['time'])
            except (ValueError,TypeError,OverflowError):issue('DELIVERY_TIME','Delivery time needs an explicit timezone.',m,'What is the delivery time including date and timezone?');continue
            if details['address'] not in m['body'] or details['time'] not in m['body']:
                issue('UNSUPPORTED_DETAILS','Typed address/time are not literal in their source.',m,'Confirm the exact address and time in the source message.');continue
            if delivery<=m['_sent']:issue('EXPIRED_PROPOSAL','Delivery time is already past at proposal time.',m,'What future delivery time is intended?');continue
            if order and int(v[1:])<=int(order[-1][1:]):issue('STALE_PROPOSAL','A newly sent proposal has an older version number.',m,'Is this a new request version or a reply to the old request?');continue
            entry=dict(version=v,details=copy.deepcopy(details),proposal=proof(m),sentAt=m['sentAt'],revoked=False,withdrawal=None,
                       parties={p:dict(status='unconfirmed',evidence=[]) for p in PARTIES},conflicts=[])
            versions[v]=entry;order.append(v)
            continue
        if not entry or m.get('ref')!=entry['proposal']['messageId'] or not isinstance(m.get('ref'),str) or not re.search(r'(?<![A-Za-z0-9_-])'+re.escape(m['ref'])+r'(?![A-Za-z0-9_-])',m['body']):
            issue('REQUEST_REFERENCE','The exact earlier request is not established.',m,'Which original request message does '+m['id']+' answer?');continue
        if m['_sent']<=stamp(entry['sentAt']):issue('CAUSAL_TIME','A response does not occur after its proposal.',m,'Confirm the response timestamp and request reference.');continue
        if kind=='withdraw':
            if m['party']!='customer':issue('WITHDRAWAL_AUTHORITY','Withdrawal needs the requesting customer.',m,'Did the customer withdraw this request?');continue
            entry['revoked']=True;entry['withdrawal']=proof(m)
            if agreement==v:issue('CONFIRMED_WITHDRAWAL','A fully confirmed instruction was withdrawn; no automatic rollback is safe.',m,'Which replacement instruction should all three parties confirm?')
            elif any(latest_ack.get(p,{}).get('version')==v for p in ('driver','dispatcher')):
                issue('WITHDRAWN_AFTER_ACK','A party had accepted the now-withdrawn instruction; old instructions cannot be silently restored.',m,'Which valid instruction should the affected party explicitly reconfirm?')
            transitions.append(dict(type='withdrawn',version=v,evidence=[proof(m)]));continue
        party=m['party'];current=entry['parties'][party]
        if kind=='received':
            if current['status']=='unconfirmed':entry['parties'][party]=dict(status='received',evidence=[proof(m)])
            continue
        if entry['revoked']:
            issue('REVOKED_ACK','A reply refers to a withdrawn request and cannot revive it.',m,'Please confirm the current valid instruction, not withdrawn '+v+'.');continue
        if kind=='accept':
            if m.get('details')!=entry['details'] or any(value not in m['body'] for value in entry['details'].values()):
                issue('STALE_INSTRUCTION','The response does not confirm the exact proposed address and time.',m,'Does '+party+' accept '+v+' at '+entry['details']['address']+' / '+entry['details']['time']+'?');continue
        new='accepted' if kind=='accept' else 'rejected'
        if current['status'] in ('accepted','rejected','conflict') and current['status']!=new:
            previous=current['evidence'][-1]['messageId']
            if m.get('supersedes')!=previous or previous not in m['body']:
                entry['parties'][party]=dict(status='conflict',evidence=current['evidence']+[proof(m)])
                entry['conflicts'].append(dict(party=party,messageId=m['id']))
                continue
        entry['parties'][party]=dict(status=new,evidence=[proof(m)])
        if new=='accepted':latest_ack[party]=dict(version=v,evidence=[proof(m)],details=copy.deepcopy(entry['details']))
        # A delayed acknowledgment of an older version cannot replace the latest
        # proposed change. It remains evidence of an old instruction in use.
        if v==order[-1] and all(p['status']=='accepted' for p in entry['parties'].values()):
            if agreement!=v:transitions.append(dict(type='confirmed',version=v,evidence=[e for p in entry['parties'].values() for e in p['evidence']]))
            agreement=v
            if initial is None:initial=v
    active=next((v for v in reversed(order) if not versions[v]['revoked']),None)
    current=versions.get(active);risks=[]
    if not current:issue('NO_INSTRUCTION','No complete valid instruction is established.',question='Provide the original shipment instruction and three party confirmations.')
    if current:
        for party,response in current['parties'].items():
            if response['status']!='accepted':
                last=latest_ack.get(party)
                risks.append(dict(code='PARTY_'+response['status'].upper(),party=party,text=PARTIES[party]+' has '+response['status']+' '+active+'.',
                                  evidence=[current['proposal']]+response['evidence']+(last['evidence'] if last and last['version']!=active else [])))
            if party in latest_ack and latest_ack[party]['version']!=active:
                risks.append(dict(code='STALE_VERSION',party=party,text=PARTIES[party]+' last explicitly confirmed '+latest_ack[party]['version']+'; current request is '+active+'.',evidence=[current['proposal']]+latest_ack[party]['evidence']))
        for v,entry in versions.items():
            for party,response in entry['parties'].items():
                if response['status']=='conflict':
                    risks.append(dict(code='CONTRADICTION',party=party,text=PARTIES[party]+' has contradictory responses for '+v+'.',evidence=response['evidence']))
                    issue('CONTRADICTION','Acceptance and rejection conflict for '+party+' / '+v+'.',question='Which response supersedes the other for '+party+' / '+v+'?')
    # Retire only source-bound historical withdrawal warnings after a strictly
    # newer, later proposal is explicitly accepted by every party. Keep the
    # original warning and exact resolution evidence in the audit history.
    warning_history=[];open_issues=[]
    fully_current=bool(current and not current['revoked'] and all(p['status']=='accepted' for p in current['parties'].values()) and all(latest_ack.get(p,{}).get('version')==active for p in PARTIES))
    for item in issues:
        archived=copy.deepcopy(item);archived['status']='open'
        if (fully_current and item['code'] in ('REVOKED_ACK','CONFIRMED_WITHDRAWAL','WITHDRAWN_AFTER_ACK')
                and item['version'] in versions and int(active[1:])>int(item['version'][1:])
                and item['sentAt'] and stamp(current['sentAt'])>stamp(item['sentAt'])):
            archived['status']='resolved'
            archived['resolution']=dict(version=active,rule='Strictly newer proposal after warning; all three explicitly accept exact complete instruction',
                                        evidence=[current['proposal']]+[ev for response in current['parties'].values() for ev in response['evidence']])
        else:open_issues.append(item)
        warning_history.append(archived)
    issues=open_issues
    for item in issues:risks.append(dict(code=item['code'],party=None,text=item['text'],evidence=item['evidence']))
    # Revoked/latest instruction uncertainty must remain visible even when the
    # previous request has unanimous historical acceptance.
    cleared=bool(current and all(p['status']=='accepted' for p in current['parties'].values()) and not risks)
    return dict(shipment=SHIPMENT,synthetic=True,interpretation='Manually reviewed synthetic typed events; deterministic authority reducer. No live AI.',
                status='ALIGNED' if cleared else ('CLARIFY' if issues else 'AT_RISK'),activeVersion=active,
                agreement=copy.deepcopy(versions.get(agreement)),originalAgreement=copy.deepcopy(versions.get(initial)),
                proposed=copy.deepcopy(current),versions=[copy.deepcopy(versions[v]) for v in order],latestAcknowledgments=latest_ack,
                warningHistory=warning_history,resolvedWarnings=[w for w in warning_history if w['status']=='resolved'],
                risks=risks,clarifications=[i['question'] for i in issues if i['question']],transitions=transitions,evidence=evidence,
                latestRequestStatus=('withdrawn' if order and versions[order[-1]]['revoked'] else 'confirmed' if cleared else 'pending-or-disputed'),
                fieldAcceptance={p:{f:current['parties'][p]['status'] for f in ('address','time')} for p in PARTIES} if current else {},
                operationalUncertainty=dict(physicalExecutionVerified=False,physicalLocation=None,reroutePerformed=None,instructionRiskOpen=not cleared,notice='Message agreement only; no telemetry or physical-execution evidence is present.'),
                counts=dict(uniqueMessages=len(by_id),acceptedMessages=len(rows),duplicatesIgnored=len(messages)-len(by_id)))
