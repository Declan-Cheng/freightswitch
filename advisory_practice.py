"""Authored acceptance practice, never inference or measured model evidence."""
from advisory_intake import bind_proposal


def import_practice(store):
    source = store.save(dict(
        id='authored_accept_practice',
        body='Sent 2026-10-29T12:00:00+00:00. Customer: I accept v6 with no remaining conditions.',
        senderLabel='Authored fictional customer — identity unverified'))
    scripted = dict(messageId=source['id'],kind='accept',confidence=1.0,
        explanation='Authored practice label, not a model prediction. Inspect the source yourself.',question=None)
    proposal = store.ingest(source,bind_proposal(scripted,source),mode='mock',real=False)
    return dict(source=source,proposal=proposal,authoredPractice=True,
        newInferenceCalls=0,agreementChanged=False,
        notice='Authored synthetic practice, not model evidence. Human interpretation only; no agreement or dispatch authority.')


def import_example(store):
    """Authored nonliteral review example, not a recorded model response."""
    source = store.save(dict(
        id='authored_review_example',
        body='Fictional desk note: the revised route v42 is a definite no from this desk.',
        senderLabel='Authored fictional operator — identity unverified'))
    scripted = dict(messageId=source['id'],kind='reject',confidence=1.0,
        explanation='Authored review label, not a model prediction. Inspect the source yourself.',question=None)
    proposal = store.ingest(source,bind_proposal(scripted,source),mode='mock',real=False)
    return dict(source=source,proposal=proposal,authoredExample=True,
        newInferenceCalls=0,agreementChanged=False,
        notice='Authored synthetic example, not model evidence. Human interpretation only; no agreement or dispatch authority.')
