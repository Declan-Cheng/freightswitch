import copy
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fixtures import events
from provider import Analyzer,ProviderError,MODEL,validate,status

class ProviderTests(unittest.TestCase):
    def setUp(self):self.messages=events()[:2];self.env={'NEBIUS_API_KEY':'FAKE-TEST-ONLY','NEBIUS_MODEL':MODEL,'FREIGHTSWITCH_ALLOW_LIVE':'approved'}
    def raw(self):return dict(observations=[dict(messageId='m02',kind='accept',version='v1',quote=self.messages[1]['body'],confidence=.8,explanation='Advisory only'),dict(messageId='m01',kind='propose',version='v1',quote=self.messages[0]['body'],confidence=.8,explanation='Advisory only')],questions=[])
    def transport(self,payload):
        self.assertNotIn('response_format',payload);self.assertEqual(payload['model'],MODEL)
        return json.dumps(dict(model=MODEL,choices=[dict(finish_reason='stop',message=dict(content=json.dumps(self.raw())))],usage=dict(prompt_tokens=100,completion_tokens=30))).encode()
    def test_mock_is_explicit_never_model_or_state_authority(self):
        r=Analyzer().analyze(self.messages);self.assertEqual(r['mode'],'mock');self.assertFalse(r['realInference']);self.assertIsNone(r['model']);self.assertTrue(r['proposalOnly'])
    def test_live_without_gates_fails_before_transport(self):
        for key in self.env:
            env=dict(self.env);env.pop(key)
            with self.assertRaises(ProviderError):Analyzer().analyze(self.messages,'live',env=env,transport=lambda _:self.fail('Must not call'))
    def test_injected_transport_never_claims_real_inference(self):
        r=Analyzer().analyze(self.messages,'live',self.env,self.transport);self.assertEqual(r['mode'],'injected-test');self.assertFalse(r['realInference']);self.assertEqual(r['usage']['prompt_tokens'],100)
    def test_one_attempt_even_after_error_no_retry_or_fallback(self):
        a=Analyzer();count=[]
        def fail(_):count.append(1);raise RuntimeError('FAKE-TEST-ONLY')
        with self.assertRaises(ProviderError) as error:a.analyze(self.messages,'live',self.env,fail)
        self.assertNotIn('FAKE-TEST-ONLY',str(error.exception))
        with self.assertRaises(ProviderError):a.analyze(self.messages,'live',self.env,fail)
        self.assertEqual(count,[1])
    def test_malformed_unsupported_and_action_output_rejected(self):
        for raw in ['{"observations":[],"observations":[],"questions":[]}','{"observations":NaN,"questions":[]}','not-json',{'observations':[],'questions':[],'dispatch':True}]:
            with self.subTest(raw=raw),self.assertRaises(ProviderError):validate(raw,self.messages)
    def test_citation_confidence_and_version_must_validate(self):
        for key,value in [('messageId','999'),('quote','invented'),('version','v99'),('confidence',float('nan'))]:
            raw=self.raw();raw['observations'][0][key]=value
            with self.subTest(key=key),self.assertRaises(ProviderError):validate(raw,self.messages)
    def test_source_integrity_and_output_size(self):
        bad=copy.deepcopy(self.messages);bad[0]['body']+='changed'
        with self.assertRaises(ProviderError):Analyzer().analyze(bad)
        with self.assertRaises(ProviderError):Analyzer().analyze(self.messages,'live',self.env,lambda _:b'x'*131073)
    def test_truncation_and_wrong_model_fail_closed(self):
        for model,finish in [(MODEL,'length'),('other','stop')]:
            with self.assertRaises(ProviderError):Analyzer().analyze(self.messages,'live',self.env,lambda _:json.dumps(dict(model=model,choices=[dict(finish_reason=finish,message={'content':json.dumps(self.raw())})])).encode())
    def test_actual_live_transport_requires_durable_ledger_before_network(self):
        from unittest.mock import patch
        with patch('urllib.request.build_opener',side_effect=AssertionError('No network')):
            with self.assertRaisesRegex(ProviderError,'ledger'):Analyzer().analyze(self.messages,'live',self.env)
    def test_presence_metadata_never_contains_secret(self):
        self.assertNotIn('FAKE-TEST-ONLY',json.dumps(status(self.env)));self.assertFalse(status(self.env)['accountAvailabilityVerified'])
    def test_rejected_content_keeps_known_usage_but_missing_usage_freezes(self):
        from unittest.mock import patch,MagicMock
        import tempfile
        from datetime import datetime
        from budget import Ledger,BudgetError
        for usage in [dict(prompt_tokens=100,completion_tokens=30,total_tokens=130),None]:
            with self.subTest(usage=usage),tempfile.TemporaryDirectory() as folder:
                ledger=Ledger(Path(folder)/'usage.sqlite',clock=lambda:datetime.fromisoformat('2026-10-28T12:00:00-04:00'))
                response=MagicMock();response.__enter__.return_value.read.return_value=json.dumps(dict(model=MODEL,choices=[dict(finish_reason='stop',message={'content':'malformed'})],usage=usage)).encode()
                with patch('urllib.request.build_opener') as opener:
                    opener.return_value.open.return_value=response
                    with self.assertRaises(ProviderError):Analyzer().analyze(self.messages,'live',self.env,ledger=ledger)
                with ledger.connect() as db:state=db.execute('SELECT status FROM attempts').fetchone()[0]
                self.assertEqual(state,'settled' if usage else 'uncertain')
                if usage:self.assertEqual(ledger.reserve(),2)
                else:
                    with self.assertRaises(BudgetError):ledger.reserve()

if __name__=='__main__':unittest.main(verbosity=2)
