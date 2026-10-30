"""Differential outcomes from exact public Python reference, offline only."""
import copy,json,sys,tempfile
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from advisory_workspace import AdvisoryReviewStore
from advisory_practice import import_practice,import_example
DYNAMIC={'auditId','actionId','proposalId','sourceRevision','createdAt'}
cases=[]
def add(name,patch=None,remove=None,assessment=True,fixture='practice'):
 cases.append(dict(name=name,patch=patch or {},remove=remove or [],assessment=assessment,fixture=fixture))
add('human accept valid')
add('approve accept blocked',{'decision':'approve'},['humanKind','sourceReviewed','conditionsQuotesChecked','localInterpretationOnlyAcknowledged'],False)
for kind in ['propose','received','reject','withdraw','unclear']:
 add('separate human '+kind,{'humanKind':kind},['sourceReviewed','conditionsQuotesChecked','localInterpretationOnlyAcknowledged'])
for flag in ['sourceReviewed','conditionsQuotesChecked','localInterpretationOnlyAcknowledged']:
 for value in [False,1,'true',None]:add(flag+' rejects '+str(value),{flag:value})
 add(flag+' missing',remove=[flag])
for note in ['', ' ', '12345678901','a'*1001,'🙂'*11,'🙂'*12,'source v6 reviewed carefully']:
 add('note '+str(len(note)),{'note':note})
for patch in [{'version':'v7'},{'quote':'partial quote'},{'sourceSHA256':'0'*64},{'sourceRevision':'stale'},{'actionId':''},{'actionId':'bad action'},{'humanKind':'automatic'},{'extra':True}]:
 add('bad '+next(iter(patch)),patch)
for action in ['__proto__','constructor','valid-action-1']:add('safe action key '+action,{'actionId':action})
for decision in ['reject','needs_clarification','approve']:
 add('example decision '+decision,{'decision':decision},['humanKind','sourceReviewed','conditionsQuotesChecked','localInterpretationOnlyAcknowledged'],False,'example')
results=[]
with tempfile.TemporaryDirectory(prefix='preview-parity-') as td:
 for index,c in enumerate(cases):
  store=AdvisoryReviewStore(Path(td)/str(index)/'review.sqlite')
  result=(import_practice if c['fixture']=='practice' else import_example)(store)
  s,p=result['source'],result['proposal'];o=p['observation']
  data=dict(actionId='contract-test',proposalId=p['proposalId'],sourceRevision=s['revisionId'],sourceSHA256=s['sha256'],version=o['version'],quote=o['quote'],note='I reviewed the complete source v6 and its unconditional wording.',humanKind='accept',sourceReviewed=True,conditionsQuotesChecked=True,localInterpretationOnlyAcknowledged=True)
  for key in c['remove']:data.pop(key,None)
  data.update(c['patch'])
  try:
   entry=(store.assess if c['assessment'] else store.decide)(data)
   expected=dict(ok=True,entry={k:v for k,v in entry.items() if k not in DYNAMIC})
  except (ValueError,TypeError,KeyError):expected=dict(ok=False)
  results.append({**c,'expected':expected})
Path(sys.argv[2]).write_text(json.dumps(results,indent=2))
print(json.dumps({'referenceCases':len(results),'newInferenceCalls':0}))
