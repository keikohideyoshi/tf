# TF Fordulókereső 1.9.5.2 – AI-kérdésértelmezés javítása

- Az AI által javasolt keresési tervet a helyi szabályalapú értelmezővel egyeztetjük.
- A `last_n`, `first`, `latest`, `rank` mezők nem származhatnak pusztán az AI feltételezéséből.
- Harc, tárgy, varázslat és NPC esetén a helyi esemény- és enciklopédia-felismerés az irányadó.
- Javított „haltam meg” felismerés; a „Mikor haltam meg csatában?” keresés minden halálos csatára vonatkozik.
- Ismeretlen szörnyazonosító nélkül a harci keresésben nem jelenik meg kitalált szöveges szűrő.
- A felismert feltételek kijelzése nem mutat félrevezető `term` mezőt általános harci kérdésnél.
- Megmarad a korábbi 1.9.5.1 SQLite-zárolási javítás és az Ollama-telepítő felület.

Megjegyzés: az AI nem generálhat új keresési operátorokat. A szemantikus keresés továbbra is későbbi fejlesztés.
