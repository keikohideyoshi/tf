#!/usr/bin/env bash
# TF Analyzer 0.6.6 – Arch/EndeavourOS-kompatibilis, önjavító indító
set -Eeuo pipefail
cd -- "$(dirname -- "$(readlink -f -- "${BASH_SOURCE[0]}")")"

hiba() { printf '\nHIBA: %s\n' "$*" >&2; exit 1; }
info() { printf '[TF Analyzer] %s\n' "$*"; }

command -v python3 >/dev/null 2>&1 || hiba 'A Python 3 hiányzik. EndeavourOS/Arch: sudo pacman -S python'
python3 -c 'import sys; assert sys.version_info >= (3, 9)' 2>/dev/null || hiba 'Python 3.9 vagy újabb szükséges.'
[[ -f requirements.txt && -f app.py ]] || hiba 'Hiányzik az app.py vagy a requirements.txt. A teljes programcsomagot csomagold ki.'

# Megakadályozzuk, hogy egy külső Python-környezet befolyásolja az indítást.
unset PYTHONHOME PYTHONPATH VIRTUAL_ENV
export PIP_DISABLE_PIP_VERSION_CHECK=1
export PIP_NO_INPUT=1
VENV="$PWD/.venv"
PY="$VENV/bin/python"

venv_ok() {
  [[ -x "$PY" ]] || return 1
  "$PY" -c 'import sys, pathlib; assert sys.prefix != sys.base_prefix; assert pathlib.Path(sys.prefix).resolve() == pathlib.Path(__import__("sys").argv[1]).resolve()' "$VENV" >/dev/null 2>&1 || return 1
  "$PY" -m pip --version >/dev/null 2>&1 || return 1
}

uj_venv() {
  info 'Saját Python-környezet létrehozása (.venv)...'
  if ! python3 -m venv "$VENV"; then
    hiba 'A virtuális környezet nem hozható létre. Ellenőrizd a python és python-pip csomagokat: sudo pacman -S python python-pip'
  fi
  if ! "$PY" -m pip --version >/dev/null 2>&1; then
    info 'pip helyreállítása a virtuális környezetben...'
    "$PY" -m ensurepip --upgrade >/dev/null 2>&1 || hiba 'A pip nem érhető el a virtuális környezetben. Telepítsd: sudo pacman -S python python-pip'
  fi
  venv_ok || hiba 'A létrehozott virtuális környezet nem működik megfelelően.'
}

if ! venv_ok; then
  if [[ -e "$VENV" ]]; then
    # A régi, sérült környezetet nem töröljük, hanem biztonságba helyezzük.
    backup=".venv.hibas.$(date +%Y%m%d_%H%M%S).$$"
    info "Hibás vagy másik gépről másolt .venv észlelve. Átnevezés: $backup"
    mv -- "$VENV" "$backup" || hiba 'Nem sikerült átnevezni a régi .venv könyvtárat.'
  fi
  uj_venv
fi

# A függőségek állapotát a requirements.txt tartalma és importpróba alapján ellenőrizzük.
REQ_HASH="$(sha256sum requirements.txt | cut -d' ' -f1)"
STAMP="$VENV/.tf_analyzer_requirements.sha256"
check_imports() {
  "$PY" - <<'PYIMPORT' >/dev/null 2>&1
import streamlit, bs4, pandas, plotly
PYIMPORT
}

if [[ ! -f "$STAMP" ]] || [[ "$(cat "$STAMP")" != "$REQ_HASH" ]] || ! check_imports; then
  info 'Függőségek ellenőrzése és szükség szerinti telepítése a .venv környezetbe...'
  if ! "$PY" -m pip install --disable-pip-version-check -r requirements.txt; then
    hiba 'A függőségek telepítése nem sikerült. Ellenőrizd az internetkapcsolatot, majd indítsd újra a start.sh-t.'
  fi
  check_imports || hiba 'A csomagtelepítés után is hiányzik egy szükséges Python-modul.'
  printf '%s\n' "$REQ_HASH" > "$STAMP"
else
  info 'Minden szükséges függőség rendelkezésre áll.'
fi

info 'TF Analyzer indítása: http://127.0.0.1:8501'
exec "$PY" -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
