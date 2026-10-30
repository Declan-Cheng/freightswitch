// Uses real application scripts with a minimal DOM/fetch test double.
// This is deterministic UI logic regression coverage, not browser visual QA.
'use strict';
const assert=require('assert/strict'),fs=require('fs'),vm=require('vm'),path=require('path');
const root=path.resolve(__dirname,'..');
const flush=()=>new Promise(resolve=>setImmediate(resolve));
function harness(file){
  const elements=new Map(),pending=[];
  function element(id){if(!elements.has(id))elements.set(id,{id,disabled:false,textContent:'',value:'',listeners:{},addEventListener(type,fn){this.listeners[type]=fn;},replaceChildren(){},append(){},classList:{toggle(){}}});return elements.get(id);}
  const context=vm.createContext({document:{getElementById:element,querySelectorAll:()=>[],createElement:tag=>element('new-'+tag),createTextNode:text=>({textContent:text})},
    fetch:(url,options)=>new Promise((resolve,reject)=>pending.push({url,options,resolve:body=>resolve({ok:true,json:async()=>body}),reject})),
    console,setTimeout,crypto:{randomUUID:()=> 'dev-action'}});
  vm.runInContext(fs.readFileSync(path.join(root,'static',file),'utf8'),context);
  return {elements,element,pending,context,exec:s=>vm.runInContext(s,context)};
}
async function sceneNewestWins(){
  const h=harness('app.js');h.exec('render=()=>{}');
  const later=h.exec('load(11)');
  assert.equal(h.pending.length,2);h.pending[1].resolve({tag:'newest'});await later;
  h.pending[0].resolve({tag:'old'});await flush();
  assert.equal(h.exec('packet.tag'),'newest');assert.equal(h.exec('currentCount'),11);assert.equal(h.exec('loading'),false);
}
async function oldFailureCannotClearNewLoading(){
  const h=harness('app.js');h.exec('render=()=>{}');const later=h.exec('load(19)');
  h.pending[0].reject(Error('outdated failure'));await flush();
  assert.equal(h.exec('loading'),true);assert.equal(h.element('load-status').textContent,'Loading evidence…');
  h.pending[1].resolve({tag:'newest'});await later;assert.equal(h.exec('currentCount'),19);assert.equal(h.exec('loading'),false);
}
async function reviewInputFreeze(){
  const h=harness('review.js');h.pending[0].resolve({audit:[]});await flush();
  h.element('review-source-id').value='synthetic';h.element('review-sender').value='Fictional sender';h.element('review-body').value='I received v27.';
  const operation=h.element('review-save').listeners.click();
  for(const id of ['review-source-id','review-sender','review-body','review-note','review-save'])assert.equal(h.element(id).disabled,true,id);
  h.pending[1].resolve({source:{id:'synthetic',body:'I received v27.',revisionId:'revision',sha256:'test-hash'}});await flush();
  assert.equal(h.pending[2].url,'/api/review');h.pending[2].resolve({audit:[]});await operation;
  for(const id of ['review-source-id','review-sender','review-body','review-note','review-save'])assert.equal(h.element(id).disabled,false,id);
  assert.equal(h.element('review-mock').disabled,false);
}
const cases={sceneNewestWins,oldFailureCannotClearNewLoading,reviewInputFreeze};
(async()=>{assert.ok(cases[process.argv[2]]);await cases[process.argv[2]]();console.log(process.argv[2]+' passed (test doubles; no browser/network/model).');})().catch(error=>{console.error(error);process.exitCode=1;});
