#!/usr/bin/env sh
set -eu
# Local reproduction of Render port binding; public deployment requires token.
: "${PORT:=10000}"
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT}" --workers 1
