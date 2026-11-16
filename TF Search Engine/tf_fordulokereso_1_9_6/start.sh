#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
if ! command -v python3 >/dev/null; then echo 'Hiányzik a python3. Telepítés: sudo pacman -S python'; exit 1; fi
if ! python3 -c 'import tkinter' >/dev/null 2>&1; then echo 'Hiányzik a tkinter. EndeavourOS: sudo pacman -S tk'; exit 1; fi
if [ ! -x .venv/bin/python ]; then python3 -m venv .venv; fi
if ! .venv/bin/python -c 'import bs4,lxml,openpyxl' >/dev/null 2>&1; then .venv/bin/python -m pip install -r requirements.txt; fi
if [ ! -f data/tudasbazis.sqlite3 ]; then .venv/bin/python app/cli.py init; fi
exec .venv/bin/python app/gui.py
