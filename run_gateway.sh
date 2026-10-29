#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
: "${GATEWAY_TOKEN:?Set a gateway bearer secret in your environment}"
: "${GATEWAY_ADMIN_TOKEN:?Set a different admin bearer secret in your environment}"
if [[ "$GATEWAY_TOKEN" == "$GATEWAY_ADMIN_TOKEN" ]]; then echo 'Use different client and admin secrets' >&2; exit 1; fi
export LD_LIBRARY_PATH="$(python runtime_env.py)"
python model_assets.py
python doctor.py
python -m pytest -q tests
if [[ "${RUN_BENCHMARK:-1}" == 1 ]]; then python benchmark_700toks.py; fi
# Uvicorn lifespan creates and warms real inference sessions before readiness.
exec python -m uvicorn gateway_server:app --host "${BIND_HOST:-127.0.0.1}" --port "${PORT:-8000}" --workers 1 --no-access-log
