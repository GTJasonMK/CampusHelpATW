#!/usr/bin/env sh
set -eu

PORT="${PORT:-3000}"
UVICORN_HOST="${UVICORN_HOST:-0.0.0.0}"
UVICORN_LOG_LEVEL="${UVICORN_LOG_LEVEL:-info}"
SQLITE_AUTO_INIT="${SQLITE_AUTO_INIT:-0}"
SQLITE_RESET_ON_START="${SQLITE_RESET_ON_START:-0}"

if [ -z "${PYTHONPATH:-}" ]; then
  export PYTHONPATH="/app"
fi

is_sqlite=0
case "${DATABASE_URL:-}" in
  sqlite+aiosqlite://*) is_sqlite=1 ;;
  *) is_sqlite=0 ;;
esac

if [ "${is_sqlite}" = "1" ] && [ "${SQLITE_AUTO_INIT}" = "1" ]; then
  if [ "${SQLITE_RESET_ON_START}" = "1" ]; then
    python scripts/init_sqlite_dev.py --reset
  else
    python scripts/init_sqlite_dev.py
  fi
fi

exec python -m uvicorn app.main:app \
  --host "${UVICORN_HOST}" \
  --port "${PORT}" \
  --log-level "${UVICORN_LOG_LEVEL}"
