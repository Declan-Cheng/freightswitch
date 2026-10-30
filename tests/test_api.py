import json
from pathlib import Path
import sys
import threading
import tempfile
import unittest
import urllib.request
import urllib.error
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from http.server import ThreadingHTTPServer
from server import Handler
from fixtures import events

class LocalAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler);cls.base='http://127.0.0.1:'+str(cls.server.server_port)
        cls.temp=tempfile.TemporaryDirectory();cls.server.review_path=Path(cls.temp.name)/'review.sqlite'
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join();cls.temp.cleanup()
    def req(self,path,data=None,headers=None):
        request=urllib.request.Request(self.base+path,data=json.dumps(data).encode() if data is not None else None,headers=headers or {})
        try:
            with urllib.request.urlopen(request,timeout=5) as r:return r.status,r.read(),r.headers
        except urllib.error.HTTPError as e:return e.code,e.read(),e.headers
    def test_actual_http_risk_then_explicit_alignment(self):
        a=json.loads(self.req('/api/state?count=10')[1]);b=json.loads(self.req('/api/state?count=11')[1])
        self.assertEqual(a['state']['status'],'AT_RISK');self.assertEqual(b['state']['status'],'ALIGNED')
    def test_live_route_blocked_and_mock_cannot_update_agreement(self):
        code,body,_=self.req('/api/analyze',{'mode':'live','messages':events()[:8]});self.assertEqual(code,403)
        code,body,_=self.req('/api/analyze',{'mode':'mock','messages':events()[:8]});self.assertEqual(code,200);self.assertFalse(json.loads(body)['realInference'])
        self.assertEqual(json.loads(self.req('/api/state?count=8')[1])['state']['status'],'AT_RISK')
    def test_custom_evaluation_ambiguity_does_not_mutate_fixture(self):
        m=events()[:11];m[-1]['identityVerified']=False
        code,body,_=self.req('/api/evaluate',{'messages':m});self.assertEqual(code,200);self.assertEqual(json.loads(body)['state']['status'],'CLARIFY')
        self.assertEqual(json.loads(self.req('/api/state?count=11')[1])['state']['status'],'ALIGNED')
    def test_origin_host_and_unknown_route(self):
        self.assertEqual(self.req('/api/analyze',{'mode':'mock','messages':events()[:1]},{'Origin':'https://evil.example'})[0],403)
        self.assertEqual(self.req('/api/state',headers={'Host':'evil.example'})[0],403)
        self.assertEqual(self.req('/../provider.py')[0],404)
    def test_repaired_recovery_route_returns_resolved_audit(self):
        code,body,_=self.req('/api/state?count=19');state=json.loads(body)['state']
        self.assertEqual(code,200);self.assertEqual(state['status'],'ALIGNED');self.assertEqual(state['agreement']['version'],'v4')
        self.assertEqual(state['resolvedWarnings'][0]['evidence'][0]['messageId'],'m15')
        self.assertEqual(len(state['resolvedWarnings'][0]['resolution']['evidence']),4)
    def test_static_policy_no_secrets_or_runtime_exception(self):
        code,body,headers=self.req('/');self.assertEqual(code,200);self.assertIn('FreightSwitch',body.decode());self.assertIn("frame-ancestors 'none'",headers['Content-Security-Policy'])
        self.assertEqual(self.req('/api/state?count=999')[0],400)
        self.assertEqual(self.req('/api/evaluate',{'messages':'invalid'})[0],400)
    def test_downloaded_recorded_export_matches_sources_and_never_calls_provider(self):
        from unittest.mock import patch
        with patch('provider.Analyzer.analyze',side_effect=AssertionError('No provider call allowed')):
            code,body,headers=self.req('/api/export?count=8&review=recorded')
        exported=json.loads(body);self.assertEqual(code,200);self.assertIn('attachment;',headers['Content-Disposition'])
        self.assertEqual(exported['buildId'],json.loads(self.req('/api/health')[1])['buildId']);self.assertEqual(exported['sourceDigest'],json.loads(self.req('/api/health')[1])['sourceDigest']);self.assertEqual(exported['visibleCount'],8);self.assertEqual(exported['scenario'],'risk');self.assertTrue(exported['realInference']);self.assertTrue(exported['recordedReplay']);self.assertEqual(exported['state']['status'],'AT_RISK')
        self.assertEqual(len(exported['messages']),8);self.assertEqual(len(exported['advisory']['observations']),3)
        self.assertEqual(self.req('/api/export?count=4&review=recorded')[0],400)
        self.assertFalse(json.loads(self.req('/api/export?count=19')[1])['realInference'])
        self.assertEqual(self.req('/.secrets/provider.json')[0],404)
    def test_review_http_revision_decision_export_and_no_live_route(self):
        headers={'Origin':self.base};body={'id':'http-source','body':'I received, but have NOT accepted shipment FS-1042 / v2. Request m05.','senderLabel':'Synthetic unverified sender'}
        self.assertEqual(self.req('/api/review/source',body)[0],403)
        source=json.loads(self.req('/api/review/source',body,headers)[1])['source']
        proposal=json.loads(self.req('/api/review/propose',dict(sourceId=source['id'],sourceRevision=source['revisionId'],mode='mock'),headers)[1])['proposal']
        data=dict(actionId='http-a1',proposalId=proposal['proposalId'],sourceRevision=source['revisionId'],sourceSHA256=source['sha256'],decision='approve',version='v2',quote=body['body'],note='Approve receipt interpretation, not acceptance.')
        code,raw,_=self.req('/api/review/decision',data,headers);self.assertEqual(code,200);self.assertFalse(json.loads(raw)['entry']['agreementChanged'])
        self.assertEqual(self.req('/api/review/decision',data,headers)[1],raw)
        self.assertEqual(self.req('/api/review/propose',dict(sourceId=source['id'],sourceRevision=source['revisionId'],mode='live'),headers)[0],400)
        code,export,metadata=self.req('/api/review/export');self.assertEqual(code,200);self.assertIn('FreightSwitch-interpretation-audit.json',metadata['Content-Disposition']);self.assertEqual(len(json.loads(export)['audit']),1);self.assertEqual(json.loads(export)['sourceDigest'],json.loads(self.req('/api/health')[1])['sourceDigest'])
        self.assertEqual(json.loads(self.req('/api/state?count=8')[1])['state']['agreement']['version'],'v1')
        health=json.loads(self.req('/api/health')[1]);self.assertTrue(health['buildId'].startswith('FS-1.6-public-'));self.assertEqual(health['webInferenceCalls'],0)

if __name__=='__main__':unittest.main(verbosity=2)
