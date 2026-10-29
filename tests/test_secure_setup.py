import http.client
import re
from pathlib import Path
import sys
import tempfile
import threading
from urllib.parse import urlencode
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from secure_setup import make_server
from secret_input import load

class OneUseHiddenHandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.target=Path(self.temp.name)/'private/provider.json';self.server=make_server(0,self.target)
        self.port=self.server.server_port;self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
    def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join();self.temp.cleanup()
    def request(self,method,path,body=None,headers=None):
        conn=http.client.HTTPConnection('127.0.0.1',self.port,timeout=3);conn.request(method,path,body=body,headers=headers or {});r=conn.getresponse();data=r.read().decode();result=(r.status,data,dict(r.getheaders()));conn.close();return result
    def form(self):
        code,body,headers=self.request('GET','/');self.assertEqual(code,200);self.assertIn('type="password"',body)
        self.assertEqual(headers['Referrer-Policy'],'same-origin')
        return re.search('name="nonce" value="([^"]+)"',body).group(1)
    def submit(self,nonce,origin=None):
        return self.request('POST','/configure',urlencode(dict(nonce=nonce,api_key='FAKE_DEDICATED_TEST_KEY_ONLY')),{'Content-Type':'application/x-www-form-urlencoded','Origin':origin or 'http://127.0.0.1:'+str(self.port)})
    def test_actual_hidden_form_stores_owner_only_and_never_echoes_secret(self):
        nonce=self.form();code,body,headers=self.submit(nonce);self.assertEqual(code,200)
        self.assertNotIn('FAKE_DEDICATED_TEST_KEY_ONLY',body);self.assertEqual(self.target.stat().st_mode&0o777,0o600)
        self.assertEqual(load(self.target)['NEBIUS_API_KEY'],'FAKE_DEDICATED_TEST_KEY_ONLY')
        self.assertEqual(self.submit(nonce)[0],409);self.assertEqual(self.request('GET','/')[0],409)
    def test_foreign_origin_missing_nonce_and_bad_host_refused(self):
        nonce=self.form();self.assertEqual(self.submit(nonce,'https://evil.example')[0],403);self.assertEqual(self.submit('wrong')[0],403)
        self.assertEqual(self.submit(nonce,'null')[0],403)
        self.assertEqual(self.request('GET','/',headers={'Host':'evil.example'})[0],404);self.assertFalse(self.target.exists())
    def test_file_content_is_not_served_and_existing_secret_not_overwritten(self):
        nonce=self.form();self.target.parent.mkdir(mode=0o700);self.target.write_text('existing')
        self.assertEqual(self.submit(nonce)[0],400);self.assertEqual(self.target.read_text(),'existing')
        self.assertEqual(self.request('GET','/provider.json')[0],404)

if __name__=='__main__':unittest.main(verbosity=2)
