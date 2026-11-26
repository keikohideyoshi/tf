#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null; then echo 'Python 3 szükséges';exit 1;fi
if [ ! -d .venv ]; then python3 -m venv .venv;fi
. .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
