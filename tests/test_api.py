from fastapi.testclient import TestClient
from app.main import app
import os
client=TestClient(app)

def test_api_health_and_ui():
    r=client.get('/api/health')
    assert r.status_code==200 and r.json()['status']=='ok'
    page=client.get('/')
    assert page.status_code==200 and 'Agentic Research Lab' in page.text
    assert page.headers['X-Content-Type-Options']=='nosniff'

def test_demo_analysis_agent():
    demo=client.get('/api/demo')
    assert demo.status_code==200
    did=demo.json()['dataset_id']
    config={'dataset_id':did,'k':10,'drop_probability':.1}
    result=client.post('/api/analyze',json=config)
    assert result.status_code==200, result.text
    assert result.json()['audit']['false_certificates']==0
    pdf=client.post('/api/report.pdf',json=config)
    assert pdf.status_code==200 and pdf.content.startswith(b'%PDF-') and len(pdf.content)>3000
    ag=client.post('/api/agent',json={**config,'query':'Audit missingness and compare baselines'})
    assert ag.status_code==200
    assert len(ag.json()['trace'])==4
    assert client.delete('/api/datasets/'+did).status_code==200
    assert client.post('/api/analyze',json=config).status_code==404

def test_invalid_upload_and_auth(monkeypatch):
    bad=client.post('/api/upload',files={'file':('notpdf.pdf',b'x','application/pdf')})
    assert bad.status_code==400
    monkeypatch.setenv('BARG_ACCESS_TOKEN','test-secret')
    assert client.get('/api/demo').status_code==401
    assert client.get('/api/demo',headers={'X-BARG-Token':'test-secret'}).status_code==200
    monkeypatch.delenv('BARG_ACCESS_TOKEN')
