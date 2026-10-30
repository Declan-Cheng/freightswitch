/* Post-evaluation review UI. No provider route or automatic model request. */
(()=>{
  'use strict';
  const panel=document.getElementById('advisory-panel');
  if(!panel)return;
  const kinds=['propose','received','reject','withdraw','unclear','accept'];
  const make=(tag,text='',cls='',id=null)=>{const e=document.createElement(tag);e.textContent=text;e.className=cls;if(id)e.id=id;return e;};
  const button=(text,id)=>{const e=make('button',text,'button light',id);e.type='button';return e;};
  const headline=make('h2','Read the suggestion. Keep the authority separate.');
  const notice=make('p','POST-HOC REVIEW WORKSPACE · NO NEW MODEL CALL. The original independent strict end-to-end result remains 0/12 cases. Retaining a suggestion here is not an improved score.');
  const boundary=make('p','A matching source hash proves neither meaning nor sender authenticity. Every retained suggestion below is UNVERIFIED. Reviewing an interpretation never changes shipment agreement or dispatches a driver.','muted');
  const actions=make('div','','review-actions');
  const load=button('Load authored review example (no model)','advisory-load');
  const practice=button('Load authored acceptance practice (no model)','advisory-practice');
  const reload=button('Reload review audit','advisory-refresh');
  const exportLink=make('a','Export advisory audit','button light','advisory-export');exportLink.href='/api/advisory/export';exportLink.download='FreightSwitch-unverified-advisory-audit.json';
  actions.append(load,practice,reload,exportLink);
  const status=make('p','Loading the separate advisory audit…','','advisory-status');status.setAttribute('role','status');
  const pickLabel=make('label','Previously retained suggestion');
  const pick=make('select','','','advisory-pick');pickLabel.append(pick);
  const proof=make('div','','review-entry','advisory-proof');
  const reasonLabel=make('label','Reason for your review decision');
  const reason=make('textarea','','','advisory-note');reason.rows=3;reason.maxLength=1000;reason.placeholder='Explain your reading of the complete source, including any limits or remaining uncertainty.';reasonLabel.append(reason);
  const decisionButtons=make('div','','review-actions');
  const approve=button('Approve supported interpretation','advisory-approve');
  const reject=button('Reject model suggestion','advisory-reject');
  const clarify=button('Request clarification','advisory-clarify');
  decisionButtons.append(approve,reject,clarify);
  const assessmentLabel=make('label','Your separate human interpretation');
  const assessment=make('select','','','advisory-human-kind');
  const placeholder=make('option','Choose your own reading');placeholder.value='';assessment.append(placeholder);
  for(const kind of kinds){const option=make('option',kind==='accept'?'ACCEPT — my local interpretation only':kind.toUpperCase());option.value=kind;assessment.append(option);}
  assessmentLabel.append(assessment);
  const acceptance=make('fieldset','','','advisory-accept-confirmations');acceptance.hidden=true;acceptance.disabled=true;
  acceptance.append(make('legend','HUMAN-REPORTED ACCEPT INTERPRETATION · not a verified agreement'));
  const acknowledgment=(id,label)=>{const e=make('input','','',id);e.type='checkbox';e.checked=false;const row=make('label');row.append(e,make('span',label));acceptance.append(row);return e;};
  const fullSource=acknowledgment('advisory-accept-full-source','I reviewed the complete source and the current version shown above.');
  const contextChecked=acknowledgment('advisory-accept-context','I checked quoted, negated and conditional context, rather than relying on the model label.');
  const localOnly=acknowledgment('advisory-accept-local-only','This is my own local interpretation, not verified counterparty agreement, legal acceptance or shipment authorization.');
  const confirmations=[fullSource,contextChecked,localOnly];
  acceptance.append(make('p','These confirmations are self-reported. They do not authenticate the sender or connect this reading to the separate authored three-party fixture. Shipment agreement stays unchanged; no dispatch.','muted small'));
  const assess=button('Record separate human assessment','advisory-assess');
  const assessmentNote=make('p','Record your own reading with a source-grounded reason. ACCEPT requires a reason of at least 12 characters, three explicit confirmations and a current sole version; it records only a HUMAN-REPORTED ACCEPT INTERPRETATION. The model remains UNVERIFIED. This never rewrites the model score or creates authenticated, legal or operational acceptance. The separate three-party view uses authored fixtures and is not linked to this form.','muted small');
  const auditBox=make('div','','','advisory-audit');
  panel.append(headline,notice,boundary,actions,status,pickLabel,proof,reasonLabel,decisionButtons,assessmentLabel,acceptance,assess,assessmentNote,make('h3','Append-only advisory review'),auditBox);

  let busy=false,selected=null,snapshot=null,writeUncertain=false;
  const reasonText={
    'literal-policy-does-not-establish-model-interpretation':'The literal wording check does not establish this model label.',
    'missing-or-competing-literal-version':'The source has a missing or competing version reference.',
    'source-specific-clarification-required':'A source-specific clarification is required.',
    'conditional-language-caution':'Conditional wording needs human attention; this lexical flag is not a semantic verdict.',
    'nonacceptance-language-caution':'Non-acceptance wording needs human attention.',
    'quoted-or-instruction-language-caution':'Quoted or instruction-like wording needs human attention; the embedded text has no authority.',
    'acceptance-needs-independent-confirmation':'A model acceptance suggestion cannot be directly approved. You may separately record your own bounded interpretation; this does not verify counterparty agreement.'
  };
  function clearAccept(){for(const input of confirmations)input.checked=false;}
  function clearAssessment(){assessment.value='';clearAccept();}
  function acceptVersionBound(){return !!selected&&selected.proposal.candidate.binding.versionOrigin==='sole-literal-source-token'&&typeof selected.proposal.observation.version==='string'&&selected.proposal.observation.version.length>0;}
  function acceptConfirmed(){return confirmations.every(input=>input.checked===true);}
  function controls(){
    const active=!!selected&&!selected.stale&&!writeUncertain;
    load.disabled=busy;practice.disabled=busy;reload.disabled=busy;pick.disabled=busy||!snapshot?.proposals.length;
    reason.disabled=busy||!active;assessment.disabled=busy||!active;
    const accepting=assessment.value==='accept';
    acceptance.hidden=!accepting;acceptance.disabled=busy||!active||!accepting||!acceptVersionBound();
    for(const input of confirmations)input.disabled=acceptance.disabled;
    assess.disabled=busy||!active||(accepting&&(!acceptVersionBound()||!acceptConfirmed()));
    assess.textContent=accepting?'Record HUMAN-REPORTED ACCEPT INTERPRETATION':'Record separate human assessment';
    reject.disabled=busy||!active;clarify.disabled=busy||!active;
    approve.disabled=busy||!active||selected?.proposal.candidate.reviewEligibility!=='manual-approval-permitted'||selected?.proposal.observation.kind==='accept'||selected?.proposal.observation.kind==='unclear'||selected?.proposal.observation.version===null;
  }
  function bound(source,proposal){
    const c=proposal?.candidate,o=proposal?.observation,b=c?.binding;
    if(!source||!c||!o||!b||b.status!=='verified'||b.identityVerified!==false||b.sourceAuthenticity!=='not-established'||c.semanticStatus!=='unverified'||proposal.semanticVerified!==false||proposal.proposalOnly!==true||proposal.agreementChanged!==false)throw Error('Unverified advisory contract required');
    if(proposal.sourceId!==source.id||proposal.sourceRevision!==source.revisionId||proposal.sourceSHA256!==source.sha256||o.messageId!==source.id||o.quote!==source.body||o.evidenceSHA256!==source.sha256||b.sourceSHA256!==source.sha256||b.sourceSpan?.start!==0||b.sourceSpan?.end!==Array.from(source.body).length||b.sourceSpan?.unit!=='unicode-codepoints')throw Error('Source binding mismatch');
    if(c.observation?.quote!==o.quote||c.modelProposal?.kind!==o.kind||c.modelProposal?.messageId!==o.messageId)throw Error('Model suggestion changed');
    return {source,proposal,stale:false};
  }
  function provenance(proposal){
    if(proposal.mode==='injected-test'&&proposal.realInference===false)return 'INJECTED TEST · NO REAL MODEL CALL';
    if(proposal.mode==='mock'&&proposal.realInference===false)return 'SCRIPTED MOCK · NO MODEL CALL';
    if(proposal.mode==='live'&&proposal.realInference===true&&proposal.recordedReplay!==true)return 'LIVE MODEL SUGGESTION · STILL UNVERIFIED';
    return 'PROVENANCE NOT ESTABLISHED · DO NOT TREAT AS LIVE INFERENCE';
  }
  function render(){
    proof.replaceChildren();
    if(!selected){proof.append(make('p','Load an explicitly authored review or acceptance practice source to inspect a retained suggestion. No inference will be requested.','muted'));controls();return;}
    const {source,proposal,stale}=selected,o=proposal.observation,c=proposal.candidate;
    const scripted=proposal.realInference===false&&['mock','injected-test'].includes(proposal.mode);
    proof.append(make('strong',(scripted?'UNVERIFIED SCRIPTED SUGGESTION · ':'UNVERIFIED MODEL SUGGESTION · ')+o.kind.toUpperCase()),make('p',provenance(proposal)),
      make('p','Version: '+(o.version||'unresolved')+' · Review scope: interpretation only'),make('blockquote',o.quote),
      make('p',o.explanation),make('small','Source '+source.id+' · revision '+source.revisionId+' · SHA-256 '+source.sha256),
      make('p','Full original source retained. Role, organization and timestamp text are unverified presentation content—not authenticated sender identity.','muted small'),
      make('p',scripted?'Scripted placeholder confidence '+o.confidence+' is not a model measurement. Binding is not semantic approval.':'Model confidence '+o.confidence+' is uncalibrated. Binding is not semantic approval.','muted small'));
    if(stale)proof.append(make('strong','STALE SOURCE · Original evidence retained; review the current revision before any decision.'));
    else if(c.reviewEligibility!=='manual-approval-permitted'||o.kind==='accept')proof.append(make('strong','DIRECT MODEL APPROVAL BLOCKED · Clarify, reject, or separately record your own interpretation. No shipment agreement is created.'));
    else proof.append(make('strong','HUMAN REVIEW REQUIRED · Eligible to review, not automatically approved.'));
    for(const code of c.reviewReasons||[])proof.append(make('p',reasonText[code]||('Review caution: '+code)));
    for(const question of proposal.questions||[])proof.append(make('p','Model question: '+question));
    controls();
  }
  function renderAudit(state){
    auditBox.replaceChildren();
    if(!state.audit.length)auditBox.append(make('p','No advisory review actions yet.','muted'));
    for(const entry of [...state.audit].reverse()){
      const row=make('article','','review-entry'+(entry.appliesToCurrentSource===false?' stale':''));
      const original=state.proposals.find(proposal=>proposal.proposalId===entry.proposalId);
      const scripted=original?.realInference===false&&['mock','injected-test'].includes(original?.mode);
      const human=entry.scope==='human-assessment-only'||entry.humanKind!==undefined;
      const label=human?(entry.humanKind==='accept'?'HUMAN-REPORTED ACCEPT INTERPRETATION':'SEPARATE HUMAN ASSESSMENT: '+String(entry.humanKind).toUpperCase()):String(entry.decision||'review').toUpperCase().replaceAll('_',' ');
      row.append(make('strong',label+' · '+entry.sourceId),make('p',(scripted?'Original scripted label: ':'Original model label: ')+String(entry.modelKind||entry.kind||'not specified').toUpperCase()+' · UNVERIFIED, retained, not rewritten'),make('blockquote',entry.quote||''),make('p',entry.note||''),make('small','Revision '+entry.sourceRevision+' · '+entry.sourceSHA256+' · '+(entry.appliesToCurrentSource===false?'STALE SOURCE':'CURRENT SOURCE REVISION')+' · Shipment agreement unchanged'));
      if(human&&entry.humanKind==='accept'){row.append(make('small','Self-reported checks · complete source: '+(entry.sourceReviewed===true?'yes':'not recorded')+' · quoted/negated/conditional context: '+(entry.conditionsQuotesChecked===true?'yes':'not recorded')+' · local-only limits: '+(entry.localInterpretationOnlyAcknowledged===true?'yes':'not recorded')));row.append(make('p','Human-reported local interpretation only. Reviewer identity is unverified; acceptance authority is none. Self-reported review, not authenticated counterparty, legal or operational acceptance. No dispatch; not linked to the authored three-party fixture.','muted small'));}
      auditBox.append(row);
    }
  }
  function choose(proposalId){
    clearAssessment();reason.value='';
    const proposal=snapshot?.proposals.find(p=>p.proposalId===proposalId);
    if(!proposal){selected=null;render();return;}
    const current=snapshot.sources.find(s=>s.id===proposal.sourceId);
    const source=(snapshot.sourceHistory||[]).find(s=>s.revisionId===proposal.sourceRevision)||(current?.revisionId===proposal.sourceRevision?current:null);
    selected=bound(source,proposal);selected.stale=!current||current.revisionId!==proposal.sourceRevision||current.sha256!==proposal.sourceSHA256;
    pick.value=proposal.proposalId;render();
  }
  async function request(path,data){
    const response=await fetch(path,data===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    const body=await response.json();if(!response.ok)throw Error('Advisory request refused');return body;
  }
  async function refresh(){
    const state=await request('/api/advisory');
    if(!state||!Array.isArray(state.sources)||!Array.isArray(state.proposals)||!Array.isArray(state.audit))throw Error('Audit schema');
    const prior=selected?.proposal.proposalId;snapshot=state;renderAudit(state);pick.replaceChildren();
    const empty=make('option','Choose a retained suggestion');empty.value='';pick.append(empty);
    for(const proposal of [...state.proposals].reverse()){
      const option=make('option',proposal.sourceId+' · '+String(proposal.observation?.kind||'unknown').toUpperCase()+' · '+proposal.mode);option.value=proposal.proposalId;pick.append(option);
    }
    writeUncertain=false;
    choose(prior||state.proposals.at(-1)?.proposalId||'');
  }
  async function action(fn){if(busy)return;busy=true;controls();try{await fn();}catch(error){selected=null;clearAssessment();render();status.textContent='Advisory review not confirmed. Reload the audit before deciding again. No automatic retry, model call or shipment change.';writeUncertain=true;}finally{busy=false;controls();}}
  load.addEventListener('click',()=>action(async()=>{
    const result=await request('/api/advisory/example',{});
    if(result.proposal?.mode!=='mock'||result.proposal.realInference!==false||result.proposal.recordedReplay!==false||result.authoredExample!==true||result.newInferenceCalls!==0)throw Error('Authored example provenance');
    selected=bound(result.source,result.proposal);render();await refresh();
    status.textContent='Authored synthetic review example loaded. Scripted mock, no model inference. Original 0/12 result unchanged; the suggestion remains unverified.';
  }));
  practice.addEventListener('click',()=>action(async()=>{
    const result=await request('/api/advisory/practice',{});
    if(result.proposal?.mode!=='mock'||result.proposal.realInference!==false||result.proposal.recordedReplay!==false||result.authoredPractice!==true||result.newInferenceCalls!==0)throw Error('Authored practice provenance');
    selected=bound(result.source,result.proposal);render();await refresh();
    status.textContent='Authored synthetic acceptance practice loaded. Scripted mock, no model inference. Any human assessment is your local interpretation only; original 0/12 unchanged.';
  }));
  reload.addEventListener('click',()=>action(async()=>{await refresh();status.textContent='Advisory audit refreshed. Historical model labels and human assessments remain separate.';}));
  pick.addEventListener('change',()=>{if(busy)return;try{choose(pick.value);reason.value='';clearAssessment();}catch(error){selected=null;render();status.textContent='Retained source binding is unavailable. No decision is permitted.';}});
  assessment.addEventListener('change',()=>{if(busy)return;clearAccept();controls();});
  for(const input of confirmations)input.addEventListener('change',()=>{if(!busy)controls();});
  function reviewPayload(){
    if(!selected||selected.stale||writeUncertain)throw Error('Current source required');
    const note=reason.value.trim();if(!note)throw Error('Review reason required');
    const {source,proposal}=selected,o=proposal.observation;
    return {actionId:crypto.randomUUID(),proposalId:proposal.proposalId,sourceRevision:source.revisionId,sourceSHA256:source.sha256,version:o.version,quote:o.quote,note};
  }
  async function submit(path,extra){
    if(!reason.value.trim()){status.textContent='Enter a reason grounded in the complete source before recording your review.';return;}
    await action(async()=>{
      const data={...reviewPayload(),...extra};const result=await request(path,data);
      if(result.entry?.agreementChanged!==false)throw Error('Unexpected authority change');
      if(data.humanKind==='accept'){
        const entry=result.entry;
        if(entry.humanKind!=='accept'||entry.scope!=='human-assessment-only'||entry.humanReported!==true||entry.interpretationAuthority!=='local-reviewer-only'||entry.noAuthenticatedCounterpartyAgreement!==true||entry.semanticVerified!==false||entry.sourceIdentityVerified!==false||entry.modelUnverified!==true||entry.reviewerIdentityVerified!==false||entry.acceptanceAuthority!=='none'||entry.sourceReviewed!==true||entry.conditionsQuotesChecked!==true||entry.localInterpretationOnlyAcknowledged!==true)throw Error('Unexpected human interpretation provenance');
      }
      reason.value='';clearAssessment();
      status.textContent='Review recorded. The original model label is retained; no shipment agreement or dispatch changed.';
      try{await refresh();}catch(error){status.textContent='Review recorded, but the audit display did not refresh. Reload the audit; do not repeat the review action.';writeUncertain=true;}
    });
  }
  for(const [element,decision] of [[approve,'approve'],[reject,'reject'],[clarify,'needs_clarification']])element.addEventListener('click',()=>{
    if(element.disabled||busy)return;
    if(decision==='approve'&&(selected?.proposal.candidate.reviewEligibility!=='manual-approval-permitted'||selected?.proposal.observation.kind==='accept'))return;
    return submit('/api/advisory/decision',{decision});
  });
  assess.addEventListener('click',()=>{
    if(assess.disabled||busy)return;
    if(!kinds.includes(assessment.value)){status.textContent='Choose your own interpretation before recording an assessment.';return;}
    if(assessment.value==='accept'){
      if(!acceptVersionBound()||!acceptConfirmed()){status.textContent='A current sole version and all three explicit confirmations are required. Nothing was recorded.';return;}
      if(Array.from(reason.value.trim()).length<12){status.textContent='Explain your own reading in at least 12 characters before recording an accept interpretation.';return;}
      return submit('/api/advisory/assessment',{humanKind:'accept',sourceReviewed:true,conditionsQuotesChecked:true,localInterpretationOnlyAcknowledged:true});
    }
    return submit('/api/advisory/assessment',{humanKind:assessment.value});
  });
  render();action(async()=>{await refresh();status.textContent='Separate advisory audit ready. No new model request was made.';});
})();
