"""Offline no-network BARG-CC startup verification; keeps scientific claims scoped."""
from __future__ import annotations
import json,sys,hashlib,platform
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
checks=[]
def test(name,fn):
 try:
  result=fn()
  checks.append({'check':name,'pass':True,'detail':str(result)[:180]})
 except Exception as exc:
  checks.append({'check':name,'pass':False,'detail':f'{type(exc).__name__}: {exc}'[:180]})

def dependencies():
 import numpy,scipy,sklearn,pandas,fastapi,uvicorn
 from sklearn.cluster import KMeans
 return 'numpy '+numpy.__version__+'; sklearn '+sklearn.__version__+'; scipy '+scipy.__version__

def import_app():
 from app.main import app
 return app.title

def rag_index():
 from app.rag import inspect_index
 result=inspect_index()
 assert result.get('ready'),result
 assert result.get('documents',0)>=2,result
 return str(result)

def sample_and_gate():
 import numpy as np
 from app.core import masked_gate
 a=masked_gate(np.array([[.2,.8,.5]]),np.array([[1,1,0]],dtype=bool),.752038698)
 assert a.shape==(1,3) and a[0,2]==0 and abs(a.sum()-1)<1e-10
 return 'exact missing-mask exclusion and normalized shares verified'

def source_files():
 x=[ROOT/'knowledge_sources'/'main.pdf',ROOT/'knowledge_sources'/'supplement.pdf',ROOT/'samples'/'digits_three_derived_pseudoviews.csv']
 assert all(f.is_file() for f in x),'Missing manuscript, supplement or demo CSV'
 return ', '.join(f.name for f in x)

test('Scientific Python libraries',dependencies)
test('Application import',import_app)
test('SQLite RAG index',rag_index)
test('Numerical masking invariant',sample_and_gate)
test('Bundled evidence files',source_files)
report={'application':'BARG-CC Agentic RAG v4','platform':platform.platform(),'python':sys.version.split()[0], 'checks':checks,'status':'PASS' if all(c['pass'] for c in checks) else 'FAIL'}
print(json.dumps(report,indent=2,ensure_ascii=True))
try:
 logs=ROOT/'logs';logs.mkdir(exist_ok=True); (logs/'preflight.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
except OSError:pass
sys.exit(0 if report['status']=='PASS' else 1)
