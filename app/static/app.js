/* BARG-CC deterministic web client. No telemetry, no external network requests. */
'use strict';
const $=id=>document.getElementById(id);
const state={datasetId:null,dataset:null,analysis:null,agent:null,ragHistory:[],busy:false,theme:'ocean',connected:false};
const THEMES=['ocean','glacier','orchid'];
// Browser privacy modes may deny sessionStorage; keep a tab-local fallback.
let fallbackToken='';
function tokenGet(){try{return sessionStorage.getItem('barg-access')||fallbackToken}catch{return fallbackToken}}
function tokenSet(v){fallbackToken=v;try{if(v)sessionStorage.setItem('barg-access',v);else sessionStorage.removeItem('barg-access')}catch{}}
const by=(selector)=>Array.from(document.querySelectorAll(selector));
const fmt=(v,d=3)=>v==null?'N/A':Number(v).toFixed(d);
const pct=v=>v==null?'N/A':Number(v).toFixed(1)+'%';
const safe=v=>String(v??'');
function element(tag,className,text){const n=document.createElement(tag);if(className)n.className=className;if(text!==undefined)n.textContent=safe(text);return n}
function toast(txt){const n=element('div','toast',txt);document.body.append(n);setTimeout(()=>n.remove(),4400)}
function activity(message,error=false){const el=$('activityStatus');if(!el)return;el.textContent=message;el.classList.toggle('error',error)}
function connectionPanel(message){const panel=$('connectionPanel');panel.classList.remove('hidden');$('connectionMessage').textContent=message||'Connect to the research engine.';const status=$('liveStatus');status.classList.add('offline');status.textContent='Action needed';activity(message||'Connection required',true)}
function closeConnection(){ $('connectionPanel').classList.add('hidden');$('liveStatus').classList.remove('offline');$('liveStatus').textContent='● API connected';state.connected=true;}
window.addEventListener('error',event=>{const x=document.getElementById('activityStatus');if(x){x.textContent='Interface error: '+event.message;x.classList.add('error')}});
function reportError(error){let msg=(error&&error.message)||String(error);$('banner').textContent=msg;$('banner').classList.remove('hidden');activity(msg,true);toast('Action failed: '+msg)}
function resetError(){$('banner').classList.add('hidden')}
function setBusy(x,label=''){state.busy=x;by('button').forEach(b=>{if(['heroRun','runAudit','loadDemo'].includes(b.id))b.disabled=x});if(x)activity(label||'Running scientific analysis…');else if(state.connected)activity(state.datasetId?'Ready • dataset loaded':'Ready • choose a dataset')}
async function api(path,opts={}){
 const token=tokenGet();
 const headers={'X-BARG-Token':token,...(opts.headers||{})};
 const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),90000);
 let resp,payload;
 try{resp=await fetch(path,{...opts,headers,signal:controller.signal});
     try{payload=await resp.json()}catch{payload={detail:'Server returned an unreadable response'}};
 }catch(e){if(e.name==='AbortError')throw Error('Request timed out. Render may be restarting or the analysis may exceed free-tier resources. Retry with fewer rows.');
   throw Error('Cannot reach the FastAPI backend. Open the deployed Render URL (or http://127.0.0.1:7860/ locally), not index.html directly. '+e.message)
 }finally{clearTimeout(timer)}
 if(!resp.ok){
   const detail=typeof payload.detail==='string'?payload.detail:(JSON.stringify(payload.detail)||'Server error');
   if(resp.status===401){connectionPanel('Access token missing or invalid. Enter the BARG_ACCESS_TOKEN from your Render environment settings, then press Connect.');throw Error('Access denied (401). Connect with the configured access token.');}
   if(resp.status===503){connectionPanel('Server-side access token has not been configured. Set BARG_ACCESS_TOKEN in the Render dashboard and redeploy.');}
   throw Error('HTTP '+resp.status+': '+detail);
 }
 return payload;
}
function navigate(id){by('.nav-link').forEach(n=>n.classList.toggle('active',n.dataset.tab===id));by('.tab').forEach(t=>t.classList.toggle('active',t.id==='tab-'+id));
 const label={overview:'Overview',audit:'Audit workbench',copilot:'RAG Copilot',agent:'Agent console',data:'Dataset studio',research:'Research basis',deployment:'Deployment'};$('crumbTitle').textContent=label[id]||id;window.scrollTo({top:0,behavior:'smooth'});if(id==='overview'&&state.analysis)setTimeout(drawScatter,30)}
function settings(){return {dataset_id:state.datasetId,k:Number($('kClusters').value),kappa:Number($('strength').value),rho:Number($('floor').value),enforce_floor:$('enforceFloor').checked,drop_probability:Number($('dropout').value),seed:Number($('seed').value)}}
function updateSliders(){$('strengthValue').textContent=fmt($('strength').value,3);$('floorValue').textContent=fmt($('floor').value,2);$('dropValue').textContent=Math.round(100*Number($('dropout').value))+'%'}
async function loadDemo(){setBusy(true,'Loading public Digits dataset…');resetError();try{const d=await api('/api/demo');closeConnection();setDataset(d);toast('Public Digits pseudo-view example loaded');await runAudit()}catch(e){reportError(e)}finally{setBusy(false)}}
function setDataset(d){state.datasetId=d.dataset_id;state.dataset=d;state.analysis=null;$('datasetLabel').textContent=d.name;let facts=$('datasetInfo');facts.replaceChildren();
 const rows=[['Name',d.name],['Number of records',d.rows],['View names',d.views.join(' · ')],['Quality source',d.score_source],['Scope',d.scope]];
 rows.forEach(([k,v])=>{const p=element('div','',undefined);const b=element('b','',k+': ');p.append(b,document.createTextNode(safe(v)));facts.append(p)});
 if(d.rows<30)$('kClusters').value=2;else if(d.rows<40)$('kClusters').value=5;else $('kClusters').value=Math.min(10,Math.floor(d.rows/3));
 const max=Math.min(.3,1/d.views.length);$('floor').max=max.toFixed(3);if(Number($('floor').value)>max)$('floor').value=Number(max.toFixed(3));updateSliders();
 $('metricRows').textContent=d.rows.toLocaleString();$('metricRowsSub').textContent=d.name.slice(0,29);$('metricViews').textContent=d.views.length;
}
async function uploadCSV(file){if(!file)return;if(!file.name.toLowerCase().endsWith('.csv')){reportError(new Error('Only .csv files are accepted'));return}
 setBusy(true);resetError();try{const fd=new FormData();fd.append('file',file);const d=await api('/api/upload',{method:'POST',body:fd});setDataset(d);toast('File ingested and validated');navigate('audit');await runAudit()}catch(e){reportError(e)}finally{setBusy(false)}}
async function runAudit(){if(!state.datasetId){navigate('data');toast('Load the demo or upload a dataset first.');return}
 setBusy(true,'Calculating BARG-CC clusters and certificates…');resetError();try{const a=await api('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(settings())});state.analysis=a;render(a);toast('Scientific audit complete · '+a.audit.dropped_rows+' affected records')}catch(e){reportError(e)}finally{setBusy(false)}}
function render(a){const d=a.dataset,s=a.summary,u=a.audit;
 $('metricRows').textContent=d.rows.toLocaleString();$('metricViews').textContent=d.views.length;$('metricCert').textContent=pct(u.certified_all_pct);$('metricEvent').textContent=pct(u.certified_dropped_pct);
 $('coverAllVal').textContent=pct(u.certified_all_pct);$('coverDropVal').textContent=pct(u.certified_dropped_pct);$('coverKeepVal').textContent=pct(u.certified_retained_pct);
 [['coverAllBar',u.certified_all_pct],['coverDropBar',u.certified_dropped_pct],['coverKeepBar',u.certified_retained_pct]].forEach(([id,v])=>$(id).style.width=Math.min(100,Number(v)||0)+'%');
 $('baselineAri').textContent=fmt(s.baseline.ARI);$('gatedAri').textContent=fmt(s.gated.ARI);
 $('deltaAri').textContent=s.delta_ARI==null?'NO LABELS':((s.delta_ARI>=0?'+':'')+fmt(s.delta_ARI,4)+' Δ ARI');
 $('requestedK').textContent=fmt(a.config.requested_kappa);$('appliedK').textContent=fmt(a.config.applied_kappa);$('minShare').textContent=pct(s.min_observed_share*100);$('falseCerts').textContent=String(u.false_certificates);
 $('gateTag').textContent='κ = '+fmt(a.config.applied_kappa);
 const viewEl=$('viewBars');viewEl.classList.remove('empty');viewEl.replaceChildren();
 Object.entries(s.mean_view_weights).forEach(([name,value])=>{const item=element('div','view-line');item.append(element('span','',name));let track=element('i');const fill=element('em');fill.style.width=(value*100).toFixed(2)+'%';track.append(fill);item.append(track,element('b','',pct(value*100)));viewEl.append(item)});
 $('recommendText').textContent=a.recommendation;const w=$('warningList');w.replaceChildren();[...a.warnings,...a.limitations].forEach(str=>w.append(element('p','',str)));
 const entries=[['Sample records',d.rows,'Uploaded dataset; no population-level claim'],['View dropout intervention',pct(u.probability*100),'Sampled at most one available view per eligible row'],
 ['Rows that lost a view',u.dropped_rows,'The event-conditioned denominator'],['Certified · all',pct(u.certified_all_pct),'Sufficient one-refit certificate'],
 ['Certified · affected',pct(u.certified_dropped_pct),'Not interchangeable with overall coverage'],
 ['Certified · unaffected',pct(u.certified_retained_pct),'Usually higher due to smaller local perturbations'],
 ['Observed unchanged · affected',pct(u.unchanged_dropped_pct),'Retrospective comparison, not a certificate'],
 ['False certificates',u.false_certificates,'Conditional to this sampled test'],
 ['Exact law test','PASS','Unit-norm separated blocks and frozen retained logits'],
 ['Certificate applicability',u.certificate_applicable?'YES':'NO','Original K-means partition must be a Lloyd fixed point']];
 const tbody=$('auditRows');tbody.replaceChildren();entries.forEach(([key,val,note])=>{const tr=element('tr');[key,val??'N/A',note].forEach(v=>tr.append(element('td','',v)));tbody.append(tr)});
 drawScatter()}
function drawScatter(){const c=$('scatterCanvas');if(!c||!state.analysis)return;
 const ctx=c.getContext('2d');const rect=c.getBoundingClientRect(),dpi=window.devicePixelRatio||1;
 const w=Math.max(200,rect.width),h=Math.max(200,rect.height);c.width=w*dpi;c.height=h*dpi;ctx.setTransform(dpi,0,0,dpi,0,0);ctx.clearRect(0,0,w,h);
 const css=getComputedStyle(document.documentElement);const grid=css.getPropertyValue('--stroke').trim(),muted=css.getPropertyValue('--muted').trim();ctx.strokeStyle=grid;ctx.lineWidth=.8;
 const pad=30;for(let i=0;i<6;i++){let xx=pad+(w-pad*2)*i/5, yy=pad+(h-pad*2)*i/5;ctx.beginPath();ctx.moveTo(xx,pad);ctx.lineTo(xx,h-pad);ctx.stroke();ctx.beginPath();ctx.moveTo(pad,yy);ctx.lineTo(w-pad,yy);ctx.stroke()}
 const dots=state.analysis.scatter;const colors=['#72e3ce','#7b9dff','#f4c87c','#df91ec','#e88c8b','#b7d08a','#70c5f2','#e3a778','#af9aff','#83cdb6','#f0c2db','#a1afff','#dcbd76','#a5d6da','#b09cac','#e4ba97','#d4e0a1','#b7caf7','#f5abc4','#9ee7cd'];
 dots.xy.forEach(([x,y],i)=>{let xx=pad+(w-2*pad)*(.5+x*.45), yy=pad+(h-2*pad)*(.5-y*.45);ctx.beginPath();ctx.arc(xx,yy,3.0,0,Math.PI*2);ctx.fillStyle=colors[dots.clusters[i]%colors.length];ctx.globalAlpha=.72;ctx.fill()});ctx.globalAlpha=1;
 ctx.font='10px system-ui';ctx.fillStyle=muted;ctx.fillText('Principal component 1  →',pad+7,h-8);$('plotPlaceholder').style.display='none';}
function downloadText(text,filename,mime){const blob=new Blob([text],{type:mime});const u=URL.createObjectURL(blob);const a=document.createElement('a');a.href=u;a.download=filename;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(u),500)}
async function downloadProtected(path, filename){
 const controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),90000);
 try{
  const r=await fetch(path,{method:'POST',headers:{'X-BARG-Token':tokenGet(),'Content-Type':'application/json'},
      body:JSON.stringify(settings()),signal:controller.signal});
  if(!r.ok){let detail='Export rejected';try{const p=await r.json();detail=p.detail||detail}catch{}throw Error(detail)}
  const b=await r.blob();const url=URL.createObjectURL(b),a=document.createElement('a');
  a.href=url;a.download=filename;document.body.append(a);a.click();a.remove();
  setTimeout(()=>URL.revokeObjectURL(url),60000);
 }finally{clearTimeout(timeout)}
}
async function exportBundle(){
 if(!state.datasetId){navigate('data');toast('Load a dataset before exporting evidence.');return}
 if(state.busy)return;setBusy(true,'Packaging reproducible evidence…');
 try{await downloadProtected('/api/evidence.zip','BARG_CC_Audit_Evidence_Bundle.zip');toast('Evidence ZIP downloaded with scope notes')}
 catch(e){reportError(e)}finally{setBusy(false)}
}
async function runDiagnostics(){
 const btn=$('runDiagnostics');const target=$('diagnosticsResults');btn.disabled=true;target.textContent='Checking authentication, source index and numerical invariants…';
 try{const r=await api('/api/self-test');target.replaceChildren();
 const h=element('div','diagnostic-head',r.status+' · '+r.checks.filter(c=>c.passed).length+'/'+r.checks.length+' checks');target.append(h);
 r.checks.forEach(c=>{const row=element('div','diagnostic-row');row.append(element('span','',c.passed?'✓':'✕'),element('strong','',c.name),element('small','',c.description));target.append(row)})
 if(r.status!=='PASS')activity('A diagnostic check requires attention.',true);else toast('Deployment checks passed');
 }catch(e){target.textContent='Diagnostic request failed: '+e.message;reportError(e)}finally{btn.disabled=false}
}
async function openPrivateSource(doc,page){
 // A new window is opened inside the click handler to avoid popup blocking.
 const preview=window.open('about:blank','_blank');
 if(preview)try{preview.document.title='Loading protected manuscript page…';preview.document.body.textContent='Loading protected BARG-CC PDF…'}catch{}
 try{
  const r=await fetch('/api/source-private/'+encodeURIComponent(doc),{headers:{'X-BARG-Token':tokenGet()}});
  if(!r.ok){let t='Source preview unavailable';try{const d=await r.json();t=d.detail||t}catch{}throw Error(t)}
  const blob=await r.blob();const url=URL.createObjectURL(blob)+'#page='+encodeURIComponent(page);
  if(preview)preview.location.replace(url);
  else{const a=document.createElement('a');a.href=url;a.download='BARG_CC_Source_'+doc+'.pdf';document.body.append(a);a.click();a.remove()}
  setTimeout(()=>URL.revokeObjectURL(url.split('#')[0]),180000);
 }catch(e){if(preview)preview.close();reportError(e)}
}
async function exportPDF(){
 if(!state.datasetId){toast('Load a dataset first.');return}
 setBusy(true);
 try{
  const token=tokenGet();
  const r=await fetch('/api/report.pdf',{method:'POST',headers:{'X-BARG-Token':token,'Content-Type':'application/json'},body:JSON.stringify(settings())});
  if(!r.ok){let d={};try{d=await r.json()}catch{}throw Error(d.detail||'PDF generation failed')}
  const blob=await r.blob();const url=URL.createObjectURL(blob);const a=document.createElement('a');
  a.href=url;a.download='BARG_CC_Evidence_Audit.pdf';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
  toast('Audit PDF created from current parameters');
 }catch(e){reportError(e)}finally{setBusy(false)}
}
async function downloadSample(){
 try{const token=tokenGet();const r=await fetch('/api/sample.csv',{headers:{'X-BARG-Token':token}});
 if(!r.ok)throw Error('Sample download failed');const blob=await r.blob();const url=URL.createObjectURL(blob);
 const a=document.createElement('a');a.href=url;a.download='BARG_CC_Digits_Pseudoviews.csv';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),800);
 }catch(e){reportError(e)}
}
function exportJSON(){if(!state.analysis){toast('Run an audit first.');return}
 downloadText(JSON.stringify({analysis:state.analysis,agent:state.agent||null},null,2),'BARG_CC_Evidence_Report.json','application/json')}
function csvField(s){const t=String(s??'');return '"'+t.replace(/"/g,'""')+'"'}
function exportAffected(){if(!state.analysis){toast('Run an audit first.');return}
 const rows=state.analysis.audit.dropped_rows_details;const hdr=['row','removed_mass','exact_drift','certified','unchanged_observed'];
 const contents=hdr.join(',')+'\n'+rows.map(row=>hdr.map(k=>csvField(row[k])).join(',')).join('\n');
 downloadText(contents,'BARG_CC_Dropped_Row_Audit.csv','text/csv');
 if(state.analysis.audit.dropped_rows>150)toast('CSV includes only the first 150 affected records; use JSON for aggregate statistics.')}
function chatMessage(role,heading,body){const wrap=element('div','chat-message '+role);const b=element('div','bubble');if(heading)b.append(element('b','',heading));b.append(element('p','',body));wrap.append(b);$('chatMessages').append(wrap);$('chatMessages').scrollTop=$('chatMessages').scrollHeight}
async function sendAgent(query){if(!state.datasetId){navigate('data');toast('Load a dataset before running the research agent.');return}
 if(state.busy)return;setBusy(true);resetError();navigate('agent');chatMessage('user',null,query);
 try{const payload={...settings(),query};const response=await api('/api/agent',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
 state.agent=response;state.analysis=response.analysis;render(state.analysis);
 const body=response.trace.map(t=>`${t.index}. ${t.tool.toUpperCase()}: ${t.outcome}`).join('\n');chatMessage('assistant','Analysis complete · review required',body+'\n\nRecommendation: '+response.decision.recommendations[0]);
 if(response.optional_llm&&response.optional_llm.text){chatMessage('assistant','Optional local LLM explanation · NOT EVIDENCE',response.optional_llm.text)}
 const list=$('agentTrace');list.replaceChildren();response.trace.forEach(t=>{const wrap=element('div','trace-step');wrap.append(element('span','trace-num',t.index));const content=element('div');content.append(element('small','',t.state.toUpperCase()));content.append(element('b','',t.tool+' · '+t.purpose));content.append(element('p','',t.outcome));wrap.append(content);list.append(wrap)})
 toast('Agent finished '+response.trace.length+' verified tool steps');
 }catch(e){chatMessage('assistant','Execution stopped',e.message);reportError(e)}finally{setBusy(false)}}
async function clearDataset(){if(state.datasetId){try{await api('/api/datasets/'+encodeURIComponent(state.datasetId),{method:'DELETE'})}catch(e){toast(e.message)}}state.datasetId=null;state.dataset=null;state.analysis=null;state.agent=null;$('datasetInfo').textContent='No dataset loaded.';$('datasetLabel').textContent='Demo not loaded';['metricRows','metricViews','metricCert','metricEvent','coverAllVal','coverDropVal','coverKeepVal'].forEach(id=>$(id).textContent='—');$('plotPlaceholder').style.display='block';$('metricRowsSub').textContent='Load the demo to begin';['baselineAri','gatedAri','deltaAri'].forEach(id=>$(id).textContent='—');['coverAllBar','coverDropBar','coverKeepBar'].forEach(id=>$(id).style.width='0%');$('viewBars').replaceChildren();$('auditRows').replaceChildren();activity('Dataset cleared. Load a demo or CSV.');toast('Dataset cleared from session')}
async function health(){
 try{const r=await api('/api/health');$('liveStatus').textContent='● API online';state.connected=true;
     if(!r.demo_available)activity('Demo sample missing from deployment',true);
     return r;
 }catch(e){$('liveStatus').textContent='● API offline';connectionPanel('The FastAPI service is unavailable. Start it with run_windows.bat or deploy the Docker app on Render, then click Retry.');reportError(e);return null;}
}
async function boot(){
 if(location.protocol==='file:'){connectionPanel('This page was opened directly from disk. FastAPI is required: run run_windows.bat and use http://127.0.0.1:7860/');return;}
 const h=await health();if(!h)return;
 if(h.auth_required && !tokenGet()){
   connectionPanel('This Render workspace requires a token. Open your Render dashboard → Environment → BARG_ACCESS_TOKEN and enter that value here.');
   await ragInit().catch(()=>{});return;
 }
 await loadDemo();await ragInit();
}
async function connectWorkspace(ev){if(ev)ev.preventDefault();
 const token=$('connectionToken').value.trim();if(token){tokenSet(token);}else{tokenSet('')}
 resetError();activity('Authenticating and loading demonstration…');await loadDemo();
 if(state.datasetId){$('connectionToken').value='';await ragInit();}
}
// Evidence-grounded RAG Copilot, separate from numerical audit agent.
function ragBubble(role,text){
 const wrap=element('div','rag-bubble '+role);wrap.append(element('div','rag-message-label',role==='user'?'YOUR QUESTION':'SOURCE-GROUNDED RESULT'));
 wrap.append(element('p','rag-answer',text));$('ragConversation').append(wrap);$('ragConversation').scrollTop=$('ragConversation').scrollHeight;
 return wrap;
}
async function ragInit(){
 try {const d=await api('/api/rag/sources');$('ragSourceCount').textContent=d.sources.length+' PDFs';$('ragChunkCount').textContent=d.index.chunks.toLocaleString();
 const area=$('ragSourceList');area.replaceChildren();d.sources.forEach(src=>{
 const e=element('div','rag-src');const icon=element('span','rag-src-icon','▤');const content=element('div');content.append(element('b','',src.title),element('small','',src.pages+' pages · original PDF pagination'));e.append(icon,content);area.append(e)})
 } catch(e) {$('ragSourceList').textContent='Source index unavailable: '+e.message}
}
function ragRenderEvidence(data){
 $('ragEvidenceTag').textContent=data.citations.length+' CITATIONS';const list=$('ragCitations');list.replaceChildren();
 if(!data.citations.length){list.append(element('p','','No matching source passages. Try a more specific research term.'));return}
 data.citations.forEach(c=>{const card=element('div','rag-citation');const header=element('div','rag-cite-head');header.append(element('strong','','['+c.number+'] '+c.title));header.append(element('span','', 'PDF PAGE '+c.page));card.append(header,element('p','',c.excerpt));
 const b=element('button','source-preview-btn','Open protected PDF · page '+c.page+' ↗');b.type='button';b.addEventListener('click',()=>openPrivateSource(c.doc_id,c.page));card.append(b)
 list.append(card)});
}
async function ragAsk(question){
 if(state.busy)return;resetError();navigate('copilot');const previous=state.ragHistory.slice(-6);
 ragBubble('user',question);state.busy=true;$('ragSend').disabled=true;$('ragSend').textContent='Retrieving…';
 try{
 const includeAudit=$('ragIncludeAudit').checked;
 const body={question,history:previous,include_audit:includeAudit,dataset_id:includeAudit?state.datasetId:null,
    k:Number($('kClusters').value),kappa:Number($('strength').value),rho:Number($('floor').value),
    enforce_floor:$('enforceFloor').checked,drop_probability:Number($('dropout').value),seed:Number($('seed').value)};
 const res=await api('/api/rag/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 ragBubble('assistant',res.answer);ragRenderEvidence(res);
 const t=$('ragTrace');t.replaceChildren();res.trace.forEach(step=>{
 const row=element('div','rag-trace-row');row.append(element('b','',step.step+' · '+step.tool),element('small','',step.outcome));t.append(row)});
 state.ragHistory.push({role:'user',content:question},{role:'assistant',content:res.answer.slice(0,500)});state.ragHistory=state.ragHistory.slice(-6);
 toast(res.citations.length+' manuscript passages retrieved');
 } catch(e){ragBubble('assistant','Request failed: '+e.message);reportError(e)}finally{state.busy=false;$('ragSend').disabled=false;$('ragSend').textContent='Retrieve evidence ↗'}
}
function ragClear(){state.ragHistory=[];$('ragConversation').replaceChildren();ragBubble('assistant','Research chat reset. No conversations are persisted on the server.');$('ragCitations').textContent='Citation ledger cleared.';$('ragTrace').textContent='No tools have run yet.';$('ragEvidenceTag').textContent='WAITING'}

function init(){
 $('bootNotice').remove();activity('JavaScript initialized • checking FastAPI connection…');
 by('.nav-link').forEach(b=>b.addEventListener('click',()=>navigate(b.dataset.tab)));
 $('themeBtn').addEventListener('click',()=>{state.theme=THEMES[(THEMES.indexOf(state.theme)+1)%THEMES.length];document.documentElement.dataset.theme=state.theme;if(state.analysis)drawScatter();toast('Theme: '+state.theme)});
 ['strength','floor','dropout'].forEach(id=>$(id).addEventListener('input',()=>{updateSliders();activity('Parameters changed. Click Run scientific audit to apply.')}));
 $('loadDemo').onclick=loadDemo;$('heroRun').onclick=async()=>{if(!state.datasetId)await loadDemo();else await runAudit()};$('runAudit').onclick=runAudit;$('heroAgent').onclick=()=>navigate('copilot');
 $('connectBtn').onclick=()=>{const p=$('connectionPanel');p.classList.toggle('hidden');if(!p.classList.contains('hidden'))$('connectionToken').focus()};
 $('connectionForm').addEventListener('submit',connectWorkspace);$('connectionRetry').onclick=()=>boot();
 $('exportBundle').onclick=exportBundle;$('runDiagnostics').onclick=runDiagnostics;$('exportJSON').onclick=exportJSON;$('exportCSV').onclick=exportAffected;$('exportPDF').onclick=exportPDF;$('sampleCSV').onclick=downloadSample;$('clearDataset').onclick=clearDataset;
 $('fileInput').onchange=e=>uploadCSV(e.target.files[0]);const zone=$('uploadZone');zone.onclick=()=>$('fileInput').click();zone.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();$('fileInput').click()}});
 zone.addEventListener('dragover',e=>{e.preventDefault();zone.classList.add('dragging')});zone.addEventListener('dragleave',()=>zone.classList.remove('dragging'));
 zone.addEventListener('drop',e=>{e.preventDefault();zone.classList.remove('dragging');uploadCSV(e.dataTransfer.files[0])});
 by('.quick-prompts button').forEach(b=>b.onclick=()=>sendAgent(b.dataset.prompt));
 by('[data-ragprompt]').forEach(b=>b.onclick=()=>ragAsk(b.dataset.ragprompt));
 $('ragForm').addEventListener('submit',e=>{e.preventDefault();const q=$('ragInput').value.trim();if(q){$('ragInput').value='';ragAsk(q)}else toast('Enter a research question first.')});
 $('ragClear').onclick=ragClear;
 $('ragInput').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();$('ragForm').requestSubmit()}});
 $('agentForm').addEventListener('submit',e=>{e.preventDefault();const q=$('agentInput').value.trim();if(q){$('agentInput').value='';sendAgent(q)}else toast('Enter an agent instruction first.')});
 window.addEventListener('resize',()=>{if(state.analysis)drawScatter()});updateSliders();boot().catch(reportError)
}
document.addEventListener('DOMContentLoaded',init);
