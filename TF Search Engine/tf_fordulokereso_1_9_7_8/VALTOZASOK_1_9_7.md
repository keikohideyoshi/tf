# TF Fordulókereső 1.9.7

- Szabad kérdés módban exportálás és alaphelyzet gomb.
- Keresési idő kijelzése.
- V/VV parancsok azonosító-alapú varázslatkeresése, a VV több paraméterével.
- Parancsok felismerése a TF `* N. KP: vv ...` fejléceiből is.
- Eseményindex verzió 4: a régi indexek automatikusan HTML-forrásból olvashatók, újraindexelés ajánlott a gyorsításhoz.
- Opcionális párhuzamos szövegkeresés, fordulóazonosító-tartományokra bontva, külön SQLite-olvasófolyamatokkal. Automatikus mód nagyobb adatbázisnál 4 folyamatot választ; az adatbázis-kezelőben állítható.
- `blocks(turn_id)` SQL-index a fordulónkénti eléréshez (első indításkor a meglévő nagy adatbázison létrehozása időt vehet igénybe).
- A jelenlegi FTS5 teljes szöveges indexet nem alkalmazzuk olyan előszűrésre, amely a részszavas vagy ragozott találatok elvesztésével járna. Az FTS5 alapú további optimalizálás későbbi feladat.
