"""Regressions for independently reproduced v1 medium-severity defects."""
import copy
import hashlib
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fixtures import events,message,LATE,NEW
from domain import evaluate
from provider import validate,ProviderError


def newer():
    return [message('m16','propose','customer',24,'v4',LATE),message('m17','accept','customer',25,'v4',LATE,'m16'),message('m18','accept','dispatcher',26,'v4',LATE,'m16'),message('m19','accept','driver',27,'v4',LATE,'m16')]

class IndependentReviewFixTests(unittest.TestCase):
    def test_provider_complete_version_tokens_not_substrings_or_attached_words(self):
        for body in ('v10','v100','av1','v1b','v1_x','v1-override','前v1后'):
            src=dict(id='source',body=body,sha256=hashlib.sha256(body.encode()).hexdigest())
            raw=dict(observations=[dict(messageId='source',kind='accept',version='v1',quote=body,confidence=.7,explanation='test')],questions=[])
            with self.subTest(body=body),self.assertRaises(ProviderError):validate(raw,[src])
    def test_exact_complete_version_token_with_punctuation_accepted(self):
        for body in ('I explicitly accept v1.','I explicitly accept (v1).','I explicitly accept [v1].'):
            src=dict(id='source',body=body,sha256=hashlib.sha256(body.encode()).hexdigest())
            raw=dict(observations=[dict(messageId='source',kind='accept',version='v1',quote=body,confidence=.7,explanation='test')],questions=[])
            self.assertEqual(validate(raw,[src])['observations'][0]['version'],'v1')
    def test_fully_confirmed_newer_version_resolves_but_preserves_revoked_ack(self):
        before=evaluate(events());after=evaluate(events()+newer())
        self.assertEqual(before['status'],'CLARIFY');self.assertEqual(after['status'],'ALIGNED');self.assertEqual(after['agreement']['version'],'v4')
        self.assertEqual(after['risks'],[]);self.assertEqual(after['clarifications'],[])
        warning=next(w for w in after['warningHistory'] if w['code']=='REVOKED_ACK')
        self.assertEqual(warning['status'],'resolved');self.assertEqual(warning['evidence'][0]['messageId'],'m15')
        self.assertEqual([e['messageId'] for e in warning['resolution']['evidence']],['m16','m17','m18','m19'])
        self.assertTrue(next(v for v in after['versions'] if v['version']=='v3')['revoked'])
        self.assertIsNone(after['operationalUncertainty']['reroutePerformed'])
    def test_partial_or_invalid_newer_confirmation_cannot_resolve_warning(self):
        for extension in (newer()[:1],newer()[:3]):
            r=evaluate(events()+extension);self.assertNotEqual(r['status'],'ALIGNED');self.assertEqual(r['resolvedWarnings'],[])
        for field,value in [('identityVerified',False),('ref','m999'),('details',NEW)]:
            extension=newer();extension[-1][field]=value
            r=evaluate(events()+extension)
            with self.subTest(field=field):self.assertNotEqual(r['status'],'ALIGNED');self.assertEqual(r['resolvedWarnings'],[])
    def test_received_only_newer_driver_does_not_clear_warning(self):
        extension=newer()[:3]+[message('m19','received','driver',27,'v4',ref='m16')]
        r=evaluate(events()+extension);self.assertNotEqual(r['status'],'ALIGNED');self.assertEqual(r['resolvedWarnings'],[])
    def test_late_revoked_ack_after_new_confirmation_reopens_warning(self):
        late=message('m20','accept','driver',28,'v3',LATE,'m12')
        r=evaluate(events()+newer()+[late]);self.assertEqual(r['status'],'CLARIFY')
        self.assertTrue(any(w['code']=='REVOKED_ACK' and w['status']=='open' and w['evidence'][0]['messageId']=='m20' for w in r['warningHistory']))
    def test_other_identity_uncertainty_not_silently_retired(self):
        unknown=message('unknown','accept','driver',23,'v3',LATE,'m12');unknown['identityVerified']=False
        r=evaluate(events()+[unknown]+newer());self.assertEqual(r['status'],'CLARIFY');self.assertTrue(any(x['code']=='IDENTITY' for x in r['risks']))
    def test_withdrawal_after_changed_instruction_requires_new_full_agreement(self):
        cancelled=events()[:11]+[message('cancel','withdraw','customer',17,'v2',ref='m05')]
        self.assertEqual(evaluate(cancelled)['status'],'CLARIFY')
        recovered=evaluate(cancelled+newer());self.assertEqual(recovered['status'],'ALIGNED')
        self.assertTrue(any(w['code']=='CONFIRMED_WITHDRAWAL' and w['status']=='resolved' for w in recovered['warningHistory']))

if __name__=='__main__':unittest.main(verbosity=2)
