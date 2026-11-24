# Windows troubleshooting quick reference

See `Complete_Windows_Installation_and_Study_Guide.pdf` for detailed explanations and verified research boundaries.

1. No Python 3.11 found with `py`: **do not use the py launcher**; `00_INSTALL_WINDOWS.cmd` uses the existing Miniconda to create a new Python 3.11 environment.
2. `WinError 206` from scikit-learn: create the environment in a short path such as `E:\BARGCC_ENV`; do not reuse the older deeply nested `.venv`.
3. `-File` script does not exist: the new `tools/install_windows.ps1` is bundled and invoked from the `00_INSTALL_WINDOWS.cmd` in the same extracted folder.
4. Buttons do nothing: run `01_START_WINDOWS.cmd`, browse to `http://127.0.0.1:7860`, not `index.html` or a stale v1 URL.
5. Port busy: stop the old server before running again or use `--port 7861` with the isolated interpreter.
6. Missing app index: the ZIP must be fully extracted, including `app/knowledge/barg_sources.sqlite3` and `knowledge_sources/*.pdf`.
7. On any failure, run `04_DIAGNOSE_WINDOWS.cmd` in the installed folder; share its logs only after reviewing for personal paths.
