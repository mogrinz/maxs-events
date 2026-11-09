#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -f .events.env ]]; then
  echo "Run bash setup.sh first."
  exit 1
fi
set -a
source .events.env
set +a
exec .venv/bin/python app.py
