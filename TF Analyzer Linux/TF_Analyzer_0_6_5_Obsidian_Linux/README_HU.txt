TF ANALYZER 0.6.5 – OBSIDIAN (LINUX)
=====================================

A 0.6.4 összes elemzőfunkciója és HTML/MHTML-támogatása megmaradt.

ÚJDONSÁGOK
1. A kezdőoldal tetején az „Adatbázis és alkalmazás kezelése” részben
   „Adatbázis kiürítése” gomb. A gomb csak a megerősítő jelölőnégyzet
   bepipálása után aktív. A művelet véglegesen törli a feltöltött
   fordulókat és azok eltárolt HTML-tartalmát az aktuális SQLite
   adatbázisból. A fájl és a táblaszerkezet megmarad, tehát azonnal
   feltölthetők új fordulók. A művelet nem vonható vissza!
2. „Bezárás” gomb: leállítja a helyi Streamlit-kiszolgálót.
   A böngészőlapot a felhasználónak kell bezárnia.

FRISSÍTÉS
1. Állítsd le a korábbi TF Analyzert (Ctrl+C).
2. Biztonsági másolatot készíthetsz a meglévő tf_analyzer.sqlite3 fájlról.
3. Csomagold ki a csomagot; a Python-forrásokat és .streamlit mappát
   másold a jelenlegi programkönyvtárba.
4. A meglévő tf_analyzer.sqlite3 fájlt NE írd felül!
5. Indítsd: ./inditas.sh

TÁMOGATOTT FÁJLOK: .html, .htm, .mhtml, .mht
A 0.6.4-ben bevezetett feltételes gyógyítás, moa spektroszkóp,
sáfránypor és HTML-alapú Hibajelzések felismerés megmaradt.

FONTOS: az adatbázis kiürítése visszavonhatatlan. A gomb nem
állítja vissza az eredeti fordulófájlokat, és nem törli a lemezen
külön tárolt HTML/MHTML-fájlokat.
