from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
ROOT=Path(__file__).resolve().parents[1]

def test_windows_launcher_is_self_contained():
    launcher=(ROOT/'00_INSTALL_WINDOWS.cmd').read_text()
    assert 'install_windows.ps1' in launcher
    assert 'SourceDir' in launcher
    runner=(ROOT/'run_windows.bat').read_text().lower()
    assert '01_start_windows.cmd' in runner
    assert 'py -3' not in runner
    assert 'venv' not in runner

def test_conda_installer_enforces_short_paths_and_safe_copy():
    script=(ROOT/'tools/install_windows.ps1').read_text()
    assert 'conda create' in script.lower()
    assert 'python=3.11' in script
    assert 'Copy-Checked' in script
    assert 'BARGCC_ENV' in script and 'BARGCC' in script
    assert 'Remove-Item' not in script

def test_v4_runtime_and_assets():
    client=TestClient(app)
    assert client.get('/').status_code==200
    assert 'V4.0 WINDOWS READY' in client.get('/').text
    assert client.get('/api/health').json()['version']=='4.0.0'
    assert client.get('/api/ready').json()['version']=='4.0.0'
    v=client.get('/api/runtime-check')
    assert v.status_code==200
    assert v.json()['index_ready'] is True
    assert 'E:' not in v.text and 'BARG_ACCESS_TOKEN' not in v.text

def test_sources_and_documentation_packaged():
    assert (ROOT/'app/knowledge/barg_sources.sqlite3').is_file()
    for x in ['knowledge_sources/main.pdf','knowledge_sources/supplement.pdf','docs/COMPLETE_SETUP_GUIDE.md']:
        assert (ROOT/x).is_file()
