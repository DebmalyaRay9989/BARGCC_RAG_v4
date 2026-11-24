"""V3 research correctness, security and evidence-release contract."""
from __future__ import annotations
import io
import json
import zipfile
import numpy as np
from fastapi.testclient import TestClient
from app.main import app
from app.core import aligned_assignment_agreement

client=TestClient(app)


def test_agreement_invariant_to_cluster_numbers():
    a=np.array([0,0,0,1,1,2,2,2])
    b=np.array([2,2,2,0,0,1,1,1])
    assert aligned_assignment_agreement(a,b)==100.
    assert float((a==b).mean())==0.
    imperfect=np.array([2,2,0,0,0,1,1,1])
    assert 0 < aligned_assignment_agreement(a,imperfect) < 100


def test_ready_route_is_dependency_aware():
    v=client.get('/api/ready')
    assert v.status_code==200 and v.json()['status']=='ready'


def test_diagnostic_invariants_and_scope():
    v=client.get('/api/self-test')
    assert v.status_code==200,v.text
    d=v.json()
    assert d['status']=='PASS',d
    assert len(d['checks'])>=6
    assert 'not validation' in d['note']


def test_source_pdf_protection(monkeypatch):
    monkeypatch.setenv('BARG_ACCESS_TOKEN','do-not-log-test-secret')
    monkeypatch.setenv('BARG_REQUIRE_TOKEN','1')
    for doc in ('main','supp'):
        assert client.get('/api/source-private/'+doc).status_code==401
        r=client.get('/api/source-private/'+doc,headers={'X-BARG-Token':'do-not-log-test-secret'})
        assert r.status_code==200 and r.content.startswith(b'%PDF')
        assert r.headers['cache-control']=='no-store'
    assert client.get('/api/source-private/unknown',headers={'X-BARG-Token':'do-not-log-test-secret'}).status_code==404
    assert client.get('/api/source/main').status_code==404
    assert 'do-not-log-test-secret' not in client.get('/api/health').text


def test_bundle_export_scoped_and_complete():
    d=client.get('/api/demo').json()
    r=client.post('/api/evidence.zip',json={'dataset_id':d['dataset_id'],'k':5,'seed':11,'drop_probability':.2})
    assert r.status_code==200,r.text[:500]
    z=zipfile.ZipFile(io.BytesIO(r.content))
    assert z.testzip() is None
    assert set(z.namelist())=={'README_SCOPE.txt','analysis.json','affected_rows_first_150.csv','audit_report.pdf'}
    result=json.loads(z.read('analysis.json'))
    assert result['summary']['assignment_agreement_pct']>=result['summary']['raw_cluster_id_agreement_pct']
    assert result['audit']['false_certificates']==0
    assert b'first 150' in z.read('README_SCOPE.txt')
    assert z.read('audit_report.pdf').startswith(b'%PDF')
    assert len(z.read('affected_rows_first_150.csv').splitlines())<=151


def test_bundle_rejects_unknown_dataset():
    r=client.post('/api/evidence.zip',json={'dataset_id':'wrong'})
    assert r.status_code==404
