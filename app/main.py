"""FastAPI service for the deployable BARG-CC audit platform."""
from __future__ import annotations
import os
import io
import json
import csv
import zipfile
import time
import uuid
from pathlib import Path
from typing import Any
from fastapi import FastAPI, Request, UploadFile, File, HTTPException, Depends
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .core import DataBundle, from_csv, analyze, masked_gate, floor_bound
from .agent import run_agent
from .reporting import make_report
from .rag import list_sources, inspect_index
from .rag_agent import run_research

ROOT=Path(__file__).resolve().parent.parent
STATIC=Path(__file__).resolve().parent/'static'
SAMPLE=ROOT/'samples'/'digits_three_derived_pseudoviews.csv'
MAX_FILE=3_000_000
TTL_SEC=3600
STORAGE:dict[str,tuple[float,DataBundle]]={}
app=FastAPI(title='BARG-CC Research Operations API',version='4.0.0',
            description='Bounded reliability gating and conditional certification research workbench')
app.mount('/static',StaticFiles(directory=STATIC),name='static')

@app.middleware('http')
async def security_headers(request:Request,call_next):
    try:
        resp=await call_next(request)
    except Exception:
        raise
    resp.headers['X-Content-Type-Options']='nosniff'
    resp.headers['X-Robots-Tag']='noindex, nofollow, noarchive'
    resp.headers['X-Frame-Options']='DENY'
    resp.headers['Referrer-Policy']='no-referrer'
    resp.headers['Cache-Control']='no-store'
    resp.headers['Content-Security-Policy']=("default-src 'self'; img-src 'self' data: blob:; "
      "script-src 'self'; style-src 'self'; connect-src 'self'; font-src 'self'; "
      "base-uri 'self'; frame-ancestors 'none'; form-action 'self'")
    return resp


def auth(request:Request):
    expected=os.environ.get('BARG_ACCESS_TOKEN','').strip()
    if not expected and os.environ.get('BARG_REQUIRE_TOKEN')=='1':
        raise HTTPException(status_code=503,detail='Workspace access token must be configured before exposing data APIs')
    if expected:
        import secrets
        token=request.headers.get('X-BARG-Token','')
        if not secrets.compare_digest(expected, token):
            raise HTTPException(status_code=401,detail='Valid workspace access token required')


def cleanup():
    now=time.time()
    for key, (expires,_) in list(STORAGE.items()):
        if expires<now: STORAGE.pop(key,None)
    while len(STORAGE)>30:
        STORAGE.pop(next(iter(STORAGE)))


def remember(data:DataBundle)->str:
    cleanup()
    key=uuid.uuid4().hex
    STORAGE[key]=(time.time()+TTL_SEC,data)
    return key


def lookup(key:str)->DataBundle:
    cleanup()
    item=STORAGE.get(key)
    if not item: raise HTTPException(status_code=404,detail='Dataset session expired or not found; reload the CSV')
    return item[1]

class Options(BaseModel):
    dataset_id:str=Field(min_length=1,max_length=80)
    k:int=Field(default=10,ge=2,le=20)
    kappa:float=Field(default=.7520386983881371,ge=0,le=10)
    rho:float=Field(default=.1,gt=0,le=.5)
    enforce_floor:bool=True
    drop_probability:float=Field(default=.10,ge=0,le=.75)
    seed:int=Field(default=23,ge=0,le=10_000_000)

class AgentOptions(Options):
    query:str=Field(default='Audit the system, compare baselines and recommend a safe next step',max_length=500)


def conf(model:Options)->dict[str,Any]:
    return model.model_dump(exclude={'dataset_id','query'})

@app.get('/')
def home():return FileResponse(STATIC/'index.html')

class ChatTurn(BaseModel):
    role: str=Field(pattern='^(user|assistant)$')
    content: str=Field(min_length=1,max_length=650)

class RagChatRequest(BaseModel):
    question: str=Field(min_length=3,max_length=900)
    history: list[ChatTurn]=Field(default_factory=list,max_length=6)
    dataset_id: str|None=Field(default=None,max_length=80)
    include_audit: bool=False
    k:int=Field(default=10,ge=2,le=20)
    kappa:float=Field(default=.7520386983881371,ge=0,le=10)
    rho:float=Field(default=.1,gt=0,le=.5)
    enforce_floor:bool=True
    drop_probability:float=Field(default=.10,ge=0,le=.75)
    seed:int=Field(default=23,ge=0,le=10_000_000)

@app.get('/api/rag/sources',dependencies=[Depends(auth)])
def rag_sources():
    return {'sources':list_sources(),'index':inspect_index(),
        'public_source_pdfs':os.environ.get('BARG_PUBLIC_SOURCE_PDFS')=='1'}

@app.get('/api/source-private/{doc_id}',dependencies=[Depends(auth)])
def source_pdf_private(doc_id:str):
    # Header-authenticated PDF viewing for collaborators; never exposed to anonymous requests.
    files={'main':ROOT/'knowledge_sources'/'main.pdf',
           'supp':ROOT/'knowledge_sources'/'supplement.pdf'}
    if doc_id not in files: raise HTTPException(404,'Unknown source identifier')
    if not files[doc_id].is_file(): raise HTTPException(404,'Source not bundled')
    return FileResponse(files[doc_id],media_type='application/pdf',
                        headers={'Cache-Control':'no-store','Content-Disposition':'inline'})

@app.get('/api/source/{doc_id}')
def source_pdf(doc_id:str):
    # Disabled by default: do not publish unpublished manuscripts accidentally.
    if os.environ.get('BARG_PUBLIC_SOURCE_PDFS')!='1':
        raise HTTPException(404,'Public source downloads disabled by default')
    files={'main':ROOT/'knowledge_sources'/'main.pdf',
           'supp':ROOT/'knowledge_sources'/'supplement.pdf'}
    if doc_id not in files:raise HTTPException(404,'Unknown source')
    return FileResponse(files[doc_id],media_type='application/pdf',
                        headers={'Content-Disposition':'inline'})

@app.post('/api/rag/chat',dependencies=[Depends(auth)])
def rag_chat(body:RagChatRequest):
    data=lookup(body.dataset_id) if body.dataset_id and body.include_audit else None
    opts=body.model_dump(include={'k','kappa','rho','enforce_floor','drop_probability','seed'})
    try:
        return run_research(body.question,[t.model_dump() for t in body.history],data,opts,body.include_audit)
    except (ValueError,AssertionError) as e:
        raise HTTPException(400,str(e)) from e

@app.get('/api/health')
def health():return {'status':'ok','engine':'deterministic','version':'4.0.0','auth_required':bool(os.environ.get('BARG_ACCESS_TOKEN','').strip() or os.environ.get('BARG_REQUIRE_TOKEN')=='1'),'rag_index':inspect_index(),'demo_available':SAMPLE.exists(),'local_llm_enabled':bool(os.environ.get('BARG_OLLAMA_MODEL'))}

@app.get('/api/ready')
def ready():
    # Render readiness: fail if packaged source index or public demo are missing.
    try:
        index=inspect_index()
        if not index['ready'] or index['documents']<2 or not SAMPLE.is_file():
            raise ValueError('Knowledge corpus or demo is incomplete')
    except Exception as exc:
        raise HTTPException(503,'Source index or sample missing') from exc
    return {'status':'ready','version':'4.0.0','knowledge_passages':index['chunks']}

@app.get('/api/runtime-check',dependencies=[Depends(auth)])
def runtime_check():
    """Deployment-safe diagnosis without private paths, tokens, user data or system environment."""
    import platform
    import sys
    return {'version':'4.0.0','python':sys.version.split()[0],
            'platform':platform.system(),'app_imported':True,
            'index_ready':bool(inspect_index().get('ready')),
            'local_access_note':'Use 01_START_WINDOWS.cmd and http://127.0.0.1:7860 on Windows'}

@app.get('/api/self-test',dependencies=[Depends(auth)])
def self_test():
    import numpy as np
    checks=[]
    def record(name, condition, description):
        checks.append({'name':name,'passed':bool(condition),'description':description})
    m=np.array([[True,True,False],[True,True,True]])
    r=np.array([[0.2,0.9,0.0],[0.0,0.6,1.0]])
    a=masked_gate(r,m,.752038698)
    record('Masked gate',np.allclose(a.sum(axis=1),1) and np.all(a[~m]==0),
           'Observed weights sum to one, absent weights exactly zero')
    record('Availability-only',np.allclose(masked_gate(r,m,0)[0,:2],[.5,.5]),
           'kappa=0 assigns uniform weights on observed views')
    record('Participation floor',abs(floor_bound(.1,3)-.752038698)<.00001,
           'Analytic 10% floor at three views')
    q=.1
    z=np.array([np.sqrt(q),np.sqrt(1-q),0.])
    new=np.array([0.,1.,0.])
    expected=np.sqrt(2*(1-np.sqrt(1-q)))
    record('Exact view-loss identity',abs(np.linalg.norm(z-new)-expected)<1e-12,
           'Unit separated blocks and fixed retained representation')
    try:
        ix=inspect_index()
        record('Source knowledge index',bool(ix['ready'] and ix['chunks']>=1),
               f"Read-only BM25 index with {ix['chunks']} passages")
    except Exception as ex:
        record('Source knowledge index',False,f'Index is unavailable: {type(ex).__name__}')
    record('Demo available',SAMPLE.is_file(),'Sample CSV is packaged')
    return {'version':'4.0.0','status':'PASS' if all(c['passed'] for c in checks) else 'FAIL',
      'checks':checks,'note':'Diagnostic unit invariants, not validation of semantic utility or deployment safety'}

@app.get('/api/demo',dependencies=[Depends(auth)])
def demo():
    try:
        data=from_csv(SAMPLE.read_bytes(),'Digits • three image-derived pseudo-views')
    except Exception as e:
        raise HTTPException(500, f'Demo sample invalid: {e}') from e
    return {'dataset_id':remember(data),'name':data.name,'rows':data.n,
            'views':data.view_names,'score_source':data.score_source,
            'scope':'Exploratory transductive sample; all three pseudo-views derive from the same digit image.'}

@app.get('/api/sample.csv',dependencies=[Depends(auth)])
def demo_csv():return FileResponse(SAMPLE,media_type='text/csv',filename=SAMPLE.name)

@app.post('/api/upload',dependencies=[Depends(auth)])
async def upload(file:UploadFile=File(...)):
    filename=file.filename or ''
    if not filename.lower().endswith('.csv') or '/' in filename or '\\' in filename or ':' in filename:
        raise HTTPException(400,'Only .csv files with safe filenames are allowed')
    contents=await file.read(MAX_FILE+1)
    await file.close()
    if len(contents)>MAX_FILE:raise HTTPException(413,'CSV file too large (max 3 MB)')
    try:data=from_csv(contents,filename)
    except ValueError as e:raise HTTPException(400,str(e)) from e
    return {'dataset_id':remember(data),'name':data.name,'rows':data.n,
            'views':data.view_names,'score_source':data.score_source,
            'scope':'Uploaded, exploratory; processed in memory and automatically expired after one hour.'}

@app.post('/api/analyze',dependencies=[Depends(auth)])
def analyze_endpoint(body:Options):
    data=lookup(body.dataset_id)
    try:return analyze(data,**conf(body))
    except (ValueError,AssertionError) as e:raise HTTPException(400,str(e)) from e

@app.post('/api/agent',dependencies=[Depends(auth)])
def agent_endpoint(body:AgentOptions):
    data=lookup(body.dataset_id)
    try:return run_agent(data,body.query,conf(body))
    except (ValueError,AssertionError) as e:raise HTTPException(400,str(e)) from e

@app.post('/api/report.pdf',dependencies=[Depends(auth)])
def report_pdf(body:Options):
    data=lookup(body.dataset_id)
    try:
        result=analyze(data,**conf(body))
        pdf=make_report(result)
    except (ValueError,AssertionError) as e:raise HTTPException(400,str(e)) from e
    return Response(pdf,media_type='application/pdf',headers={
        'Content-Disposition':'attachment; filename=BARG_CC_Evidence_Audit.pdf'})

@app.post('/api/evidence.zip',dependencies=[Depends(auth)])
def evidence_bundle(body:Options):
    # Archival, human-auditable output. Affected-row ledger is capped to 150 entries
    # by the existing engine; never imply this is a complete per-row export.
    data=lookup(body.dataset_id)
    try:
        result=analyze(data,**conf(body))
        pdf=make_report(result)
    except (ValueError,AssertionError) as e:
        raise HTTPException(400,str(e)) from e
    buf=io.BytesIO()
    ledger=result['audit']['dropped_rows_details']
    csvbuf=io.StringIO(newline='')
    fieldnames=['row','removed_mass','exact_drift','certified','unchanged_observed']
    writer=csv.DictWriter(csvbuf,fieldnames=fieldnames)
    writer.writeheader();writer.writerows(ledger)
    note=('BARG-CC Research Studio v4.0 - exploratory evidence export\n'
          'The CSV ledger contains up to the first 150 affected records only; see aggregate\n'
          'metrics in analysis.json for the full dataset. The source images are pseudo-views\n'
          'when using the Digits demonstration. This is not prospective validation.\n'
          'The one-refit certificate is sufficient, not necessary, and not global optimality.\n'
          f"Dataset fingerprint: {data.fingerprint}\n")
    with zipfile.ZipFile(buf,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        z.writestr('README_SCOPE.txt',note)
        z.writestr('analysis.json',json.dumps(result,indent=2,ensure_ascii=False))
        z.writestr('affected_rows_first_150.csv',csvbuf.getvalue())
        z.writestr('audit_report.pdf',pdf)
    return Response(buf.getvalue(),media_type='application/zip',headers={
        'Content-Disposition':'attachment; filename=BARG_CC_Audit_Evidence_Bundle.zip',
        'Cache-Control':'no-store'})

@app.delete('/api/datasets/{dataset_id}',dependencies=[Depends(auth)])
def delete_dataset(dataset_id:str):
    if dataset_id in STORAGE: del STORAGE[dataset_id]
    return {'deleted':True}
