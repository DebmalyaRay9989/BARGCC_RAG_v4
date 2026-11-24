# BARG-CC Agentic RAG v4 — Windows installation from zero

See the separate detailed PDF and DOCX document for illustrations and explanations.

## A. Diagnose the original failure

- `py -3.11 --version` returned “No suitable Python runtime found”. This only shows the Windows Python launcher did not find Python 3.11. It **does not** mean Miniconda is absent.
- Import of `sklearn` failed with `[WinError 206] The filename or extension is too long` because `.venv` was created in a very deep project path.
- The old `.ps1` call failed because that script was not actually located inside the current directory.

## B. New installation (recommended)

1. Download the complete v4 release ZIP; do not extract into the older deeply nested folder.
2. In File Explorer, create `E:\BARGCC_SETUP` (or `C:\BARGCC_SETUP`) and extract the ZIP to that folder.
3. Open the extracted **BARGCC_RAG_v4** project folder: `00_INSTALL_WINDOWS.cmd`, `requirements.txt`, `app` and `tools` must be visible together.
4. Double-click **00_INSTALL_WINDOWS.cmd**. Do not run an older `run_windows.bat` from the old folder.
5. The installer checks Conda, copies the application to `E:\BARGCC`, creates Python 3.11 under `E:\BARGCC_ENV`, installs binary wheels and test tools, runs preflight and tests, then starts Uvicorn.
6. Leave the server window running and open `http://127.0.0.1:7860/`.
7. Click “Load demo”, “Run audit”, “RAG Copilot”, and “Deployment > Run system check”.
8. Restart anytime with `E:\BARGCC\01_START_WINDOWS.cmd`.

If drive E: is unavailable, the installer uses C:. If the target exists, the installer backs it up to a timestamped sibling before copying; it does not delete the original nested research folder.

## C. Manual Conda installation, PowerShell

```powershell
& 'E:\Miniconda3\Scripts\conda.exe' create --yes --prefix E:\BARGCC_ENV python=3.11 pip
Set-Location E:\BARGCC
& 'E:\BARGCC_ENV\python.exe' -m pip install --only-binary=:all: -r requirements.txt
& 'E:\BARGCC_ENV\python.exe' -m pip install --only-binary=:all: -r requirements-dev.txt
& 'E:\BARGCC_ENV\python.exe' tools\preflight.py
& 'E:\BARGCC_ENV\python.exe' -m pytest -q tests
& 'E:\BARGCC_ENV\python.exe' -m uvicorn app.main:app --host 127.0.0.1 --port 7860
```

Do not run the manual commands inside your old deeply nested directory. Set `C:` instead of `E:` if necessary.

## D. Common error reference

| Symptom | Cause | Action |
|---|---|---|
| `py -3.11` not found | CPython launcher registry lacks 3.11 | Use the isolated Conda 3.11 environment; no `py` required |
| `WinError 206` in sklearn DLL load | Environment DLL path too long | Install `E:\BARGCC_ENV` and run copied application `E:\BARGCC` |
| `-File` script does not exist | PowerShell working folder is not the download folder | Use bundled `00_INSTALL_WINDOWS.cmd` from extracted new ZIP |
| `ModuleNotFoundError` | Wrong interpreter or incomplete pip install | Run installer again; then `02_VERIFY_WINDOWS.cmd` |
| `Conda could not be found` | Conda installed outside detection paths | Invoke installer with `-CondaExe 'path\to\conda.exe'` |
| HTTP 401 | Server needs shared token | Enter token using Connect, or use local start script which disables token for localhost |
| HTTP 503 | Token required but not configured on host | Set BARG_ACCESS_TOKEN on Render; redeploy |
| Browser buttons inert | Old app, direct HTML opening or inaccessible API | Open `http://127.0.0.1:7860/`, not the HTML file; force reload Ctrl+Shift+R |
| Port already in use | Another process uses 7860 | Stop old instance, or start Uvicorn with `--port 7861` |
| SQLite index missing | ZIP not fully extracted | Extract all files, check `app/knowledge/barg_sources.sqlite3` |
| Test fails | Dependency mismatch or missing dev tools | Run `03_RUN_TESTS_WINDOWS.cmd` and inspect exact failure |

## E. Research workflow

1. Load the public Digits **pseudo-view** sample. Derived views are not independent sensors.
2. Compare κ=0 availability-only baseline and κ>0 gate under matched seed.
3. Inspect dataset rows, 3 view masks and weights; check the participation floor.
4. Apply one-view dropout at selected probability and separate certification for all, affected, unaffected.
5. Ask the RAG copilot for a proposition; check citations to manuscript pages.
6. Export evidence ZIP with JSON analysis, PDF report and capped row ledger.
7. Record assumptions before interpreting evidence. Neither clustering accuracy nor certificates imply field safety.

## F. Render Free

Keep the GitHub repository **private** if PDFs are unpublished. Upload project contents **at repository root**. Render Dashboard > New > Blueprint > connect repository > verify `runtime: docker`, `plan: free`; set secret BARG_ACCESS_TOKEN; deploy; visit `/api/ready`; use dashboard Connect. Hosted datasets are in memory only; service may sleep/restart and data can disappear. No live deployment is included in this release.

## G. Privacy

Use localhost for sensitive work. The shared token is not per-user authentication. Uploads are temporary memory sessions; do not use for protected medical or personal records in a public free demo.
