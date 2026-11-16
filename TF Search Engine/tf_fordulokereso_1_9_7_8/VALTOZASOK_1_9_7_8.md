# TF Fordulókereső 1.9.7.8

- A nem harci (`V`/`VV`) varázslatkeresés most **közvetlen, indexelt SQLite JOIN lekérdezést** használ. Nem járja végig a fordulók teljes listáját, és nem vizsgál minden fordulónál fájlelérhetőséget.
- A korábbi fordulók varázslatindexének egyszeri feltöltése közvetlenül a tömörített parancsgyorsítótárból történik; hiányzó gyorsítótár esetén a meglévő HTML-t egyszer dolgozza fel. Az index később újrahasznosul.
- A részletes keresési diagnosztika most külön méri a varázslatindex feltöltését, a lekérdezést és a találatok összeállítását; számlálja az indexelt és megtalált eseményeket.
- A harci varázslatok keresése és a hatás-oszlop szerinti besorolás nem változott.
- Az adatbázis meglévő adatai megmaradnak; az index automatikusan létrejön.

**Fontos:** Az első keresés az index egyszeri felépítése miatt tovább tarthat. A második azonos keresés sebessége mutatja meg az új útvonal valódi teljesítményét. A teljes felhasználói adatbázison nem történt mérés.

**Teszt:** `python -m unittest discover -s tests -q` (50 sikeres teszt).
