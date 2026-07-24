#!/bin/sh
set -e

# Render sets $PORT at runtime (varies, commonly 10000 -- always read the
# env var rather than hardcoding it).
PORT="${PORT:-10000}"

echo "[start.sh] verifying app import..."
python -c "import app.main"

echo "[start.sh] starting uvicorn on port $PORT..."
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
