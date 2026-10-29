import copy
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from review_workspace import ReviewStore
from fixtures import events
from domain import evaluate

class ReviewWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'runtime/review.sqlite';self.store=ReviewStore(self.path)
        self.data=dict(id='u01',body='I received, but have NOT accepted shipment FS-1042 / v2. Request m05.',senderLabel='Unverified synthetic driver')
    def tearDown(self):self.tmp.cleanup()
    def proposal(self):
        s=self.store.save(self.data);return s,self.store.propose(s['id'],s['revisionId'],'mock')
    def decision(self,s,p,kind='approve',action='a1'):
        return dict(actionId=action,proposalId=p['proposalId'],sourceRevision=s['revisionId'],sourceSHA256=s['sha256'],decision=kind,version=p['observation']['version'],quote=p['observation']['quote'],note='Receipt only: this does not establish acceptance.')
    def test_approve_interpretation_never_changes_agreement(self):
        before=evaluate(events()[:8]);s,p=self.proposal();entry=self.store.decide(self.decision(s,p))
        self.assertEqual(p['observation']['kind'],'received');self.assertEqual(entry['scope'],'interpretation-only');self.assertFalse(entry['agreementChanged']);self.assertEqual(before,evaluate(events()[:8]))
    def test_all_three_decisions_append_and_survive_restart(self):
        s,p=self.proposal()
        for i,kind in enumerate(('approve','reject','needs_clarification')):self.store.decide(self.decision(s,p,kind,'a'+str(i)))
        audit=ReviewStore(self.path).snapshot()['audit'];self.assertEqual(len(audit),3);self.assertTrue(all(a['appliesToCurrentSource'] for a in audit))
        self.assertEqual(self.path.stat().st_mode&0o777,0o600)
    def test_repeat_action_idempotent_and_conflict_rejected(self):
        s,p=self.proposal();data=self.decision(s,p);first=self.store.decide(data);self.assertEqual(first,self.store.decide(data));self.assertEqual(len(self.store.snapshot()['audit']),1)
        changed={**data,'decision':'reject'}
        with self.assertRaises(ValueError):self.store.decide(changed)
    def test_edit_retains_original_and_marks_decision_stale(self):
        s,p=self.proposal();self.store.decide(self.decision(s,p));new=self.store.save({**self.data,'body':self.data['body'].replace('v2','v10')})
        self.assertNotEqual(s['revisionId'],new['revisionId']);snapshot=self.store.snapshot();self.assertEqual(snapshot['sourceHistory'][0]['body'],self.data['body']);self.assertFalse(snapshot['audit'][0]['appliesToCurrentSource'])
        with self.assertRaises(ValueError):self.store.decide(self.decision(s,p,action='a2'))
        with self.assertRaises(ValueError):self.store.propose(s['id'],s['revisionId'],'mock')
    def test_sender_change_also_invalidates_revision_even_when_body_hash_matches(self):
        s,p=self.proposal();new=self.store.save({**self.data,'senderLabel':'Different unverified sender'});self.assertEqual(s['sha256'],new['sha256'])
        with self.assertRaises(ValueError):self.store.decide(self.decision(s,p))
    def test_changed_quote_version_hash_or_revision_cannot_be_approved(self):
        s,p=self.proposal()
        for field,value in [('quote','invented'),('version','v1'),('sourceSHA256','wrong'),('sourceRevision','old')]:
            with self.subTest(field=field),self.assertRaises(ValueError):self.store.decide({**self.decision(s,p),field:value})
        self.assertEqual(self.store.snapshot()['audit'],[])
    def test_unclear_and_absent_version_need_clarification(self):
        self.data['body']='Tomorrow at 3, maybe.';s,p=self.proposal()
        self.assertIsNone(p['observation']['version'])
        with self.assertRaises(ValueError):self.store.decide(self.decision(s,p))
        self.assertEqual(self.store.decide(self.decision(s,p,'needs_clarification'))['decision'],'needs_clarification')
    def test_replay_exact_sources_and_no_live_or_provider_call(self):
        from unittest.mock import patch
        with patch('provider.Analyzer.analyze',side_effect=AssertionError('No model call')):
            result=self.store.import_recorded()
        self.assertTrue(result['proposal']['realInference']);self.assertTrue(result['proposal']['recordedReplay']);self.assertEqual(result['proposal']['observation']['kind'],'received')
        with self.assertRaises(ValueError):self.store.propose(result['source']['id'],result['source']['revisionId'],'live')
    def test_identical_save_reuses_revision_and_source_bounds_hold(self):
        s=self.store.save(self.data);self.assertEqual(s,self.store.save(self.data))
        for changes in ({'id':'../x'},{'body':''},{'body':'x'*12001},{'senderLabel':''}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):self.store.save({**self.data,**changes})
        self.assertEqual(len(self.store.snapshot()['sourceHistory']),1)

if __name__=='__main__':unittest.main(verbosity=2)
