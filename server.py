"""FreightSwitch loopback-only private demo. No live-inference web route."""
import argparse
import hashlib
import json
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlparse,parse_qs
from fixtures import events,recovery_events,RECOVERY_SCENE,SCENES,PARTIES
from domain import evaluate
from provider import Analyzer,ProviderError,status,parse
from recorded_review import load_recorded
from review_workspace import ReviewStore
from advisory_workspace import AdvisoryReviewStore
from advisory_practice import import_practice,import_example
from build_id import BUILD_ID,SOURCE_DIGEST

ROOT=Path(__file__).resolve().parent
ANALYZER=Analyzer()


def packet(count):
    if type(count) is not int or not 0<=count<=len(recovery_events()):raise ValueError('Invalid event count')
    messages=recovery_events()[:count]
    return dict(state=evaluate(messages),messages=messages,scenes=SCENES+[RECOVERY_SCENE],parties=PARTIES,provider=status(),visibleCount=count,recordedReview=load_recorded(),buildId=BUILD_ID,sourceDigest=SOURCE_DIGEST)


class Handler(BaseHTTPRequestHandler):
    def review(self):return ReviewStore(getattr(self.server,'review_path',ROOT/'.runtime'/'review.sqlite'))
    def advisory(self):return AdvisoryReviewStore(getattr(self.server,'advisory_path',ROOT/'.runtime'/'advisory.sqlite'))
    def log_message(self,*args):pass
    def send(self,code,data,kind='application/json',download=False,filename='FreightSwitch-FS-1042-evidence.json'):
        body=json.dumps(data,ensure_ascii=False).encode() if kind=='application/json' else data
        self.send_response(code);self.send_header('Content-Type',kind+'; charset=utf-8');self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
        if download:self.send_header('Content-Disposition','attachment; filename="'+filename+'"')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers();self.wfile.write(body)
    def local(self):
        return self.headers.get('Host') in ('127.0.0.1:'+str(self.server.server_port),'localhost:'+str(self.server.server_port))
    def do_GET(self):
        if not self.local():return self.send(403,{'error':'Loopback host required'})
        path=urlparse(self.path)
        try:
            if path.path=='/api/state':return self.send(200,packet(int(parse_qs(path.query).get('count',['8'])[0])))
            if path.path in ('/api/advisory','/api/advisory/export'):
                return self.send(200,dict(buildId=BUILD_ID,sourceDigest=SOURCE_DIGEST,postHocRepair=True,originalStrictHybridScore=dict(passed=0,total=12),**self.advisory().snapshot()),download=path.path.endswith('/export'),filename='FreightSwitch-unverified-advisory-audit.json')
            if path.path in ('/api/review','/api/review/export'):
                return self.send(200,dict(buildId=BUILD_ID,sourceDigest=SOURCE_DIGEST,**self.review().snapshot()),download=path.path.endswith('/export'),filename='FreightSwitch-interpretation-audit.json')
            if path.path=='/api/export':
                query=parse_qs(path.query);current=packet(int(query.get('count',['8'])[0]));review=query.get('review',['none'])[0]
                if review not in ('none','recorded'):raise ValueError('Unknown review')
                advisory=current['recordedReview'] if review=='recorded' else None
                if review=='recorded' and (advisory is None or not set(advisory['sourceIds']).issubset({m['id'] for m in current['messages']})):raise ValueError('Review/source mismatch')
                return self.send(200,dict(format='freightswitch-private-evidence-v1.3',buildId=BUILD_ID,sourceDigest=SOURCE_DIGEST,visibleCount=current['visibleCount'],scenario=next((s['id'] for s in current['scenes'] if s['count']==current['visibleCount']),None),synthetic=True,realInference=advisory is not None,recordedReplay=advisory is not None,state=current['state'],messages=current['messages'],advisory=advisory,notice='Recorded synthetic advisory only; no new call, physical execution, sender authentication or carrier validation.'),download=True)
            if path.path=='/api/health':return self.send(200,dict(name='FreightSwitch',buildId=BUILD_ID,sourceDigest=SOURCE_DIGEST,synthetic=True,webInferenceCalls=0,liveWebRoute=False))
            files={'/':('index.html','text/html'),'/app.js':('app.js','text/javascript'),'/review.js':('review.js','text/javascript'),'/advisory.js':('advisory.js','text/javascript'),'/style.css':('style.css','text/css')}
            if path.path in files:
                name,kind=files[path.path];return self.send(200,(ROOT/'static'/name).read_bytes(),kind)
            return self.send(404,{'error':'Unknown route'})
        except (ValueError,TypeError):return self.send(400,{'error':'Invalid scenario count'})
    def do_POST(self):
        if not self.local():return self.send(403,{'error':'Loopback host required'})
        origin=self.headers.get('Origin')
        if origin is not None and origin not in ('http://127.0.0.1:'+str(self.server.server_port),'http://localhost:'+str(self.server.server_port)):return self.send(403,{'error':'Same-origin only'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=100000:return self.send(413,{'error':'Bounded JSON body required'})
            data=parse(self.rfile.read(length))
            if not isinstance(data,dict):raise ValueError('JSON object required')
            if self.path.startswith('/api/advisory/'):
                if origin is None:return self.send(403,{'error':'Advisory writes require explicit local Origin'})
                store=self.advisory()
                if self.path=='/api/advisory/example':
                    if data:raise ValueError('No example parameters allowed')
                    return self.send(200,import_example(store))
                if self.path=='/api/advisory/practice':
                    if data:raise ValueError('No practice parameters allowed')
                    return self.send(200,import_practice(store))
                if self.path=='/api/advisory/source':return self.send(200,dict(source=store.save(data)))
                if self.path=='/api/advisory/decision':return self.send(200,dict(entry=store.decide(data)))
                if self.path=='/api/advisory/assessment':return self.send(200,dict(entry=store.assess(data)))
                return self.send(404,{'error':'Unknown advisory route'})
            if self.path.startswith('/api/review/'):
                if origin is None:return self.send(403,{'error':'Review writes require explicit local Origin'})
                store=self.review()
                if self.path=='/api/review/source':return self.send(200,{'source':store.save(data)})
                if self.path=='/api/review/propose':
                    if set(data)!={'sourceId','sourceRevision','mode'}:raise ValueError('Exact proposal schema required')
                    return self.send(200,{'proposal':store.propose(data['sourceId'],data['sourceRevision'],data['mode'])})
                if self.path=='/api/review/recorded':
                    if data:raise ValueError('No recorded request parameters')
                    return self.send(200,store.import_recorded())
                if self.path=='/api/review/decision':return self.send(200,{'entry':store.decide(data)})
                return self.send(404,{'error':'Unknown review route'})
            if self.path=='/api/evaluate':return self.send(200,{'state':evaluate(data.get('messages'))})
            if self.path=='/api/analyze':
                if data.get('mode')!='mock':return self.send(403,{'error':'Live inference has no web route. Use the separately authorized bounded CLI only.'})
                return self.send(200,ANALYZER.analyze(data.get('messages'),mode='mock'))
            return self.send(404,{'error':'Unknown route'})
        except (ValueError,TypeError,KeyError,ProviderError) as exc:return self.send(400,{'error':str(exc) if self.path.startswith(('/api/review/','/api/advisory/')) else 'Invalid bounded request/source; no authority was changed'})


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8909);args=parser.parse_args()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    print(BUILD_ID+' · http://127.0.0.1:%s · SYNTHETIC · NO PAID WEB CALLS'%args.port,flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
