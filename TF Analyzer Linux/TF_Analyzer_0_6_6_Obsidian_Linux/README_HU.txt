TF ANALYZER 0.6.6 – OBSIDIAN LINUX
==================================

A 0.6.5 teljes funkcionalitása változatlanul megmaradt.
ÚJ: megbízható, önálló virtuális Python-környezetet használó indító.

INDÍTÁS
  1. Csomagold ki a teljes ZIP-et.
  2. Nyiss terminált a program könyvtárában.
  3. Futtasd: ./start.sh
     (A régi ./inditas.sh is működik, az új start.sh-t hívja.)

ELSŐ INDÍTÁS
  - Python 3 szükséges. EndeavourOS/Arch: sudo pacman -S python python-pip
  - A start.sh automatikusan létrehozza a .venv könyvtárat.
  - A függőségeket kizárólag ebbe a virtuális környezetbe telepíti.
  - Az első telepítéshez internetkapcsolat szükséges.
  - A későbbi indításokkor nem telepít újra, ha minden rendben van.
  - Sérült, régi vagy más gépről másolt .venv esetén a régi mappát
    .venv.hibas.* néven megőrzi, és újat hoz létre.
  - A program böngészőben nyílik meg: http://127.0.0.1:8501
    (Ha nem nyílik meg automatikusan, nyisd meg kézzel.)

ADATBÁZIS / FRISSÍTÉS
  - A tf_analyzer.sqlite3 fájlt NE írd felül és NE töröld.
  - A kezdőoldali adatbázis-kiürítés funkció megmaradt.
  - A Bezárás gomb megmaradt.
  - A .venv és .venv.hibas.* könyvtárakat ne terjeszd tovább.
  - A program mappájának legyen írási jogosultsága az adatbázishoz.

HIBAELHÁRÍTÁS
  - python3: command not found -> sudo pacman -S python
  - venv/pip hiányzik -> sudo pacman -S python python-pip
  - Csomagtelepítési hiba -> internetkapcsolat ellenőrzése, újraindítás.
  - Port foglalt -> zárd be a korábbi TF Analyzer példányt.
  - NEM szükséges és NEM javasolt: sudo pip vagy --break-system-packages.

TÁMOGATOTT FÁJLOK: .html, .htm, .mhtml, .mht
MEGŐRZÖTT FUNKCIÓK: harci elemzés, TVP, feltételes gyógyítás,
moa spektroszkóp, sáfránypor, HTML-alapú Hibajelzések, Obsidian téma.
