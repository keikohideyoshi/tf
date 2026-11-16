# TF Fordulókereső 1.9.7.4 – SQLite-szintű tárgyesemény-előszűrés

- A tárgyesemény-keresés a meglévő akcióige- és zsákmánybevezető regexekkel szűri a blokkokat már az SQLite-lekérdezésben, így a nem releváns blokkok nem kerülnek át a Python találatfeldolgozásába.
- A felismerési feltétel azonos a 1.9.7.3 gyors kizárási feltételével; az eseményazonosítás többi szabálya változatlan.
- A diagnosztika új számlálói: `blocks_scanned_in_sql`, `blocks_filtered_in_sql`, `blocks_read`.
- Nem kell adatbázist újraimportálni vagy újraindexelni.
- Az SQL-szűrés továbbra is átvizsgálja a jelölt fordulók blokkjait; ez nem egy új perzisztens index. A sebességnyereséget a felhasználó adatbázisán kell mérni.
