/* FreightSwitch recorded-output preview. Browser-local adapter, NOT Python server. */
(function(root){
'use strict';
const clone=x=>JSON.parse(JSON.stringify(x));
const canonical=x=>JSON.stringify(x,(k,v)=>v&&typeof v==='object'&&!Array.isArray(v)?Object.keys(v).sort().reduce((a,n)=>(a[n]=v[n],a),{}):v);
const cpLength=x=>Array.from(x).length;
const idOK=x=>typeof x==='string'&&/^[A-Za-z0-9_-]{1,80}$/.test(x);
const exact=(data,fields)=>data&&typeof data==='object'&&!Array.isArray(data)&&canonical(Object.keys(data).sort())===canonical(fields.slice().sort());
const confirmations=['sourceReviewed','conditionsQuotesChecked','localInterpretationOnlyAcknowledged'];
class PreviewAPI{
 constructor(data,storage,crypto){this.data=clone(data);this.storage=storage;this.crypto=crypto;this.key='freightswitch-preview-v1-'+data.preview.buildId;this.pending=Promise.resolve();}
 async hash(text){return Array.from(new Uint8Array(await this.crypto.subtle.digest('SHA-256',new TextEncoder().encode(text)))).map(x=>x.toString(16).padStart(2,'0')).join('');}
 fresh(){return {sources:[],sourceHistory:[],proposals:[],audit:[],requests:{}};}
 state(){const raw=this.storage.getItem(this.key);if(!raw)return this.fresh();const s=JSON.parse(raw);if(!s||!['sources','sourceHistory','proposals','audit'].every(k=>Array.isArray(s[k]))||!s.requests||typeof s.requests!=='object')throw Error('Browser demo storage is invalid; export/reset the preview.');return s;}
 save(s){this.storage.setItem(this.key,JSON.stringify(s));}
 stamp(){return new Date().toISOString();}
 uuid(){return this.crypto.randomUUID();}
 envelope(){return {buildId:this.data.preview.buildId,sourceDigest:this.data.preview.sourceDigest,referenceBuildId:this.data.reference.buildId,referenceSourceDigest:this.data.reference.sourceDigest,previewRuntime:'browser-local-recorded-output',storage:'this-browser-only; editable and not authenticated',synthetic:true,newInferenceCalls:0,liveWebRoute:false,agreementChanged:false};}
 snapshot(s){const result=clone(s);delete result.requests;for(const p of result.proposals)p.appliesToCurrentSource=result.sources.some(x=>x.id===p.sourceId&&x.revisionId===p.sourceRevision);for(const e of result.audit)e.appliesToCurrentSource=result.sources.some(x=>x.id===e.sourceId&&x.revisionId===e.sourceRevision);return {...this.envelope(),...result,advisoryOnly:true,modelAccuracy:null,semanticApprovalIsShipmentAuthority:false,originalStrictHybridScore:{passed:0,total:12},scoreNotice:'Reported historical frozen strict-integrated score from the reference project; not a score for this browser preview or a new model evaluation.'};}
 async source(s,data){
  if(!exact(data,['id','body','senderLabel'])||!idOK(data.id)||typeof data.body!=='string'||cpLength(data.body)<1||cpLength(data.body)>12000||typeof data.senderLabel!=='string'||cpLength(data.senderLabel)<1||cpLength(data.senderLabel)>100)throw Error('Exact bounded synthetic source required');
  const previous=s.sources.find(x=>x.id===data.id);if(previous&&previous.body===data.body&&previous.senderLabel===data.senderLabel)return previous;
  if(!previous&&s.sources.length>=30)throw Error('30-source workspace limit');if(s.sourceHistory.length>=1000)throw Error('Source revision limit reached');
  const source={...clone(data),sha256:await this.hash(data.body),revisionId:this.uuid(),savedAt:this.stamp(),synthetic:true,identityVerified:false};
  s.sources=s.sources.filter(x=>x.id!==data.id);s.sources.push(source);s.sourceHistory.push(clone(source));return source;
 }
 async practice(s,kind='practice'){
  const fixture=this.data[kind];const source=await this.source(s,{id:fixture.source.id,body:fixture.source.body,senderLabel:fixture.source.senderLabel});
  if(s.proposals.length>=1000)throw Error('Proposal limit reached');
  const proposal={...clone(fixture.proposal),proposalId:this.uuid(),sourceRevision:source.revisionId,sourceSHA256:source.sha256,createdAt:this.stamp()};
  delete proposal.appliesToCurrentSource;
  s.proposals.push(proposal);return {source,proposal,[kind==='practice'?'authoredPractice':'authoredExample']:true,newInferenceCalls:0,agreementChanged:false,notice:'Authored synthetic practice; browser-local adapter, no inference or shipment authority.'};
 }
 requestSchema(data,assessment){
  let fields=['actionId','proposalId','sourceRevision','sourceSHA256','version','quote','note',assessment?'humanKind':'decision'];const accept=assessment&&data?.humanKind==='accept';if(accept)fields=fields.concat(confirmations);
  if(!exact(data,fields)||!idOK(data.actionId)||typeof data.proposalId!=='string'||!data.proposalId.length||data.proposalId.length>80)throw Error('Exact source-bound review schema required');
  if(typeof data.note!=='string'||!data.note.trim()||cpLength(data.note)>1000)throw Error('Meaningful bounded review reason required');
  if(assessment){if(!['propose','received','reject','withdraw','unclear','accept'].includes(data.humanKind))throw Error('Explicit human interpretation kind required');if(accept&&(confirmations.some(k=>data[k]!==true)||cpLength(data.note.trim())<12))throw Error('Human acceptance requires three true confirmations and a reason of at least 12 characters');}
  else if(!['approve','reject','needs_clarification'].includes(data.decision))throw Error('Explicit review decision required');
  return accept;
 }
 async current(s,data){
  const p=s.proposals.find(x=>x.proposalId===data.proposalId);if(!p||p.scope!=='unverified-advisory')throw Error('Unknown authored advisory proposal');
  const source=s.sources.find(x=>x.id===p.sourceId);if(!source||data.sourceRevision!==source.revisionId||data.sourceRevision!==p.sourceRevision||data.sourceSHA256!==source.sha256||data.sourceSHA256!==p.sourceSHA256||await this.hash(source.body)!==source.sha256)throw Error('Stale source/proposal: review the current revision');
  const original=[this.data.practice,this.data.example].find(x=>x.source.id===p.sourceId);if(!original)throw Error('Unknown authored fixture');
  if(source.body!==original.source.body||source.senderLabel!==original.source.senderLabel||source.id!==original.source.id||canonical(p.candidate)!==canonical(original.proposal.candidate)||canonical(p.observation)!==canonical(original.proposal.observation)||p.reviewEligibility!==original.proposal.reviewEligibility||p.mode!=='mock'||p.realInference!==false||p.recordedReplay!==false)throw Error('Stored proposal differs from captured authored practice');
  const c=p.candidate,o=p.observation;if(data.version!==o.version||data.quote!==source.body||data.quote!==o.quote||p.sourceSHA256!==o.evidenceSHA256||c.binding.status!=='verified'||c.binding.sourceSHA256!==source.sha256)throw Error('Version/complete quote differs from reviewed source');
  return {p,source,c,o};
 }
 async record(s,data,assessment){
  const humanAccept=this.requestSchema(data,assessment),serialized=canonical(data),old=Object.hasOwn(s.requests,data.actionId)?s.requests[data.actionId]:null;
  if(old){if(old.request!==serialized)throw Error('Action ID already used for a different review');if(humanAccept){const {c,o}=await this.current(s,data);if(!o.version||c.binding.versionOrigin!=='sole-literal-source-token')throw Error('Sole literal version required');}return clone(old.entry);}
  if(s.audit.length>=1000)throw Error('Audit limit reached');
  const {p,source,c,o}=await this.current(s,data);
  if(humanAccept&&(!o.version||c.binding.versionOrigin!=='sole-literal-source-token'))throw Error('Sole literal version required');
  if(!assessment&&data.decision==='approve'&&(c.reviewEligibility!=='manual-approval-permitted'||['accept','unclear'].includes(o.kind)||!o.version))throw Error('High-risk interpretation cannot be approved as model output');
  const entry={auditId:this.uuid(),actionId:data.actionId,proposalId:p.proposalId,sourceId:source.id,sourceRevision:source.revisionId,sourceSHA256:source.sha256,version:o.version,quote:o.quote,kind:o.kind,modelKind:o.kind,decision:assessment?'human_assessment':data.decision,note:data.note,createdAt:this.stamp(),scope:assessment?'human-assessment-only':'interpretation-only',agreementChanged:false,semanticVerified:false,modelUnverified:true,synthetic:true,sourceIdentityVerified:false};
  if(assessment)Object.assign(entry,{humanKind:data.humanKind,humanReported:true,reviewerIdentityVerified:false,acceptanceAuthority:'none'});
  if(humanAccept)Object.assign(entry,Object.fromEntries(confirmations.map(k=>[k,true])),{interpretationAuthority:'local-reviewer-only',noAuthenticatedCounterpartyAgreement:true});
  s.audit.push(entry);Object.defineProperty(s.requests,data.actionId,{value:{request:serialized,entry:clone(entry)},enumerable:true,writable:true,configurable:true});return entry;
 }
 async handle(path,body,method='GET'){
  const u=new URL(path,'https://preview.invalid'),route=u.pathname;
  if(method==='GET'){
   if(route==='/api/health')return {...this.envelope(),name:'FreightSwitch private interactive preview',webInferenceCalls:0};
   if(route==='/api/advisory'||route==='/api/advisory/export')return this.snapshot(this.state());
   if(route==='/api/review'||route==='/api/review/export')return {...this.envelope(),...this.fresh(),notice:'Free-form Python review workspace is not included in this browser preview.'};
   if(route==='/api/state'||route==='/api/export'){
    const count=Number(u.searchParams.get('count')??8);const ambiguous=route==='/api/export'&&count===-1; if(!Number.isInteger(count)||(!ambiguous&&!this.data.packets[String(count)]))throw Error('Recorded scenario unavailable');
    const packet={...clone(ambiguous?{...this.data.packets['8'],...this.data.ambiguity}:this.data.packets[String(count)]),...this.envelope(),recordedReview:null};
    if(route==='/api/state')return packet;
    if((u.searchParams.get('review')||'none')!=='none')throw Error('Legacy model recordings are not included in this preview');
    return {...this.envelope(),format:'freightswitch-browser-preview-evidence-v1',visibleCount:count,scenario:ambiguous?'authored-ambiguous-time':packet.scenes.find(x=>x.count===count)?.id??null,state:packet.state,messages:packet.messages,realInference:false,recordedReplay:false,notice:'Precomputed authored scenario output from the reference Python build. Human review is browser-local and cannot alter this agreement state.'};
   }
  }
  if(method==='POST'){
   if(!body||typeof body!=='object'||Array.isArray(body))throw Error('JSON object required');
   if(route==='/api/analyze'){
    if(!exact(body,['mode','messages'])||body.mode!=='mock')throw Error('No live inference');
    const key=Object.keys(this.data.packets).find(k=>canonical(this.data.packets[k].messages)===canonical(body.messages));if(key===undefined)throw Error('Only captured authored fixture mocks are available');return clone(this.data.mocks[key]);
   }
   if(route==='/api/evaluate'){
    if(!exact(body,['messages'])||canonical(body.messages)!==canonical(this.data.ambiguity.messages))throw Error('This preview only replays the authored ambiguous-time test; use Python for arbitrary evaluation');return {state:clone(this.data.ambiguity.state)};
   }
   const s=this.state();let result;
   if(route==='/api/advisory/practice'||route==='/api/advisory/example'){if(!exact(body,[]))throw Error('No fixture parameters allowed');result=await this.practice(s,route.endsWith('practice')?'practice':'example');}
   else if(route==='/api/advisory/source')result={source:await this.source(s,body)};
   else if(route==='/api/advisory/decision')result={entry:await this.record(s,body,false)};
   else if(route==='/api/advisory/assessment')result={entry:await this.record(s,body,true)};
   else throw Error('This browser preview does not provide that Python or recorded-model route');
   this.save(s);return result;
  }
  throw Error('Unknown preview route');
 }
 call(path,body,method){const result=this.pending.then(()=>this.handle(path,body,method));this.pending=result.catch(()=>{});return result;}
}
if(typeof module!=='undefined'&&module.exports){module.exports={PreviewAPI,canonical};return;}
root.FreightSwitchPreviewAPI=PreviewAPI;
const api=new PreviewAPI(root.FS_DEMO_DATA,root.localStorage,root.crypto);root.freightPreview=api;
const nativeFetch=root.fetch.bind(root);
root.fetch=async function(input,options={}){
 const path=typeof input==='string'?input:input.url,u=new URL(path,location.href);
 if(u.origin!==location.origin||!u.pathname.startsWith('/api/'))return nativeFetch(input,options);
 const task=async()=>{try{const method=options.method||'GET';const body=options.body===undefined?undefined:JSON.parse(options.body);const data=await api.call(u.pathname+u.search,body,method);return new Response(JSON.stringify(data),{status:200,headers:{'Content-Type':'application/json'}});}catch(e){return new Response(JSON.stringify({error:e.message}),{status:400,headers:{'Content-Type':'application/json'}});}};
 return navigator.locks?navigator.locks.request(api.key,task):task();
};
})(typeof window==='undefined'?globalThis:window);
