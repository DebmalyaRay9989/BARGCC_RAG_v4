import os,sys,json,base64
from pathlib import Path
from urllib.parse import urlparse
from fastapi.testclient import TestClient
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
from app.main import app
client=TestClient(app)
results=[]
with sync_playwright() as pw:
 browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
 def setup(auth=False):
  if auth:os.environ['BARG_ACCESS_TOKEN']='unit-test-token';os.environ['BARG_REQUIRE_TOKEN']='1'
  else:os.environ.pop('BARG_ACCESS_TOKEN',None);os.environ.pop('BARG_REQUIRE_TOKEN',None)
  ctx=browser.new_context(viewport={'width':1450,'height':950},accept_downloads=True)
  page=ctx.new_page();errors=[]
  page.on('pageerror',lambda error:errors.append(str(error)))
  def fetch_bridge(data):
   path=urlparse(str(data.get('url',''))).path or '/'; method=data.get('method','GET')
   headers={k:v for k,v in data.get('headers',{}).items() if k.lower() in ('content-type','x-barg-token')}
   content=data.get('body','')
   if method=='GET':resp=client.get(path,headers=headers)
   elif method=='POST':resp=client.post(path,content=content.encode('utf-8'),headers=headers)
   elif method=='DELETE':resp=client.delete(path,headers=headers)
   else:resp=client.request(method,path,headers=headers)
   return {'status':resp.status_code,'payload':base64.b64encode(resp.content).decode(), 'contentType':resp.headers.get('content-type','application/json')}
  page.expose_function('fetchBridge',fetch_bridge)
  page.goto('about:blank')
  page.set_content((root/'app/static/index.html').read_text(),wait_until='load')
  page.add_style_tag(content=(root/'app/static/styles.css').read_text())
  page.evaluate("window.__store={};Object.defineProperty(window,'sessionStorage',{value:{getItem:k=>window.__store[k]||null,setItem:(k,v)=>window.__store[k]=String(v),removeItem:k=>delete window.__store[k]}});")
  page.evaluate('''window.fetch=async function(url,opts={}){
   const item=await window.fetchBridge({url,method:opts.method||'GET',headers:opts.headers||{},body:opts.body||''});
   const binary=atob(item.payload);const buf=Uint8Array.from(binary,ch=>ch.charCodeAt(0));
   return new Response(buf,{status:item.status,headers:{'content-type':item.contentType}});
  };''')
  page.add_script_tag(content=(root/'app/static/app.js').read_text())
  page.evaluate('init()')
  return ctx,page,errors
 ctx,p,errors=setup(False)
 p.wait_for_function("document.querySelector('#metricRows').textContent !== '—'",timeout=30000)
 assert p.locator('#metricRows').inner_text()!='—'
 results.append('Auto-load demo and audit populates dashboard')
 assert p.locator('#bootNotice').count()==0
 results.append('Client bootstrap removes boot diagnostic')
 for tab in ('overview','audit','copilot','agent','data','research','deployment'):
  p.locator(f'[data-tab="{tab}"]').click();assert p.locator(f'#tab-{tab}').is_visible(),tab
 results.append('All seven sidebar tabs navigate')
 p.locator('#themeBtn').click();assert p.locator('html').get_attribute('data-theme')=='glacier'
 results.append('Theme switch changes colors')
 p.locator('#heroAgent').click() if p.locator('#heroAgent').is_visible() else p.locator('[data-tab="overview"]').click() or p.locator('#heroAgent').click()
 assert p.locator('#tab-copilot').is_visible()
 results.append('Hero Copilot button navigates')
 p.locator('[data-ragprompt]').first.click()
 p.wait_for_function("document.querySelectorAll('.rag-citation').length>0",timeout=30000)
 results.append('RAG prompt yields manuscript citations')
 p.locator('#ragClear').click();assert 'cleared' in p.locator('#ragCitations').inner_text().lower()
 results.append('Clear RAG chat works')
 p.locator('[data-tab="agent"]').click();p.locator('.quick-prompts button').first.click()
 p.wait_for_function("document.querySelectorAll('#agentTrace .trace-step').length===4",timeout=30000)
 results.append('Agent tool chain runs with four steps')
 p.locator('[data-tab="audit"]').click();p.locator('#strength').fill('0.5')
 assert 'Parameters changed' in p.locator('#activityStatus').inner_text()
 p.locator('#runAudit').click();p.wait_for_function("document.querySelector('#appliedK').textContent.startsWith('0.500')",timeout=30000)
 results.append('Sliders and manual audit apply new kappa')
 with p.expect_download(timeout=30000) as ev:p.locator('#exportPDF').click()
 assert ev.value.suggested_filename.endswith('.pdf')
 results.append('Export PDF returns generated PDF')
 with p.expect_download(timeout=30000) as ev:p.locator('#exportCSV').click()
 assert ev.value.suggested_filename.endswith('.csv')
 results.append('Export affected CSV works')
 with p.expect_download(timeout=30000) as ev:p.locator('#exportJSON').click()
 results.append('Export report JSON works')
 p.locator('[data-tab="data"]').click();p.locator('#clearDataset').click()
 p.wait_for_function("document.querySelector('#metricRows').textContent==='—'",timeout=15000)
 results.append('Clear dataset resets dashboard')
 p.locator('#loadDemo').click();p.wait_for_function("document.querySelector('#metricRows').textContent!=='—'",timeout=30000)
 results.append('Load public Digits demo restores dashboard')
 p.locator('#connectBtn').click();assert p.locator('#connectionPanel').is_visible();p.locator('#connectBtn').click()
 results.append('Manual connection panel opens and closes')
 p.locator('[data-tab="overview"]').click()
 p.screenshot(path=str(root/'docs'/'fixed_dashboard_preview.png'),full_page=True)
 assert not errors,errors
 results.append('No browser page errors (open local mode)')
 p.locator('[data-tab="deployment"]').click();p.locator('#runDiagnostics').click()
 p.wait_for_function("document.querySelector('#diagnosticsResults').textContent.includes('PASS')",timeout=30000)
 results.append('New deployment self-test executes and reports live invariants')
 p.locator('[data-tab="audit"]').click()
 with p.expect_download(timeout=30000) as ev:p.locator('#exportBundle').click()
 assert ev.value.suggested_filename.endswith('.zip')
 results.append('New evidence bundle downloads from backend')
 p.locator('[data-tab="copilot"]').click();p.locator('[data-ragprompt]').first.click()
 p.wait_for_function("document.querySelectorAll('.source-preview-btn').length>0",timeout=30000)
 results.append('New protected PDF view buttons are visible on cited results')
 p.locator('[data-tab="overview"]').click()
 p.screenshot(path=str(root/'docs'/'v3_dashboard_preview.png'),full_page=True)
 p.locator('[data-tab="copilot"]').click()
 p.screenshot(path=str(root/'docs'/'v3_copilot_preview.png'),full_page=True)
 p.locator('[data-tab="deployment"]').click()
 p.screenshot(path=str(root/'docs'/'v3_diagnostics_preview.png'),full_page=True)

 ctx.close()
 # Test Render locked token flow
 ctx,p,errors=setup(True)
 p.wait_for_function("!document.querySelector('#connectionPanel').classList.contains('hidden')",timeout=20000)
 assert p.locator('#metricRows').inner_text()=='—'
 results.append('Locked Render workspace displays explicit access panel')
 p.locator('#connectionToken').fill('unit-test-token');p.locator('#connectionSubmit').click()
 p.wait_for_function("document.querySelector('#metricRows').textContent!=='—'",timeout=30000)
 assert p.locator('#connectionPanel').get_attribute('class').find('hidden')>=0
 results.append('Correct access token unlocks and loads demo')
 p.locator('[data-tab="copilot"]').click()
 p.locator('[data-ragprompt]').first.click()
 p.wait_for_function("document.querySelectorAll('.rag-citation').length>0",timeout=30000)
 results.append('Authenticated RAG chat returns citations')
 assert not errors,errors
 results.append('No browser errors in authenticated Render configuration')
 p.screenshot(path=str(root/'docs'/'fixed_rag_preview.png'),full_page=True)
 ctx.close();browser.close()
print(json.dumps({'checks':len(results),'results':results},indent=2))
