# TF Fordulókereső 1.9.7.9

A program Linuxos kiadása. Indítás a főkönyvtárban: `chmod +x start.sh && ./start.sh`.

A korábbi verzió meglévő adatbázisát a program leállítása után, biztonsági mentés készítését követően másold a `data/tudasbazis.sqlite3` útvonalra. A `data/reference` enciklopédiák a csomagban találhatók.

**Új:** Objektumkeresés → válassz egy tárgyat → Tárgyesemény → **Alkímiáztam**.

**Szabad kérdés példák:**
- `Hányszor alkímiáztam nerub dobónyilat?`
- `Hány darab nerub dobónyilat alkímiáztam?`
- `Hányszor menekültem az utolsó 100 fordulóban?`
- `Hányszor haltam meg az utolsó 100 fordulóban?`
- `Hányszor szereztem nerub dobónyilat?`

A szabad kérdés mód két lépéses: **1. Kérdés értelmezése**, majd **2. Keresés indítása**.

A részletes változásokat és a felismerés korlátait lásd: `VALTOZASOK_1_9_7_9.md`.
