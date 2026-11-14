#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if [[ "${1:-}" == "--html-only" || "${1:-}" == "--cli" || "${1:-}" == "--karakter" || "${1:-}" == "--cel" ]]; then
  if [[ "${1:-}" == "--cli" ]]; then shift; fi
  if [[ "${1:-}" == "--html-only" ]]; then python tf_zip_letolto.py "$@"; exit $?; fi
fi
if [[ ! -d .venv ]]; then python -m venv .venv; fi
. .venv/bin/activate
python -c 'import playwright' 2>/dev/null || python -m pip install playwright
python -m playwright install chromium
if [[ "${1:-}" == "--cli" ]]; then shift; python tf_zip_letolto.py "$@"; else python gui.py; fi
