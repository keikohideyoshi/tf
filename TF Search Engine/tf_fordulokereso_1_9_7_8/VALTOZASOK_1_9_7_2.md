# 1.9.7.2 – keresési diagnosztika

- A főablakban **Keresési diagnosztika** jelölőnégyzet; alapértelmezetten kikapcsolva.
- Bekapcsolva minden végrehajtott keresés JSON-sor naplója: `logs/search_performance.log`.
- Dátum, keresés típusa, tárgyazonosító, esemény típusa, eltelt idő, keresőszál CPU-ideje, találatok száma.
- Tárgyeseményeknél FTS5-előszűrés, jelöltlista TEMP tábla, blokkok lekérdezése/feldolgozása, HTML-beolvasás és linkfelismerés szakaszonkénti ideje, feldolgozott blokkok és fordulók száma.
- A napló nem tartalmazza a szabad kérdés szövegét vagy a fordulók tartalmát.
- **Naplómappa** gomb: a logkönyvtár megnyitása.
- A diagnosztika a kereső algoritmusát nem módosítja. Az időadatok átfedő szakaszokat is tartalmazhatnak, ezért nem minden esetben összeadhatók.
- A többprocesszoros munkák CPU-ideje ebben a kiadásban nem összesített; a `thread_cpu_seconds` a keresést indító szálé.
