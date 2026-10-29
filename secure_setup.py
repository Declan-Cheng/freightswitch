"""One-use local UI handoff for an already-approved dedicated provider key.

No account login, key creation, clipboard read or inference happens here. The
browser uses a password field; server logs and responses never echo input.
Launch only when ready to transfer the one key. No public bind/configurable host.
"""
import argparse
import hmac
from http.server import BaseHTTPRequestHandler,HTTPServer
import secrets
from urllib.parse import parse_qs
from secret_input import SECRET,store


def make_server(port=8913,target=SECRET):
    nonce=secrets.token_urlsafe(32);state={'saved':False}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def origin(self):return 'http://127.0.0.1:'+str(self.server.server_port)
        def valid_host(self):return self.headers.get('Host')=='127.0.0.1:'+str(self.server.server_port)
        def reply(self,code,body):
            raw=body.encode();self.send_response(code);self.send_header('Content-Type','text/html; charset=utf-8')
            self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','same-origin')
            self.send_header('Content-Security-Policy',"default-src 'none'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers();self.wfile.write(raw)
        def do_GET(self):
            if not self.valid_host() or self.path!='/':return self.reply(404,'Not available')
            if state['saved']:return self.reply(409,'Configuration already saved; no further input accepted')
            return self.reply(200,'<!doctype html><html lang="en"><meta charset="utf-8"><title>FreightSwitch secure local setup</title><h1>Server-only key setup</h1><p>One approved dedicated key. Local password input only. No inference or account change occurs.</p><form method="post" action="/configure"><input type="hidden" name="nonce" value="'+nonce+'"><label>API key <input type="password" name="api_key" autocomplete="off" required></label><button type="submit">Save server-only key</button></form></html>')
        def do_POST(self):
            if not self.valid_host() or self.path!='/configure' or self.headers.get('Origin')!=self.origin():return self.reply(403,'Local same-origin handoff required')
            if state['saved']:return self.reply(409,'Already configured')
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=8192 or self.headers.get('Content-Type','').split(';')[0]!='application/x-www-form-urlencoded':return self.reply(400,'Bounded form input required')
                fields=parse_qs(self.rfile.read(length).decode(),strict_parsing=True)
                if set(fields)!={'nonce','api_key'} or any(len(v)!=1 for v in fields.values()) or not hmac.compare_digest(fields['nonce'][0],nonce):return self.reply(403,'Invalid one-use form')
                store(fields['api_key'][0],target)
            except Exception:return self.reply(400,'Setup refused; no secret echoed; existing configuration preserved')
            state['saved']=True;return self.reply(200,'<!doctype html><title>FreightSwitch setup complete</title><h1>Server-only configuration saved</h1><p>Owner-only storage. No key is shown. No inference was performed.</p>')
    server=HTTPServer(('127.0.0.1',port),Handler);server.setup_state=state
    return server


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--port',type=int,default=8913);args=p.parse_args()
    if SECRET.exists():raise SystemExit('Existing secret preserved; setup not started')
    server=make_server(args.port)
    print('One-use local hidden input ready: http://127.0.0.1:'+str(server.server_port)+'/',flush=True)
    try:
        while not server.setup_state['saved']:server.handle_request()
    except KeyboardInterrupt:pass
    finally:server.server_close()
