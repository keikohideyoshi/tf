#!/usr/bin/env bash
set -Eeuo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

say() { printf '\n[TF Fordulóletöltő] %s\n' "$*"; }
fail() { printf '\nHIBA: %s\n' "$*" >&2; exit 1; }

command -v python >/dev/null 2>&1 || fail "A Python hiányzik. Telepítés: sudo pacman -S python"

# A HTML-only módnak sem Playwright, sem grafikus környezet nem szükséges.
if [[ "${1:-}" == "--html-only" ]]; then
  say "HTML-ek kigyűjtése (böngésző és pip nélkül)."
  exec python tf_zip_letolto.py "$@"
fi

# A --cli a korábbi parancssoros letöltőt indítja.
mode=gui
if [[ "${1:-}" == "--cli" ]]; then mode=cli; shift; fi

if [[ "$mode" == gui ]]; then
  python -c 'import tkinter; import _tkinter' >/dev/null 2>&1 || fail "A Tkinter hiányzik. EndeavourOS alatt: sudo pacman -S tk"
  [[ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]] || fail "Nincs grafikus munkamenet (DISPLAY/WAYLAND_DISPLAY)."
fi

# Sérült / régi virtuális környezet újraépítése csak szükség esetén.
if [[ -e .venv && ! -x .venv/bin/python ]]; then
  fail "A .venv mappa létezik, de nem használható. Nevezd át vagy töröld, majd indítsd újra."
fi
if [[ ! -x .venv/bin/python ]]; then
  say "Első indítás: saját Python-környezet létrehozása…"
  python -m venv .venv || fail "A virtuális környezet nem hozható létre. Ellenőrizd a Python venv/ensurepip támogatását."
fi
PY=.venv/bin/python
if ! "$PY" -m pip --version >/dev/null 2>&1; then
  say "pip előkészítése a virtuális környezetben…"
  "$PY" -m ensurepip --upgrade >/dev/null 2>&1 || fail "A venv pip modulja nem állítható helyre. Töröld a .venv mappát, és indítsd újra."
fi
if ! "$PY" -c 'import playwright.sync_api' >/dev/null 2>&1; then
  say "Playwright telepítése kizárólag a .venv környezetbe…"
  "$PY" -m pip install playwright || fail "A Playwright telepítése sikertelen. Ellenőrizd az internetkapcsolatot."
fi
# A Playwright a saját kompatibilis Chromiumját használja, nem a rendszer Chromiumját.
if ! "$PY" -c 'from pathlib import Path; from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    assert Path(p.chromium.executable_path).is_file()' >/dev/null 2>&1; then
  say "A Playwright Chromium böngészőjének telepítése…"
  "$PY" -m playwright install chromium || fail "A Chromium telepítése sikertelen. Ellenőrizd a hálózatot és a szabad lemezterületet."
fi

if [[ "$mode" == cli ]]; then
  exec "$PY" tf_zip_letolto.py "$@"
else
  exec "$PY" gui.py "$@"
fi
