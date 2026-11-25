#!/usr/bin/env bash
set -e
cd -- "$(dirname -- "$(realpath -- "$0")")"
if ! python -c 'import PySide6' 2>/dev/null; then
  echo 'A PySide6 telepítése szükséges.'
  sudo pacman -S --needed pyside6
fi
exec python main.py
