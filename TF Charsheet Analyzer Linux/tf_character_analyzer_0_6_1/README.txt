TF Character Analyzer 0.6.1 — offline CSV és XLSX export
==================================================

Indítás: ./start.sh
Függőségek: sudo pacman -S python python-beautifulsoup4 tk

A böngészőben megnyíló fejlődéstörténeti jelentés minden blokkjában
az „Exportálás” gomb CSV vagy XLSX fájlt tölt le. A „Teljes adatexport”
gomb az összes adatkészletet több munkalapos XLSX-be, illetve egy
ZIP-ben összecsomagolt CSV-készletbe exportálja.

Az export mindig az aktuálisan kijelölt fordulóintervallumra vonatkozik.
A szakértelem-grafikon exportja csak a grafikonhoz kijelölt szakértelmeket
tartalmazza; a szakértelem-változás táblázat exportja az összes szakértelmet,
a táblázat keresőjével szűrve. A változásnapló keresőjét is figyelembe veszi.
A fordulónkénti részletes adatok a grafikonokon túli elemzéshez is alkalmasak.
A CSV UTF-8 BOM-mal, pontosvesszővel elválasztva készül; az XLSX
formátum helyben, internet és további Python-csomagok nélkül készül.

Az adatbázis: tf_karakterlapok/tf_karakterek.sqlite3
A korábbi 0.5.1-es adatbázis változatlanul használható. Ne írd felül
az archivált adatbázisodat a csomag teszt/ könyvtárának mintájával.

A korábbi HTML/MHTML-import, szűrés, szintlépés-elemzés, sötét navigáció,
./start.sh indítás és automatikus böngészőmegnyitás megmaradt.

0.6.1: Átméretezhető sötét fordulóválasztó; Shift+nyíl és Ctrl+A kijelölés; szakértelem-töredékek figyelésének elhagyása a jelentésből és exportokból.
