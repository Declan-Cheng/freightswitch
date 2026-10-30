/* Preview-only disclosure, downloads and source-revision exercise. */
(()=>{
'use strict';
const banner=document.createElement('section');banner.className='preview-disclosure';banner.setAttribute('aria-label','Preview limitations');
const heading=document.createElement('h2');heading.textContent='Recorded-output interactive preview';
const notice=document.createElement('p');notice.textContent='Preview build · Synthetic fixtures · No live AI, carrier connection or dispatch. Scenario results were captured from the Python reference build. Human review below runs in this browser, not the Python/SQLite server.';
const storage=document.createElement('p');storage.textContent='Audit records stay in this browser only. They can be edited or cleared by the browser owner and are not authenticated, tamper-proof, cross-device records or a compliance guarantee. Export before clearing browser data.';
const source=document.createElement('small');source.textContent='Reference: '+FS_DEMO_DATA.reference.buildId+' · Preview: '+FS_DEMO_DATA.preview.buildId;
banner.append(heading,notice,storage,source);document.querySelector('main').prepend(banner);
const footer=document.querySelector('footer span');if(footer)footer.textContent='Browser-local synthetic preview · No live model calls or shipment authority';
const details=document.querySelector('.model-panel details');if(details)details.hidden=true;
const recorded=document.getElementById('recorded-review');if(recorded){recorded.hidden=true;recorded.disabled=true;}
const workshop=document.querySelector('.source-workshop');if(workshop)workshop.remove();
const panel=document.getElementById('advisory-panel');
const revision=document.createElement('details');revision.className='preview-revision';
const summary=document.createElement('summary');summary.textContent='Preview-only exercise: change the source and inspect stale-review protection';
const explain=document.createElement('p');explain.textContent='This changes only the authored practice source in this browser. It cannot generate a new interpretation or alter the shipment fixture. Existing proposals and audit entries remain linked to their original revision. Load authored practice again to restore the original source as a new revision.';
const label=document.createElement('label');label.textContent='Revised synthetic source';const textarea=document.createElement('textarea');textarea.id='preview-revision-body';textarea.maxLength=12000;textarea.rows=3;textarea.value=FS_DEMO_DATA.practice.source.body.replace('v6','v7');label.append(textarea);
const save=document.createElement('button');save.id='preview-revision-save';save.className='button light';save.textContent='Save preview source revision';
const result=document.createElement('p');result.id='preview-revision-status';result.setAttribute('role','status');
save.addEventListener('click',async()=>{save.disabled=true;textarea.disabled=true;try{const r=await fetch('/api/advisory/source',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:FS_DEMO_DATA.practice.source.id,senderLabel:FS_DEMO_DATA.practice.source.senderLabel,body:textarea.value})});const data=await r.json();if(!r.ok)throw Error(data.error);document.getElementById('advisory-refresh').click();result.textContent='New source revision saved. Old review evidence retained; old proposals must not authorize a decision. Shipment agreement unchanged.';}catch(e){result.textContent=e.message;}finally{save.disabled=false;textarea.disabled=false;}});
revision.append(summary,explain,label,save,result);panel.append(revision);
const exportStatus=document.createElement('p');exportStatus.id='preview-export-status';exportStatus.setAttribute('role','status');banner.append(exportStatus);
document.addEventListener('click',async event=>{const a=event.target.closest('a');if(!a)return;const u=new URL(a.href,location.href);if(u.origin!==location.origin||!u.pathname.startsWith('/api/')||!u.pathname.endsWith('export'))return;event.preventDefault();event.stopImmediatePropagation();try{if(a.id==='export'&&(!packet||loading))throw Error('Wait for the current scenario to finish loading');const r=await fetch(u.pathname+u.search);const data=await r.json();if(!r.ok)throw Error(data.error);if(a.id==='export'&&analysis){if(analysis.realInference===true||analysis.recordedReplay===true)throw Error('Only scripted mock output is included in this preview');data.advisory=analysis;}const blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),download=document.createElement('a');download.href=url;download.download=a.download||'FreightSwitch-browser-preview-evidence.json';download.click();setTimeout(()=>URL.revokeObjectURL(url),1000);exportStatus.textContent='Export prepared from this browser. Includes preview and Python-reference provenance; no shipment authority.';}catch(e){exportStatus.textContent='Export unavailable: '+e.message;}},true);
})();
