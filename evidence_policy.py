"""Conservative action-evidence gate, not a general natural-language proof system.

Rules constrain an advisory interpretation. They never establish actor identity,
field completeness or shipment agreement. Unknown phrasing needs clarification.
"""
import re
from datetime import datetime

VERSION=re.compile(r'(?<![\w-])v[1-9][0-9]{0,2}(?![\w-])')
FLAGS=re.I
PATTERNS={
 'accept':r'\b(?:I|we)\s+(?:(?:explicitly|unconditionally)\s+)?(?:accept|agree\s+to|confirm\s+acceptance)\b|(?:我|我们)(?:明确|无条件)?(?:接受|同意|确认接受)',
 'propose':r'^\s*(?:I|we)\s+(?:propose|request\s+(?:a|the)\s+change)\b|^\s*please\s+(?:change|deliver|reschedule|use)\b|^(?:我|我们)(?:提议|建议|请求变更)|^请(?:更改|变更|改为|送到)',
 'reject':r'\b(?:I|we)\s+(?:explicitly\s+)?(?:reject|decline|do\s+not\s+accept|cannot\s+accept|can\x27t\s+accept|will\s+not\s+accept)\b|(?:我|我们)(?:明确)?(?:拒绝|不接受|不同意)',
 'withdraw':r'\b(?:I|we)\s+(?:hereby\s+)?(?:withdraw|revoke|cancel)\b|(?:我|我们)(?:撤回|撤销|取消)',
 'received':r'\b(?:I|we)\s+(?:have\s+)?(?:received|acknowledge(?:\s+receipt)?|seen|noted)\b|^\s*(?:received|acknowledged|noted|got\s+it)\b|(?:已收到|我收到了|我们收到了|收到)',
}
AMBIGUOUS=re.compile(r'^\s*(?:ok(?:ay)?|yes|sure|fine|好(?:的)?|可以)[.!。！\s]*(?:shipment\b|FS[- ]|v[1-9]|$)',FLAGS)
CONDITION=re.compile(r'\b(?:if|unless|provided|pending|maybe|perhaps|possibly|probably|could|would|once|only|when|until|after|assuming|but|however|except|though|condition|conditional)\b|\bsubject\s+to\b|\bas\s+long\s+as\b|如果|要是|除非|有条件|可能|尚未|还未|还没|待确认|但是|但',FLAGS)
NEGATED_ACCEPT=re.compile(r'\b(?:not|never)\s+(?:yet\s+)?accept(?:ed|ing|ance)?\b|\b(?:no\s+acceptance|don\x27t\s+accept|cannot\s+accept|can\x27t\s+accept)\b|\bnot\s+an\s+acceptance\b|未接受|不接受|没有同意|尚未确认',FLAGS)
UNTRUSTED=re.compile(r'\b(?:forwarded|quoted|system\s+override|ignore\s+(?:all\s+)?(?:previous|prior)|mark\s+all\s+accepted|dispatch\s+now|developer\s+instruction)\b|\b(?:he|she|someone)\s+said\b|["“\x27‘]\s*(?:I|we)\s+|转发|轉發|引用|忽略之前|全部接受|伪造',FLAGS)
DIRECT_ACCEPT=re.compile(r'^\s*(?:I|we)\s+(?:(?:explicitly|unconditionally)\s+)?(?:accept|agree\s+to|confirm\s+acceptance(?:\s+of)?)\s+(?:(?:the|this|that|a|an)\s+)?(?:(?:shipment|delivery|change|request|instruction|version)\b|(?:\(|\[)?\s*v[1-9][0-9]{0,2}\b)|^\s*(?:我|我们)(?:明确|无条件)?(?:接受|确认接受|同意)\s*(?:(?:该|此|本)?(?:变更|指令|请求|版本|交付)|v[1-9][0-9]{0,2}\b)',FLAGS)
ENVELOPE=re.compile(r'\ASent (?P<stamp>[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2}))\. (?P<role>Customer|Dispatcher|Driver):[ \t]*(?P<payload>.+)\Z',re.S)

def source_context(body):
    """Ignore only a validated presentation envelope, never arbitrary context.

    Speaker text is unverified and grants no identity/authority. Quotes must
    retain ALL payload after the prefix; the original body/hash is unchanged.
    """
    match=ENVELOPE.fullmatch(body)
    if match:
        try:
            stamp=datetime.fromisoformat(match['stamp'].replace('Z','+00:00'))
            if stamp.utcoffset() is None:raise ValueError('Timezone required')
        except ValueError:return body,{body}
        payload=match['payload']
        return payload,{body,body[match.start('role'):],payload}
    return body,{body}

def has(kind,text):return re.search(PATTERNS[kind],text,FLAGS) is not None

def assessment(body):
    """Return admissible advisory labels and whether a question is mandatory."""
    body,_=source_context(body)
    versions=set(VERSION.findall(body))
    if len(versions)>1 or UNTRUSTED.search(body):return {'unclear'},True
    accepts=has('accept',body);rejects=has('reject',body);withdraws=has('withdraw',body);proposes=has('propose',body)
    if sum((accepts,rejects,withdraws,proposes))>1:return {'unclear'},True
    if accepts:
        if not versions:return {'unclear'},True
        if DIRECT_ACCEPT.search(body) is None:return {'unclear'},True
        if CONDITION.search(body) or NEGATED_ACCEPT.search(body):return {'unclear','received'} if has('received',body) else {'unclear'},True
        return {'accept'},not versions
    if rejects:return {'reject'},not versions
    if withdraws:return {'withdraw'},not versions
    if has('received',body):return {'received','unclear'},not versions
    if AMBIGUOUS.search(body):return {'received','unclear'},True
    if has('propose',body):return {'propose'},not versions or bool(CONDITION.search(body))
    return {'unclear'},True

def validate_evidence(row,body,questions):
    quote=row['quote'];kind=row['kind'];version=row['version']
    payload,complete_forms=source_context(body)
    action_quote=payload if quote in complete_forms else quote
    # Removing identifiers must leave actual language, not a version token.
    language=VERSION.sub('',action_quote)
    if len(re.findall(r'[A-Za-z\u3400-\u9fff]',language))<2:raise ValueError('Evidence must contain meaningful action or ambiguity language, not only a version')
    versions=set(VERSION.findall(body))
    if len(versions)==1 and version!=next(iter(versions)):raise ValueError('Version must bind the complete source version')
    if len(versions)>1 and (version is not None or kind!='unclear'):raise ValueError('Competing source versions require clarification without choosing one')
    allowed,needs_question=assessment(body)
    if kind not in allowed:raise ValueError('Proposed action lacks explicit supported source language')
    if kind=='accept':
        # Full source prevents an accept fragment from hiding qualifications.
        if quote not in complete_forms or not has('accept',action_quote):raise ValueError('Acceptance requires the complete explicit unqualified source payload, not a selected fragment')
    elif kind in ('propose','reject','withdraw'):
        if not has(kind,action_quote):raise ValueError('Quote must include the source words supporting this action')
    elif kind=='received':
        if not has('received',action_quote) and not AMBIGUOUS.search(action_quote):raise ValueError('Receipt quote lacks acknowledgment language')
    elif quote not in complete_forms:
        raise ValueError('Unclear intent requires the complete source as evidence')
    if (kind=='unclear' or needs_question) and not questions:raise ValueError('Ambiguous or incomplete interpretation needs a clarification question')

def offline_kind(body):
    allowed,question=assessment(body)
    kind=next(iter(allowed)) if len(allowed)==1 else ('received' if has('received',body) else 'unclear')
    if not set(VERSION.findall(body)):question=True
    return kind,question
