# TF Fordulókereső 1.9.6.1

- Egységes szótár-alapú eseményértelmezés: spell_use, item_acquire, item_use, npc_speech és harci csoportok.
- Ragozott varázslat- és tárgynevek feloldása az enciklopédiai entitásokhoz, ha az adatbázis elérhető.
- Többértelmű igéknél (használtam, alkalmaztam) az objektum típusa dönt.
- Fel nem ismert, egyértelmű varázslási kérdésnél értelmezési hiba, nem a teljes kérdésre végzett szövegkeresés.
- AI-keresési tervek ellenőrzése az új helyi értelmezővel.
- 6 új regressziós teszt; összesen 31 sikeres teszt.

Megjegyzés: a szabad kérdés kétlépcsős jóváhagyása és az adatbázis-kezelő változatlan. Az Ollama és a grafikus felület élő környezetben nem volt tesztelhető.
