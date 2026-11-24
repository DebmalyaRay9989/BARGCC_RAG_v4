from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app

ROOT=Path(__file__).resolve().parents[1]


def test_ui_static_handlers_and_critical_elements():
    html=(ROOT/'app/static/index.html').read_text()
    js=(ROOT/'app/static/app.js').read_text()
    assert 'V4.0 WINDOWS READY' in html
    for id_ in ('bootNotice','connectionPanel','connectionForm','connectionToken','connectionRetry','connectBtn','heroRun','runAudit','loadDemo','ragForm','agentForm'):
        assert f'id="{id_}"' in html
    assert "document.addEventListener('DOMContentLoaded',init)" in js
    assert 'function connectWorkspace' in js and 'function boot()' in js
    assert 'tokenGet()' in js and 'tokenSet(' in js


def test_browser_static_assets_served_by_backend():
    client=TestClient(app)
    assert client.get('/').status_code==200
    js=client.get('/static/app.js?v=4.0.0')
    assert js.status_code==200 and b'connectWorkspace' in js.content
    css=client.get('/static/styles.css?v=4.0.0')
    assert css.status_code==200 and b'connection-panel' in css.content


def test_auth_health_exposes_setup_state_without_secret(monkeypatch):
    monkeypatch.setenv('BARG_REQUIRE_TOKEN','1')
    monkeypatch.setenv('BARG_ACCESS_TOKEN','test-secret-should-not-appear')
    client=TestClient(app)
    health=client.get('/api/health')
    assert health.status_code==200
    assert health.json()['auth_required'] is True
    assert health.json()['version']=='4.0.0'
    assert 'test-secret-should-not-appear' not in health.text
    assert client.get('/api/demo').status_code==401
