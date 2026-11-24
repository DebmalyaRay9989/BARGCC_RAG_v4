# BARG-CC Agentic RAG v4.0 release verification

Date: 2026-11-24

Verified on a Linux build host:
- 40 Python tests: passed (`python -m pytest -q tests`).
- Local Python numerical and RAG preflight: passed (`python tools/preflight.py`).
- 23 Chromium interaction tests: passed using a browser and FastAPI test-client fetch bridge.
- Direct Uvicorn localhost HTTP smoke: passed for /, /static/app.js, /api/health, /api/ready, /api/runtime-check, /api/rag/sources and /api/demo.
- `node --check app/static/app.js`: passed.
- Master source archive ZIP checksum verification: see MANIFEST_SHA256.csv.

Not verified in this Linux environment:
- Actual PowerShell 5.1 or .cmd execution on Windows.
- Conda package installation and scikit-learn DLL loading on user's Windows computer.
- Docker image build and Render public deployment.
- Real-world scientific utility beyond the available manuscript and sample.

The v4 Windows PowerShell scripts have been statically reviewed. All claims about the installer are implementation descriptions, not observed Windows-run results.
