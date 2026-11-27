#!/usr/bin/env bash
set -e
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if ! python3 -c 'import tkinter' 2>/dev/null; then
  echo 'A Tkinter hiányzik. EndeavourOS/Arch: sudo pacman -S --needed tk'
  if command -v pacman >/dev/null && [[ -t 0 ]]; then read -rp 'Telepíted? [i/N] ' a; [[ "$a" == i ]] && sudo pacman -S --needed tk || exit 1; else exit 1; fi
fi
if python3 -c 'import openpyxl' 2>/dev/null; then exec python3 app.py; fi
python3 -m venv .venv
.venv/bin/python -m pip install openpyxl
exec .venv/bin/python app.py
