# TF Fordulóletöltő 1.3 – Linux

Indítás: `./start.sh` (ha szükséges: `chmod +x start.sh`). EndeavourOS/Arch: hiányzó rendszerfüggőség esetén `sudo pacman -S python tk`. Az indító saját .venv környezetben telepíti a Playwrightot és Chromiumot, nem használ rendszerszintű pipet. A korábbi böngészőprofil változatlan.

- ZIP-ek letöltése + HTML: jelentkezz be a megnyíló böngészőben, majd kattints a Bejelentkezés kész gombra. A ZIP-ek megmaradnak. Az ismert ZIP-linkeket a helyi index alapján kihagyja; régi, még nem indexelt ZIP-eknél a böngészőnek el kell indítania a letöltést a fájlnév megállapításához.
- Nyilvános fordulók: karakterazonosító, típusok és opcionális számtartomány. A tartomány az adott típus sorszámára vonatkozik (olimpiánál olimpiaszám). Közvetlen HTTPS, bejelentkezés nélkül; csak a karakteroldalon ténylegesen felsorolt linkek. A speciális típusok ellenőrzése konzervatív, ismeretlen formátumot nem ment el.
- HTML-ek kigyűjtése: meglévő ZIP-ekből, lapos HTML almappába. Offline CLI: `./start.sh --html-only --cel /útvonal`.
- Megszakítás: az aktuális hálózati művelet befejeződése vagy időtúllépése után. Újraindítással folytatható. A nyilvános letöltés két másodperc szünetet tart, 401/403/429/503 esetén leáll. Csak teljes, ellenőrzött válasz kerül végleges fájlba; meglévő hibás fájlt nem ír felül.

A nyilvános HTML-ek eredeti bájtjai megmaradnak; képek és külső stíluslapok nem kerülnek letöltésre. A minták alapján 903 link felismerése és a normál forduló ellenőrzése tesztelt. Élő letöltés, speciális fordulók és grafikus indítás még felhasználói tesztet igényelnek. A szűrők a nyilvános módra vonatkoznak. Tömeges letöltés előtt ellenőrizd a szolgáltató feltételeit.
