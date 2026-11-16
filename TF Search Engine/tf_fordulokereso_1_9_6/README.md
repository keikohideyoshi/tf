# TF Fordulókereső 1.9.4

A párhuzamos importálás részletei: `VALTOZASOK_1_9_4.md`.


A javítás részletei: `JAVITAS_1_9_1.md`.

# TF Fordulókereső 1.8 – használati útmutató

## Indítás (EndeavourOS / Arch Linux)

```bash
chmod +x start.sh
./start.sh
```

A `start.sh` saját `.venv` környezetet készít, így nem ütközik az Arch Linux externally-managed-environment korlátozásába. Ha a Tkinter hiányzik: `sudo pacman -S tk`.

## Új funkció: Objektumkeresés

A keresési módok között válaszd az **Objektumkeresés** módot. A **Objektum kiválasztása** gombbal a három referencia-HTML-ből felépített katalógusban kereshetsz névre (ékezetfüggetlenül), vagy `#211` alakú azonosítóra. A találatoknál egyértelműen látszik az objektum típusa, azonosítója és neve. A kiválasztott objektum neve automatikusan a keresőmezőbe kerül.

A keresés **csak az importált fordulókban** történik. A szörny-, tárgy- és varázslat-enciklopédia a kereséshez segédadat, önmagában nem ad fordulótalálatot.

A kiválasztott objektumra a program kétféle előfordulást keres:

- **Név:** az enciklopédiában szereplő teljes név, ékezetfüggetlenül, szóhatárokkal.
- **Azonosító:** csak egyértelműen típusozott hivatkozások, például `211. tárgyat` vagy `71. varázslatot`. Szörnyeknél csak a kifejezett `szörny #467` / `lény #467` alakot ismeri fel. A puszta `211`, `#211` vagy más, nem típusozott szám **nem** számít találatnak.

A találati táblázat új **Egyezés** oszlopa megmutatja, hogy a fordulóban név, azonosító vagy mindkettő alapján történt egyezés. Egy találat továbbra is egy forduló; megmaradt az előfordulásszám, a példák, a HTML megnyitása, a rendezés és a CSV/XLSX export. Az exportban az egyezés típusa is szerepel.

### Fontos korlátok

- Ez **objektumemlítés-keresés**, nem eseményfelismerés: egy tárgy említése nem bizonyítja annak megszerzését, és egy szörny említése nem bizonyítja a vele való csatát.
- Az azonosítós szabályok szándékosan szigorúak. Ha a játék más alakban írja ki az azonosítót, azt a jelenlegi verzió nem feltétlenül találja meg.
- Az előfordulásszám az indexelt szövegblokkokból készül; az importáló nem garantálja minden HTML-részlet lefedését.
- Az objektum kiválasztása különösen fontos a több kategóriában előforduló azonosítóknál (pl. `#211` tárgy, szörny vagy varázslat is lehet).

## Adatbázis átvétele

A korábbi 1.4-es programot zárd be, készíts biztonsági másolatot, majd másold át a `data/tudasbazis.sqlite3` fájlt az 1.5-ös verzió azonos helyére. A korábbi adatbázis-séma változatlan; a referenciakatalógusnak benne kell lennie. Ha új, üres adatbázist használsz, a csomagolt adatbázis már tartalmazza a három referencialistát, de **nem tartalmaz importált karakterfordulókat**.

## Megőrzött funkciók

- Pontos kifejezéses és intelligens (ÉS/VAGY/NEM) keresés.
- Háttérben futó mappaimport százalékos előrehaladással.
- Karakter szerinti szűrés, forduló- és előfordulásszám szerinti kattintható rendezés.
- Találatok CSV és XLSX exportálása.
- Sötét, működő natív Tk legördülő menük; Bezárás gomb.

## 1.5.1 – Teljes HTML-indexelés, újraindexelés és keresési állapot

- A HTML-fordulók teljes **látható törzsszövegét** dolgozzuk fel, beleértve a táblázatok közötti, közvetlenül a `body` alatt álló szövegeket, a `BR`-rel elválasztott eseményeket és a beágyazott formázott szövegeket. A `script`, `style` és rejtett elemek kimaradnak.
- Az indexelő dokumentumsorrendben halad, a szöveget nem duplikálja a szülő/gyerek HTML-elemek többszörös beolvasásával. A túl hosszú szövegrészeket felosztja, nem dobja el.
- A **Fordulók újraindexelése** gomb a korábban importált fordulókat az adatbázisban rögzített eredeti fájlelérési útjukról olvassa újra. Folyamatjelzővel dolgozik, a hiányzó forrásokat jelzi, és azok régi adatait megőrzi. Az újraindexelés előtt ajánlott az adatbázisról biztonsági másolatot készíteni.
- A keresések háttérszálon futnak; az állapotsorban „Keresés folyamatban… Dolgozom…” olvasható. Az elavult keresések eredményei nem írják felül az újabb keresést.
- Silverina (#2081) 328. fordulójával ellenőrizve: az „ősi gyógyítás” 12 előfordulása, ebből 10 feltételes gyógyítás, az új indexben kereshető.

**Adatbázis átvitele:** az 1.5-ös verzió bezárása után másold át a régi `data/tudasbazis.sqlite3` fájlt az 1.5.1-es mappa azonos helyére. Indítás után kattints a **Fordulók újraindexelése** gombra. Az újraindexeléshez az eredeti HTML-fájloknak a korábban importált elérési útjukon kell lenniük. Ha időközben elmozgattad őket, az új mappából a „Mappa importálása” funkcióval újra beolvashatod a fájlokat; a régi, hiányzó útvonalakhoz tartozó adatok nem törlődnek automatikusan.

## Újdonságok – 1.6

- **Lekerekített, ikonos gombok** a felső műveletsoron (import, újraindexelés, objektumválasztás, megnyitás, export). A gombok tisztán Tkinter Canvas-alapúak, nem igényelnek új GUI-függőséget. A bezárás és az objektumválasztó megerősítő gombja is ilyen.
- **Tárgyesemény-szűrő** az objektumkereséshez: *Összes említés / Megszereztem / Használtam / Leadtam*. A kiválasztott tárgy enciklopédiai neve és az egyértelműen típusjelölt tárgyazonosító egyaránt használható.
- **Óvatos eseményfelismerés:** csak a szereplő cselekvésére utaló kifejezett igékkel, rövid szövegkörnyezetben egyező tárgyhivatkozásokat számoljuk. Negált és bizonytalan kifejezéseket igyekszünk kizárni. Nem minden ragozott alak vagy összetett játékhelyzet felismerhető: a találatok **szövegminta-alapú eseményjelöltek**, nem garantáltan teljes vagy tévedhetetlen eseménynapló.
- A szörnyekre és varázslatokra az eseményszűrő még nem vonatkozik; az eddigi objektumkeresés változatlan.
- A korábbi **pontos/intelligens keresés**, CSV/XLSX export, oszloprendezés, háttérkeresés, teljes HTML-indexelés és újraindexelés megmaradt.
- **Adatbázis-kompatibilis** az 1.5.1-gyel; a 1.6-os eseményszűrőhöz nincs szükség újraindexelésre, ha már 1.5.1-gyel indexeltél.

### Frissítés

Az alkalmazás bezárása után készíts másolatot a korábbi `data/tudasbazis.sqlite3` fájlról, majd másold az 1.6-os mappa `data` könyvtárába. Indítás: `./start.sh`.

## 1.6.1 – Pontosabb tárgyszerzés-felismerés

- Felismeri a szörnyektől szerzett zsákmány bevezetőit: `Szerzeményed: 1 rítusónix` és `Lássuk, mire bukkantál: 1 rítusónix`.
- A bevezető után közvetlenül álló tárgyat kapcsolja az eseményhez; az ugyanabban a fordulóban előforduló tárgylistákat és enciklopédiai említéseket nem tekinti automatikusan szerzésnek.
- Silverina 282. és 286. fordulójával tesztelve, a rítusónix (#751) mindkét fordulóban egy szerzési eseményként szerepel.
- Az 1.6-os adatbázissal kompatibilis; újraindexelés nem szükséges.


## 1.7 – Harci események
Új „Harci események” keresési mód: győzelem, menekülés, halál, ismeretlen, összes harc.
Az utolsó 50/100/200 vagy összes importált forduló választható. Szörny nélkül is keres.
Az eredményeket az eredeti HTML-ekből olvassa ki, így nincs adatbázis-migráció; a fájlokat nem szabad áthelyezni.
A tárgyak megszerzési/használati felismerője változatlan. A „Leadtam” menüpont kivezetve.
A szörny azonosítása többellenfeles csatáknál ellenőrzést igényelhet.


## 1.7.1 – felületi finomítások
- Egységesebb, finom vonalrajzos ikonok és normál (nem félkövér) gombfeliratok.
- Új „Alaphelyzet” gomb: minden keresési mező és szűrő visszaállítása, a találatok törlése.
- A tárgyfelismerő és a keresési algoritmusok változatlanok.

## 1.8 – Szabad kérdéses keresés (első kiadás)

A felső **Szabad kérdés** mezőbe természetes magyar nyelvű kérdés írható. A **Kérdés megválaszolása** gomb a meglévő keresőmotorra épülő, óvatos értelmezést és forrásforduló-listát ad. A találatok exportálhatók és dupla kattintással megnyithatók. A kérdésértelmezés jelenleg **korlátozott**, nem általános nyelvi megértés; a nem értelmezhető kérdések hibajelzést adhatnak. A harci eredményekhez az eredeti HTML-fájlok szükségesek.

Az **Online AI beállítás** ablakban opcionálisan OpenRouter API-kulcs és **`:free` végű modellazonosító** adható meg. A modellválaszték, az ingyenes kvóták és az elérhetőség a szolgáltatótól függ; **korlátlan ingyenes használat nem garantált**. Az API-kulcsot csak a futó program memóriája őrzi, a program nem írja lemezre. Az online kérdésértelmezés kizárólag a beírt kérdést küldi az OpenRouternek; a helyi fordulóadatbázist és a forrásszövegeket nem. Online hiba esetén a program automatikusan a szabályalapú értelmezőre vált. Online AI nélkül is működik. Az online szolgáltatás használata előtt ellenőrizd annak adatkezelési feltételeit.

A keresés szöveges összefoglalót és ellenőrizhető találati listát jelenít meg. A találati lista a meglévő exportálóval menthető. A természetes nyelvű kérdésre adott összesítés az importált adatokra korlátozódik, és nem garantál teljes körű TF-eseményfelismerést. A szöveges találatok nem jelentenek bizonyított eseményt.

**Felület:** minden gomb ikon nélküli, normál betűvastagságú, visszafogott funkcionális színekkel. A meglévő tárgykereső és tárgyesemény-felismerő fájlja változatlan.

**Frissítés:** az 1.7.1 verzió bezárása után készíts biztonsági másolatot az adatbázisról, és másold a `data/tudasbazis.sqlite3` fájlt az új verzió `data` könyvtárába. Az eredeti HTML-ek maradjanak az importáláskor használt elérési útjukon. Újraindexelés nem szükséges.

## 1.9 – TF-fogalomtár, csataazonosítás, varázslatok és NPC-k

- A **Szabad kérdés** helyi értelmezője a `app/tf_dictionary.json` bővíthető szinonimáit és a három enciklopédiát használja. Az ismert szörnyek ragozott neveit azonosítja; a konkrét szörnyre vonatkozó halál/győzelem/menekülés keresés nem terjed ki más csatákra.
- A „bármilyen/valamilyen szörny” nem jelent szörnyazonosító-szűrést. Az egyértelműen ismeretlen megnevezett szörnyre inkább hibát jelez, mint hogy az összes harcot találatnak mutassa.
- A varázslatoknál külön kereshetők a csatán belüli, név szerint megjelenő varázslási események; a csatán kívüli, névvel kiírt varázslások is megjelenhetnek. Ez **konzervatív mintafelismerés**, nem minden varázslat és sikeresség automatikus felismerése. A puszta számozott `vv` parancs nem bizonyít sikeres varázslást.
- A KLD/BE események kereshetők parancsszám, név és egyszerű párbeszéd-/teljesítési jelzés alapján. A szöveg továbbra is az eredeti fordulóból származik, nem AI által kitalált válasz.
- A szabad kérdéses találatok fölött megjelennek az értelmezett feltételek. A helyben biztosan felismert szörny/varázslat/NPC feltételeket az online AI nem dobhatja el.
- Importáláskor és újraindexeléskor a csaták és a KLD/BE/varázslási utasítások **tömörített, helyi SQLite-eseményindexbe** kerülnek. A korábbi adatbázis átvehető, de a gyorsított eseménykereséshez ajánlott egyszer lefuttatni a **Fordulók újraindexelése** műveletet. Ha az eredeti HTML hiányzik, a régi eseményindex nem helyettesíti a forrásfájlt.
- A tárgykereső `app/object_search.py` változatlan. A meglévő exportálás, sötét felület, ingyenes/opcionális AI és a venv-es `start.sh` megmarad.

**Korlátok:** A részletes sebzésrangsor, a „majdnem meghaltam” szubjektív értelmezése, a teljes küldetéslánc rekonstrukciója, a tárgyszerzés forrásának automatikus azonosítása és minden szabad nyelvű kérdés megválaszolása még nincs kész. A varázslat- és NPC-keresés első, szövegmintákon alapuló változat; ellenőrizd a forrásfordulót. A `tests/test_natural_19.py` tesztek futtatása: `python -m unittest discover -s tests -v`.
