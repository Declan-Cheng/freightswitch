"""Authored example/human workflow HTTP checks; never a model rerun."""
import json
from pathlib import Path
import sys,tempfile,threading,unittest,urllib.request,urllib.error
from unittest.mock import patch
from http.server import ThreadingHTTPServer
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server import Handler

class AdvisoryAPITests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.server.advisory_path=Path(self.temp.name)/'advisory.sqlite';self.server.review_path=Path(self.temp.name)/'review.sqlite'
        self.base='http://127.0.0.1:'+str(self.server.server_port);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
    def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join();self.temp.cleanup()
    def request(self,path,data=None,origin=True):
        headers={'Content-Type':'application/json'}
        if data is not None and origin:headers['Origin']=self.base
        request=urllib.request.Request(self.base+path,data=json.dumps(data).encode() if data is not None else None,headers=headers)
        try:
            with urllib.request.urlopen(request,timeout=5) as response:return response.status,json.loads(response.read())
        except urllib.error.HTTPError as error:return error.code,json.loads(error.read())
    def load(self):
        with patch('provider.Analyzer.analyze',side_effect=AssertionError('No model call')),patch('urllib.request.build_opener',wraps=urllib.request.build_opener):
            code,data=self.request('/api/advisory/example',{})
        self.assertEqual(code,200);return data
    def decision(self,data,**extra):
        s,p=data['source'],data['proposal'];return dict(actionId='action-one',proposalId=p['proposalId'],sourceRevision=s['revisionId'],sourceSHA256=s['sha256'],version=p['observation']['version'],quote=s['body'],note='Authored HTTP workflow test, not a score correction.',**extra)
    def test_authored_example_is_unverified_and_unsupported_approval_blocked(self):
        data=self.load();p=data['proposal']
        self.assertTrue(data['authoredExample']);self.assertEqual(data['newInferenceCalls'],0)
        self.assertFalse(p['recordedReplay']);self.assertFalse(p['realInference']);self.assertFalse(p['semanticVerified'])
        self.assertEqual(p['candidate']['reviewEligibility'],'clarification-required')
        self.assertEqual(self.request('/api/advisory/decision',self.decision(data,decision='approve'))[0],400)
    def test_human_assessment_retains_original_model_kind_and_agreement(self):
        before=self.request('/api/state?count=8')[1]['state'];data=self.load();modelkind=data['proposal']['observation']['kind']
        code,result=self.request('/api/advisory/assessment',self.decision(data,humanKind='unclear'));self.assertEqual(code,200)
        self.assertEqual(result['entry']['modelKind'],modelkind);self.assertEqual(result['entry']['humanKind'],'unclear');self.assertFalse(result['entry']['agreementChanged'])
        after=self.request('/api/state?count=8')[1]['state'];self.assertEqual(before,after)
        export=self.request('/api/advisory/export')[1];self.assertEqual(export['originalStrictHybridScore'],dict(passed=0,total=12));self.assertEqual(len(export['audit']),1)
        self.assertEqual(self.request('/api/review')[1]['proposals'],[])
    def test_forged_model_accept_or_source_revision_cannot_be_promoted(self):
        data=self.load()
        self.assertEqual(self.request('/api/advisory/assessment',self.decision(data,humanKind='accept'))[0],400)
        changed=dict(id=data['source']['id'],body=data['source']['body']+' Edited note.',senderLabel=data['source']['senderLabel'])
        self.assertEqual(self.request('/api/advisory/source',changed)[0],200)
        self.assertEqual(self.request('/api/advisory/decision',self.decision(data,decision='reject'))[0],400)
    def practice(self):
        with patch('provider.Analyzer.analyze',side_effect=AssertionError('No model call')):
            code,data=self.request('/api/advisory/practice',{})
        self.assertEqual(code,200);self.assertTrue(data['authoredPractice'])
        self.assertEqual(data['newInferenceCalls'],0);self.assertFalse(data['proposal']['realInference'])
        self.assertEqual(data['proposal']['mode'],'mock');return data
    def acceptance(self,data,**changes):
        payload=self.decision(data,humanKind='accept',sourceReviewed=True,conditionsQuotesChecked=True,localInterpretationOnlyAcknowledged=True)
        payload.update(changes);return payload
    def test_local_human_accept_is_separate_and_cannot_change_agreement(self):
        before=self.request('/api/state?count=8')[1]['state'];data=self.practice()
        self.assertEqual(self.request('/api/advisory/decision',self.decision(data,decision='approve'))[0],400)
        payload=self.acceptance(data)
        code,result=self.request('/api/advisory/assessment',payload);self.assertEqual(code,200)
        entry=result['entry'];self.assertEqual(entry['humanKind'],'accept');self.assertEqual(entry['modelKind'],'accept')
        self.assertTrue(entry['humanReported']);self.assertEqual(entry['scope'],'human-assessment-only')
        for field in ('agreementChanged','semanticVerified','sourceIdentityVerified','reviewerIdentityVerified'):self.assertFalse(entry[field])
        self.assertEqual(self.request('/api/advisory/assessment',payload),(200,result))
        self.assertEqual(before,self.request('/api/state?count=8')[1]['state'])
        audit=self.request('/api/advisory/export')[1];self.assertEqual(len(audit['audit']),1)
        self.assertTrue(audit['audit'][0]['appliesToCurrentSource']);self.assertEqual(audit['originalStrictHybridScore'],dict(passed=0,total=12))
    def test_human_accept_requires_explicit_true_acknowledgments_and_reason(self):
        data=self.practice()
        for field in ('sourceReviewed','conditionsQuotesChecked','localInterpretationOnlyAcknowledged'):
            for value in (False,'true',1,None):
                with self.subTest(field=field,value=value):self.assertEqual(self.request('/api/advisory/assessment',self.acceptance(data,**{field:value}))[0],400)
            payload=self.acceptance(data);del payload[field]
            self.assertEqual(self.request('/api/advisory/assessment',payload)[0],400)
        self.assertEqual(self.request('/api/advisory/assessment',self.acceptance(data,note='  '))[0],400)
        self.assertEqual(len(self.request('/api/advisory/export')[1]['audit']),0)
    def test_edit_invalidates_human_accept_and_prevents_identical_replay(self):
        data=self.practice();payload=self.acceptance(data)
        self.assertEqual(self.request('/api/advisory/assessment',payload)[0],200)
        changed=dict(id=data['source']['id'],body=data['source']['body']+' Correction: not accepted.',senderLabel=data['source']['senderLabel'])
        self.assertEqual(self.request('/api/advisory/source',changed)[0],200)
        self.assertEqual(self.request('/api/advisory/assessment',payload)[0],400)
        self.assertEqual(self.request('/api/advisory/assessment',dict(payload,actionId='new-action'))[0],400)
        audit=self.request('/api/advisory/export')[1]['audit'];self.assertEqual(len(audit),1)
        self.assertFalse(audit[0]['appliesToCurrentSource']);self.assertFalse(audit[0]['agreementChanged'])
    def test_authored_practice_cannot_accept_parameters_or_missing_origin(self):
        self.assertEqual(self.request('/api/advisory/practice',{'body':'override'})[0],400)
        self.assertEqual(self.request('/api/advisory/practice',{},origin=False)[0],403)
    def test_served_page_mounts_separate_advisory_ui_and_checkbox_styles(self):
        with urllib.request.urlopen(self.base+'/',timeout=5) as response:page=response.read().decode()
        self.assertIn('id="advisory-panel"',page);self.assertIn('src="/advisory.js" defer',page)
        with urllib.request.urlopen(self.base+'/advisory.js',timeout=5) as response:script=response.read().decode()
        self.assertIn('advisory-accept-confirmations',script);self.assertIn('/api/advisory/practice',script)
        with urllib.request.urlopen(self.base+'/style.css',timeout=5) as response:style=response.read().decode()
        self.assertIn('#advisory-panel fieldset[hidden]{display:none}',style)
    def test_duplicate_json_confirmation_or_source_binding_keys_rejected(self):
        data=self.practice();payload=self.acceptance(data)
        for key,value in [('sourceReviewed',False),('conditionsQuotesChecked',False),('localInterpretationOnlyAcknowledged',False),('sourceSHA256','wrong'),('version','v99')]:
            raw=('{'+json.dumps(key)+':'+json.dumps(value)+','+json.dumps(payload)[1:]).encode()
            request=urllib.request.Request(self.base+'/api/advisory/assessment',data=raw,headers={'Content-Type':'application/json','Origin':self.base})
            with self.subTest(key=key),self.assertRaises(urllib.error.HTTPError) as caught:urllib.request.urlopen(request,timeout=5)
            self.assertEqual(caught.exception.code,400)
        self.assertEqual(self.request('/api/advisory/export')[1]['audit'],[])
    def test_no_origin_no_arbitrary_example_and_no_live_web_route(self):
        self.assertEqual(self.request('/api/advisory/example',{},origin=False)[0],403)
        self.assertEqual(self.request('/api/advisory/example',{'path':'/tmp/other'})[0],400)
        self.assertEqual(self.request('/api/advisory/diagnostic',{})[0],404)
        self.assertEqual(self.request('/api/advisory/live',{})[0],404)
        self.assertEqual(self.request('/api/analyze',{'mode':'live'})[0],403)

if __name__=='__main__':unittest.main(verbosity=2)
