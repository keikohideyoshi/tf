# TF Fordulókereső 1.9.4 – gyorsított importálás

- Párhuzamos HTML-feldolgozás külön Python-folyamatokkal (ProcessPoolExecutor).
- A SQLite-adatbázist továbbra is csak a vezérlő folyamat írja, fordulónként atomi tranzakcióval.
- A blokkok kötegelt beszúrása (`executemany`), a meglévő FTS-triggerek megőrzésével.
- A változatlan fájlok SHA-256 alapján automatikusan kihagyhatók normál importáláskor.
- A teljes újraindexelés is több processzormagot használ; a hiányzó forrásokat megőrzi.
- A grafikus felületen az „Importálás feldolgozófolyamatai” mezőben Automatikus / 1 / 2 / 4 / 6 / 12 választható.
- Az automatikus beállítás legfeljebb 6 folyamatot indít, és általában hagy szabad CPU-kapacitást.
- A korábbi objektum-, harc-, esemény- és természetes nyelvi keresési funkciók változatlanok.

## Mérés (nem általános sebességgarancia)

3 valódi forduló (Silverina 304, 328 és Keiko Hideyoshi 1677), helyi környezet:
- korábbi, egyszálú `import_turn`: 3,21 másodperc
- új, 3 feldolgozófolyamatos import: 2,42 másodperc
- azonos: 9317 szövegblokk, 33 hibajelzés, 51 sáfránypor-esemény, 3 strukturált eseményindex.
- változatlan állományok újraimportja: ~0,004 másodperc.

Az első teljes import gyorsulása a háttértártól, a fordulók méretétől és a géptől függ. Sok kis vagy nagyon nagy fájlnál eltérő eredmény lehetséges.

## Adatbázis és indítás

A régi `data/tudasbazis.sqlite3` átmásolható. Nem kell újraindexelni a kereséshez; a gyorsítás a következő importáláskor vagy kézi újraindexeléskor lép működésbe. A `start.sh` a saját virtuális környezetet használja.
