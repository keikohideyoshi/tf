# TF Fordulókereső 1.9.7.5

- A V és VV parancsok varázslat-ID-ját kizárólag a parancs fejlécéből olvassa ki, nem a hozzá tartozó teljes szövegből.
- Minden egyező V/VV pozíció külön esemény, beleértve a sikertelen kísérleteket és az ismétlődő varázslatokat.
- A harci varázslatok keresését FTS5-ös forduló-előszűrés gyorsítja, ha a meglévő FTS-index elérhető. Hiányzó FTS esetén a régi teljes feldolgozás marad.
- A harci keresés külön vizsgálja az egyes mondatokat, és kiszűr több ellenfélhez tartozó megfogalmazást.
- Új regressziós tesztek a vv 171 171 171 téves találatra és a vv 75 75 109 dupla találatra.

Megjegyzés: a teljes, több GB-os felhasználói adatbázison a futásidő nem volt mérhető a kiadási környezetben. A harci szövegek értelmezése továbbra is heurisztikus; a V/VV azonosítás pontos.
