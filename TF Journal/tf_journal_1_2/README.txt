TF Journal 1.0 — A karakter útinaplója

Linux / EndeavourOS, Python 3, Tkinter, SQLite.
Kicsomagolás után: ./start.sh (ha szükséges: chmod +x start.sh).
Az indító ellenőrzi a Tkintert és az openpyxl-t; szükség esetén helyi virtuális környezetet készít. Első telepítéshez internet kellhet.

Importálj mappát (almappákkal együtt) vagy válassz fájlokat. HTML, HTM, MHTML, MHT, ZIP támogatott. A karakterválasztóval válts karaktert. A fordulótartomány szűri az összes nézetet. Az oszlopfejlécekre kattintva rendezhetsz. CSV: aktív táblázat; XLSX: minden táblázat külön munkalapon. Az idővonal CSV exportja az időszakokat tartalmazza.

zones.json: soronként [név, min X, max X, min Y, max Y], határok befoglalók. A grafikus szerkesztő ellenőrzi az átfedést. A módosítás azonnal újrabesorolja a meglévő adatokat. A journal.sqlite3 a helyi adatbázis; mentéshez a program bezárása után másold ezt és a zones.json fájlt. Az import.log a legutóbbi import jelzéseit tartalmazza. Eltérő duplikátumnál az első adat marad meg.

A hiányzó fordulók csak a megfigyelt fordulók közötti hézagokat jelentik. Az időszakok hézagnál megszakadnak. A zónaváltások megfigyelt végpontok, nem tényleges útvonalak. Az ismeretlen terület külön kategória. Az alkalmazás nem tartalmaz valódi térképet.

Teszt: a három eredeti ZIP koordinátái, dátumai, azonosítói és besorolása ellenőrizve; grafikus felület nem tesztelt valódi Linux asztali munkamenetben.

1.2: A régi fordulók felismerése és a Térkép fül. Az 1.0 adatbázisa és saját zones.json fájlja átmásolható bezárt alkalmazás mellett, biztonsági mentés után. Az eredeti fordulókat újra kell importálni a tartalék adatokhoz. A térképen görgővel nagyíthatsz, húzással mozgathatsz, kattintással részleteket láthatsz. A feltételezett pontok alapból ki vannak kapcsolva. PNG exporthoz Pillow és Ghostscript szükséges. A hőtérkép színezett köröket használ.

1.2: Betáplálási idő (HH:MM), karakterlap szintje, szintdiagram és évjelölések a térkép lejátszójában. A szintlépés zöld jelölése csak szomszédos ismert fordulók esetén jelenik meg. A hiányzó értékeket nem becsüljük. A régi adatbázis automatikusan bővül; az eredeti fordulók ismételt importálása tölti fel az új mezőket. Átmásolás előtt készíts biztonsági mentést.
