"""Capture only authored synthetic fixture outputs; never imports evaluation/gold."""
import copy,hashlib,json,sys,tempfile
from pathlib import Path
root=Path(__file__).resolve().parent
source=Path(sys.argv[1]).resolve()
sys.path.insert(0,str(source))
from fixtures import recovery_events,SCENES,RECOVERY_SCENE,PARTIES
from domain import evaluate
from provider import Analyzer
from advisory_workspace import AdvisoryReviewStore
from advisory_practice import import_practice,import_example
from build_id import BUILD_ID,SOURCE_DIGEST
EXPECTED='22bb8d9b977bc99dbbcf08d925bcaf2c3d63830ab4236f99ea81f578d3e7c902'
if SOURCE_DIGEST!=EXPECTED:raise SystemExit('Reference source changed; reapprove snapshot: '+SOURCE_DIGEST)
messages=recovery_events()
data={'reference':{'buildId':BUILD_ID,'sourceDigest':SOURCE_DIGEST},'packets':{},'mocks':{}}
analyzer=Analyzer()
for count in range(len(messages)+1):
    docs=copy.deepcopy(messages[:count])
    data['packets'][str(count)]=dict(state=evaluate(docs),messages=docs,scenes=SCENES+[RECOVERY_SCENE],parties=PARTIES,provider={'candidateModel':'NVIDIA model adapter (disabled in this preview)','provider':'Nebius Token Factory'},visibleCount=count,recordedReview=None)
    data['mocks'][str(count)]=analyzer.analyze(docs,mode='mock') if docs else {'observations':[],'questions':[],'mode':'mock','realInference':False}
ambiguous=copy.deepcopy(messages[:8]);proposal=next(m for m in ambiguous if m['id']=='m05');proposal['details']['time']='Tomorrow at 3';proposal['body']=proposal['body'].replace('2026-10-27T11:30:00-04:00','Tomorrow at 3');proposal['sha256']=hashlib.sha256(proposal['body'].encode()).hexdigest()
data['ambiguity']={'messages':ambiguous,'state':evaluate(ambiguous)}
with tempfile.TemporaryDirectory(prefix='freight-preview-') as temporary:
    store=AdvisoryReviewStore(Path(temporary)/'review.sqlite')
    data['practice']=import_practice(store)
    data['example']=import_example(store)
# Nothing from evaluation, gold, private evidence, .runtime, credentials or recorded model outputs is read.
dist=root/'dist';dist.mkdir(exist_ok=True)
for name in ['app.js','advisory.js','style.css','index.html']:(dist/name).write_bytes((source/'static'/name).read_bytes())
index=(dist/'index.html').read_text().replace('<script src="/review.js" defer></script>','')
index=index.replace('<script src="/app.js" defer></script>','<script src="/demo-data.js" defer></script><script src="/demo-api.js" defer></script><script src="/app.js" defer></script>')
index=index.replace('<script src="/advisory.js" defer></script>','<script src="/advisory.js" defer></script><script src="/demo-ui.js" defer></script>')
index=index.replace('PRIVATE LOCAL','BROWSER PREVIEW')
index=index.replace('</head>','<link rel="stylesheet" href="/demo.css"></head>')
index=index.replace('<title>FreightSwitch — One change. One shared instruction.</title>','<title>FreightSwitch — recorded-output interactive preview</title>')
(dist/'index.html').write_text(index)
app=(dist/'app.js').read_text().replace("+' · PRIVATE LOCAL'","+' · BROWSER PREVIEW'")
(dist/'app.js').write_text(app)
for name in ['demo-api.js','demo-ui.js','demo.css','responsive-qa.html']:(dist/name).write_bytes((root/name).read_bytes())
# Build digest: sorted deployed source filenames/bytes plus captured JSON before preview metadata.
digest=hashlib.sha256()
for path in sorted(dist.iterdir()):
    if path.is_file() and path.name!='demo-data.js':digest.update(path.name.encode()+b'\0'+path.read_bytes()+b'\0')
digest.update(b'capture.json\0'+json.dumps(data,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()+b'\0')
sha=digest.hexdigest();data['preview']={'buildId':'FS-BROWSER-PREVIEW-'+sha[:12],'sourceDigest':sha,'digestContract':'Sorted deployed files except demo-data.js plus canonical capture JSON excluding preview metadata.'}
(root/'capture.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
(dist/'demo-data.js').write_text('window.FS_DEMO_DATA='+json.dumps(data,ensure_ascii=False,separators=(',',':'))+';\n')
manifest={'reference':data['reference'],'preview':data['preview'],'artifacts':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(dist.iterdir()) if p.is_file()},'noNewInference':True,'recordedModelsIncluded':False,'storage':'browser-local','runtimeDifference':'Not Python/SQLite; agreement output captured, source-bound human review uses separately tested browser adapter.'}
(root/'PREVIEW_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'reference':data['reference'],'preview':data['preview'],'files':len(manifest['artifacts']),'newInferenceCalls':0}))
