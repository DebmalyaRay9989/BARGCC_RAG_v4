"""RAG source fidelity, access control, retrieval and safe audit integration."""
import sqlite3
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.rag import inspect_index, answer, list_sources, DB, search

client=TestClient(app)


def test_index_covers_both_pdfs():
    state=inspect_index()
    assert state['ready'] and state['documents']==2 and state['chunks']>=200
    src=list_sources()
    assert {s['doc_id'] for s in src}=={'main','supp'}
    assert next(s['pages'] for s in src if s['doc_id']=='main')==44
    assert next(s['pages'] for s in src if s['doc_id']=='supp')==25


def test_source_grounding_page_and_exact_excerpt():
    a=answer('At 10% simulated single-view loss, which dropped records passed the certificate?')
    assert a['status']=='RETRIEVED'
    assert a['generated_by_llm'] is False
    assert len(a['citations'])>0
    assert any('189' in c['excerpt'] or '77.1%' in c['excerpt'] for c in a['citations'])
    with sqlite3.connect(DB) as con:
        for c in a['citations']:
            row=con.execute('SELECT body FROM chunks WHERE doc_id=? AND page=? AND part=?',
                            (c['doc_id'],c['page'],c['part'])).fetchone()
            assert row and c['excerpt'].strip('…')[:45] in row[0]


def test_proposition_14_retrieval():
    out=answer('What does Proposition 14 certify with centroid refit?')
    assert out['status']=='RETRIEVED'
    assert any(c['doc_id']=='main' and c['page'] in {16,17} for c in out['citations'])


def test_nonsense_abstention():
    r=answer('qxvjt gnpszt asdrue agzqwl')
    assert r['status']=='INSUFFICIENT_EVIDENCE' and not r['citations']


def test_fts_injection_is_plain_text():
    # SQL/FTS operators must be treated as literal search terms; they cannot
    # change a read-only SELECT into an injected expression or SQL command.
    results=search('" OR * AND NEAR( foo )')
    assert isinstance(results,list)
    assert all(r['doc_id'] in {'main','supp'} and r['page']>=1 for r in results)


def test_chat_api_and_source_private():
    resp=client.post('/api/rag/chat',json={'question':'What are limitations of the one refit certificate?'})
    assert resp.status_code==200
    d=resp.json()
    assert d['mode']=='extractive_citation_rag' and d['citations'] and not d['generated_by_llm']
    assert len(d['trace'])>=1
    assert client.get('/api/source/main').status_code==404
    s=client.get('/api/rag/sources')
    assert s.status_code==200 and s.json()['index']['documents']==2


def test_rag_hybrid_tools_uses_existing_engine():
    demo=client.get('/api/demo').json()['dataset_id']
    body={'question':'Explain the view-loss certificate and audit this data',
          'dataset_id':demo,'include_audit':True,'k':5,'drop_probability':.1}
    r=client.post('/api/rag/chat',json=body)
    assert r.status_code==200, r.text[:250]
    a=r.json()
    assert a['audit_summary'] and a['audit_summary']['rows']>100
    assert 'CURRENT-DATA TOOL RESULT' in a['answer']
    assert a['audit_summary']['audit']['false_certificates']==0
    assert a['trace'][-1]['tool']=='scope_checker'


def test_missing_dataset_is_explicit_not_fake():
    r=client.post('/api/rag/chat',json={'question':'Explain Eq 22','include_audit':True})
    assert r.status_code==200 and r.json()['audit_summary'] is None
    assert r.json()['trace'][-1]['state']=='skipped'


def test_access_token_required_when_render_configured(monkeypatch):
    monkeypatch.setenv('BARG_REQUIRE_TOKEN','1')
    monkeypatch.delenv('BARG_ACCESS_TOKEN',raising=False)
    assert client.get('/api/rag/sources').status_code==503
    monkeypatch.setenv('BARG_ACCESS_TOKEN','test-token')
    assert client.get('/api/rag/sources').status_code==401
    assert client.get('/api/rag/sources',headers={'X-BARG-Token':'test-token'}).status_code==200


def test_validation_bounded():
    r=client.post('/api/rag/chat',json={'question':'a'*901})
    assert r.status_code==422
