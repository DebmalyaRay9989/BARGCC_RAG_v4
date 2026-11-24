# BARG-CC Agentic RAG Research Studio v4.0

**Rebuilt from the existing manuscript-based v3 application with a Windows safe-path installer.**

## Windows: three steps

1. Extract this ZIP **directly into `E:\BARGCC_SETUP`** (or `C:\BARGCC_SETUP`); use File Explorer > Extract All. Do not run files from inside the ZIP.
2. Double-click `00_INSTALL_WINDOWS.cmd`. It uses your Miniconda installation to create Python 3.11 under `E:\BARGCC_ENV`, copies the app to `E:\BARGCC`, installs dependencies, runs preflight and tests, and starts the local server. No `py -3.11` command is necessary.
3. Open **http://127.0.0.1:7860/**. On later days use `E:\BARGCC\01_START_WINDOWS.cmd`.

The installer uses `C:` if `E:` does not exist. If `E:\BARGCC` already exists, it is backed up to a timestamped folder before updating. No system administrator, registry change, or old research environment deletion is required. Internet access is required to create a Conda environment and download PyPI dependencies if they are not cached.

**Critical:** This is a local Windows repair and release. Windows execution itself cannot be tested in the Linux packaging environment. Run `02_VERIFY_WINDOWS.cmd` and `03_RUN_TESTS_WINDOWS.cmd` on Windows to verify after installation.

## What the application does

- BARG-CC masked reliability gate (including baseline κ=0) and participation floor
- K-means comparisons and view-loss/one-refit stability certificates
- Research Copilot with page-cited extraction from the manuscript and supplement (304 indexed passages)
- Deterministic agent with audit trace, dataset import, and evidence PDF/ZIP exports
- Private source PDF viewing through token-protected endpoints; public PDF access disabled
- No paid LLM API requirement; optional Ollama is external and disabled by default

These are conditional research checks, not validation of field robustness, semantic quality or production safety.

## Complete documentation

Read `docs/COMPLETE_SETUP_GUIDE.md` for the full numbered walkthrough, troubleshooting, commands, security notes, and Render Free deployment. For visual explanation, open the separately provided **BARGCC_RAG_v4_Complete_Installation_and_Study_Guide.pdf**.

## Alternative environments

- Linux/macOS: `bash run_linux_mac.sh` (Python 3.11 installed first)
- Docker: `docker build -t bargcc-rag-v4 .`, then `docker run --rm -p 7860:10000 bargcc-rag-v4`
- Render: put project files at GitHub repository root, create Blueprint from `render.yaml`, and enter a secret BARG_ACCESS_TOKEN.

Public deployment is not a confidential multi-user solution. Never publish the manuscript PDFs without permission.
