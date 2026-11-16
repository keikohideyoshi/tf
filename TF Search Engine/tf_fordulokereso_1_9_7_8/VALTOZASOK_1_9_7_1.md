# TF Fordulókereső 1.9.7.1 – célzott tárgykeresési gyorsítás

- A `Megszereztem` / `Használtam` / `Leadtam` tárgyesemény-keresések FTS5 előszűrést kapnak.
- Az előszűrés az adott tárgy nevének első szavára (ragozást toleráló prefix) és azonosítójára épül.
- A program csak a jelölt fordulók szövegblokkjait és HTML-fájljait ellenőrzi, a korábbi eseményfelismeréssel.
- Hiányzó vagy hibás FTS5-tábla esetén a régi teljes keresés fut.
- Nincs adatbázis-migráció vagy kötelező újraindexelés.
- Három új regressziós teszt; összesen 37 sikeres teszt.

**Korlát:** A gyors előszűrés nem garantál teljes egyezőséget olyan ritka esetekben, amikor az eredeti HTML Enc-hivatkozásának látható szövege és az indexelt blokk sem a tárgy nevének első szavát, sem a tárgy azonosítóját nem tartalmazza. A 2 GB-os valós adatbázison még nem történt teljesítménymérés. Ellenőrizd a garling kristály #1463 korábbi 47 találat / 43 forduló értékét; eltérés esetén jelezd.
