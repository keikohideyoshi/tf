#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null; then
  echo "Telepítsd a Pythont: sudo pacman -S python python-pip"
  exit 1
fi
if [ ! -d .venv ]; then python3 -m venv .venv; fi
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
