'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),crypto=require('node:crypto').webcrypto;
const {PreviewAPI,canonical}=require('../demo-api.js');
const data=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../capture.json'),'utf8'));
const cases=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'reference_cases.json'),'utf8'));
const dynamic=new Set(['auditId','actionId','proposalId','sourceRevision','createdAt']);let passed=0;
function memory(){const x=new Map;return {getItem:k=>x.get(k)??null,setItem:(k,v)=>x.set(k,v)};}
function base(result){return {actionId:'contract-test',proposalId:result.proposal.proposalId,sourceRevision:result.source.revisionId,sourceSHA256:result.source.sha256,version:result.proposal.observation.version,quote:result.source.body,note:'I reviewed the complete source v6 and its unconditional wording.',humanKind:'accept',sourceReviewed:true,conditionsQuotesChecked:true,localInterpretationOnlyAcknowledged:true};}
(async()=>{
 for(const test of cases){
  const api=new PreviewAPI(data,memory(),crypto),fixture=await api.call('/api/advisory/'+test.fixture,{},'POST'),payload=base(fixture);
  for(const key of test.remove)delete payload[key];Object.assign(payload,test.patch);
  let result;try{const {entry}=await api.call('/api/advisory/'+(test.assessment?'assessment':'decision'),payload,'POST');result={ok:true,entry:Object.fromEntries(Object.entries(entry).filter(([k])=>!dynamic.has(k)))};}catch(e){result={ok:false};}
  assert.deepEqual(result,test.expected,test.name);passed++;
 }
 const storage=memory(),api=new PreviewAPI(data,storage,crypto),initial=await api.call('/api/state?count=19',undefined,'GET');
 const f=await api.call('/api/advisory/practice',{},'POST'),payload=base(f);
 const first=await api.call('/api/advisory/assessment',payload,'POST'),retry=await api.call('/api/advisory/assessment',payload,'POST');assert.deepEqual(first,retry);passed++;
 assert.equal((await api.call('/api/advisory',undefined,'GET')).audit.length,1);passed++;
 await assert.rejects(api.call('/api/advisory/assessment',{...payload,note:'Changed action reason'},'POST'));passed++;
 const reloaded=new PreviewAPI(data,storage,crypto);assert.equal((await reloaded.call('/api/advisory',undefined,'GET')).audit.length,1);passed++;
 assert.deepEqual((await api.call('/api/state?count=19',undefined,'GET')).state,initial.state);passed++;
 await api.call('/api/advisory/source',{id:f.source.id,senderLabel:f.source.senderLabel,body:f.source.body.replace('v6','v7')},'POST');
 await assert.rejects(api.call('/api/advisory/assessment',payload,'POST'));passed++;
 await assert.rejects(api.call('/api/advisory/assessment',{...payload,actionId:'fresh-stale'},'POST'));passed++;
 const stale=await api.call('/api/advisory/export',undefined,'GET');assert.equal(stale.audit[0].appliesToCurrentSource,false);assert.equal(stale.sourceHistory.length,2);assert.equal(stale.proposals[0].observation.kind,'accept');passed++;
 assert.equal(stale.previewRuntime,'browser-local-recorded-output');assert.equal(stale.referenceSourceDigest,data.reference.sourceDigest);assert.equal(stale.sourceDigest,data.preview.sourceDigest);passed++;
 const restored=await api.call('/api/advisory/practice',{},'POST');assert.notEqual(restored.source.revisionId,f.source.revisionId);passed++;
 await api.call('/api/advisory/assessment',{...base(restored),actionId:'restored'},'POST');passed++;
 for(const [count,packet] of Object.entries(data.packets)){
  assert.deepEqual((await api.call('/api/state?count='+count,undefined,'GET')).state,packet.state);passed++;
 }
 assert.deepEqual(await api.call('/api/evaluate',{messages:data.ambiguity.messages},'POST'),{state:data.ambiguity.state});passed++;
 await assert.rejects(api.call('/api/evaluate',{messages:[]},'POST'));passed++;
 await assert.rejects(api.call('/api/analyze',{messages:data.packets['8'].messages,mode:'live'},'POST'));passed++;
 assert.deepEqual(await api.call('/api/analyze',{messages:data.packets['8'].messages,mode:'mock'},'POST'),data.mocks['8']);passed++;
 await assert.rejects(api.call('/api/advisory/diagnostic',{},'POST'));passed++;
 await assert.rejects(api.call('/api/review/recorded',{},'POST'));passed++;
 const health=await api.call('/api/health',undefined,'GET');assert.equal(health.liveWebRoute,false);assert.equal(health.webInferenceCalls,0);passed++;
 const fresh=new PreviewAPI(data,memory(),crypto);assert.equal((await fresh.call('/api/advisory',undefined,'GET')).audit.length,0);passed++;
 const exp=await api.call('/api/export?count=19&review=none',undefined,'GET');assert.equal(exp.realInference,false);assert.equal(exp.recordedReplay,false);assert.deepEqual(exp.state,initial.state);passed++;
 const ambiguousExport=await api.call('/api/export?count=-1&review=none',undefined,'GET');assert.deepEqual(ambiguousExport.state,data.ambiguity.state);assert.deepEqual(ambiguousExport.messages,data.ambiguity.messages);assert.equal(ambiguousExport.referenceBuildId,data.reference.buildId);assert.equal(ambiguousExport.scenario,'authored-ambiguous-time');passed++;
 assert.deepEqual(stale.originalStrictHybridScore,{passed:0,total:12});assert.match(stale.scoreNotice,/not a score for this browser preview/);passed++;
 const labelAPI=new PreviewAPI(data,memory(),crypto),labelOriginal=await labelAPI.call('/api/advisory/practice',{},'POST');const changedLabel=(await labelAPI.call('/api/advisory/source',{id:labelOriginal.source.id,body:labelOriginal.source.body,senderLabel:'New fictional label'},'POST')).source;assert.equal(changedLabel.sha256,labelOriginal.source.sha256);assert.notEqual(changedLabel.revisionId,labelOriginal.source.revisionId);assert.equal((await labelAPI.call('/api/advisory',undefined,'GET')).proposals[0].appliesToCurrentSource,false);passed++;
 console.log(JSON.stringify({passed,pythonDifferentialCases:cases.length,newInferenceCalls:0,browserVisualQA:'not-run-by-this-test'}));
})().catch(error=>{console.error(error);process.exit(1)});
