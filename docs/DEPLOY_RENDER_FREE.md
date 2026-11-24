# Render Free deployment — operator instructions

## Before uploading

- Keep this Git repository **private** if the manuscript is unpublished; the app package contains the original 44-page PDF and 25-page supplement.
- Copy all project files to **the repository root**, not a nested `BARG_CC_Agentic_Lab` directory if `render.yaml` is at root.
- The deployment uses one Docker web service (`plan: free`), no disks, no workers, no paid database, and one uvicorn process.
- Confirm monthly free-tier usage and any Render billing prompts before you approve deployment. This template never provisions paid resources on its own.

## Blueprint wizard

1. Render dashboard → **New** → **Blueprint**.
2. Connect your private GitHub repository and target branch.
3. Render detects `render.yaml`; inspect the service plan `free` and runtime `docker`.
4. Enter a strong, secret `BARG_ACCESS_TOKEN` when prompted. It must not be placed in public source code. A token can be generated locally with `python -c "import secrets;print(secrets.token_urlsafe(32))"`.
5. Start Blueprint deployment. Watch the build logs for package installation; the app should bind to `0.0.0.0:${PORT}` (Render's default port is 10000).
6. Check `/api/ready`. A healthy response includes `rag_index.ready = true` and `rag_index.documents = 2`.
7. Open the web dashboard and enter the token when the browser requests it. Load the demo, then switch to **RAG Copilot**.

## File layout and runtime behavior

- `Dockerfile`: `python:3.11-slim`, `pip install -r requirements.txt`, a non-root user, a single uvicorn worker.
- `app/knowledge/barg_sources.sqlite3`: bundled read-only FTS5 corpus. It is not populated by a background task.
- `knowledge_sources/main.pdf` and `supplement.pdf`: original source PDFs retained for index provenance; **public download off**.
- `app/core.py`: existing audit engine. Dataset sessions are stored in memory for up to 1 hour and lost on restart.
- `app/rag.py`: document retrieval and literal page-cited passages. No online model.
- `app/rag_agent.py`: checks retrieved sources and invokes existing deterministic audit only when requested and a dataset is present.

## Web service variables

| Variable | Value / behavior |
|---|---|
| `BARG_ACCESS_TOKEN` | **Secret, required on Render**; requested on Blueprint creation |
| `BARG_REQUIRE_TOKEN` | `1` in `render.yaml`; missing token blocks protected APIs with 503 |
| `BARG_PUBLIC_SOURCE_PDFS` | `0` by default; do not enable unless source dissemination is authorized |
| `OPENBLAS_NUM_THREADS` | `1`; avoids CPU thread oversubscription on low-power free instance |
| `OMP_NUM_THREADS`, `MKL_NUM_THREADS` | `1` |
| `PORT` | Render sets automatically; Docker CMD uses `${PORT:-10000}` |

## What remains free / limits

Official Render documentation (checked 24 Nov 2026) says Free web services offer ~512 MB RAM, 0.1 CPU, 750 free instance-hours per workspace each calendar month, and spin down after 15 minutes of idle traffic. A cold start may take roughly a minute. Render may restart instances, and Free web services do not support persistent disks. A separate free Postgres offering is **not used** (and has an expiration policy). Keep experiments small; do not try to install Ollama in this image.

If your Free instance hours are exhausted, Render suspends Free web services until the next month. It does not mean research metrics have been lost from the manuscript, but **uploaded dataset sessions are lost on spin-down/restart**.

Official sources:
- https://render.com/docs/free
- https://render.com/docs/blueprint-spec
- https://render.com/docs/web-services
- https://render.com/docs/compute-plans
- https://render.com/pricing

## Troubleshooting

| Problem | Action |
|---|---|
| Render reports no open port | Check Docker CMD uses `--host 0.0.0.0` and `--port ${PORT:-10000}` |
| Browser asks for token | Enter the `BARG_ACCESS_TOKEN` secret configured in Render; the browser stores it in **sessionStorage** only |
| HTTP 503 on protected endpoints | `BARG_REQUIRE_TOKEN=1`, but `BARG_ACCESS_TOKEN` is missing; set it in Render environment and redeploy |
| RAG index missing | Verify `app/knowledge/barg_sources.sqlite3` is present in Git and Docker copy includes it |
| Page citation downloads say 404 | Expected: source PDF downloads are disabled by default; citation cards still name source page |
| Older CSV session stops working | Expected after a free-service restart or session expiry; upload dataset again |
| Health succeeds but audit is slow | Reduce CSV rows, K-means K, and concurrent users. Render Free has restricted CPU/RAM |
| Blueprints ask for paid features | Stop and review settings; `render.yaml` itself declares a single Free web service only |

## Production warning

Render Free is suited for demos and educational research. It is not suitable for confidential multi-user work or SLA-backed deployment. Add real user authentication, rate limiting, isolation, audited authorization, persistent storage, backups, monitoring, and validation before any production usage.


### Version 2.1.1 interface fix

If the deployed UI has inactive buttons, verify that the sidebar displays `V3.0 ENHANCED` and includes `RAG Copilot`. The earlier V1 screenshot is an older app. For the new token connection panel, load the Render web URL and use **Connect** with the exact secret configured as `BARG_ACCESS_TOKEN`. For complete instructions see `FIX_INACTIVE_BUTTONS.md`.

## v3.0 buttons and evidence privacy

- **Deployment → Run system check** returns six diagnostic invariants via a token-authenticated request.
- **Audit → Evidence ZIP** produces `analysis.json`, `audit_report.pdf`, a scope README, and a capped (150 row) affected ledger.
- **RAG → Open protected PDF** uses a private token-authenticated route and a temporary browser Blob URL, not an anonymous public download.
- The unlabeled cluster assignment agreement value now matches cluster IDs optimally; raw ID match is retained for diagnostic comparison.
- Set `BARG_REQUIRE_TOKEN=1`, configure `BARG_ACCESS_TOKEN` as a Render secret, and keep the manuscript repository private.
