#!/usr/bin/env bash
set -Eeuo pipefail
DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"
if ! command -v python3 >/dev/null 2>&1; then
  echo 'HIBA: A python3 nem található. Telepítés: sudo pacman -S python' >&2
  exit 1
fi
if ! python3 -c 'import bs4; import tkinter' >/dev/null 2>&1; then
  echo 'HIBA: Hiányzó Python-csomag. Telepítés: sudo pacman -S python-beautifulsoup4 tk' >&2
  exit 1
fi
exec python3 "$DIR/tf_character_analyzer.py" "$@"
