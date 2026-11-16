# TF Fordulókereső 1.9.7.8 – Felhasználói kézikönyv

**Kezdőknek és haladóknak · Linux / EndeavourOS · 2026. november**

## 1. Mire való a program?

A **TF Fordulókereső** a *Túlélők Földje* játékból lementett HTML-formátumú fordulókban keres. A célja, hogy sok száz vagy több ezer forduló átnézése helyett gyorsan megtaláld, hol szerepelt egy szó, tárgy, szörny, varázslat, csata vagy bizonyos játékbeli esemény.

A program **helyben, a saját számítógépeden** tárolja és dolgozza fel a fordulókat egy SQLite-adatbázisban. A keresés alapfunkcióihoz nem szükséges online mesterséges intelligencia. Az enciklopédiák segítenek azonosítani a tárgyakat, szörnyeket és varázslatokat, de **nem helyettesítik a ténylegesen importált fordulókat**.

**Fontos különbség:** egy szó vagy tárgy *említése* nem feltétlenül jelenti azt, hogy a karakter megszerezte, használta vagy legyőzte. Az eseménykeresések külön felismerési szabályokat alkalmaznak, de a forrásforduló ellenőrzése továbbra is ajánlott.

## 2. A csomag tartalma és a rendszerigény

A ZIP-csomag többek között a következőket tartalmazza:

- `start.sh` – Linuxos indító, amely a saját Python-környezetet is előkészíti.
- `app/` – a program forráskódja.
- `data/reference/` – a tárgy-, szörny- és varázslat-enciklopédia.
- `data/tudasbazis.sqlite3` – a helyi adatbázis, ha már létrejött.
- `logs/` – keresési diagnosztikai naplók.
- `requirements.txt` – a szükséges Python-csomagok listája.
- `tests/` – fejlesztői ellenőrzőtesztek.

A program Python 3-at, Tkintert, valamint a `beautifulsoup4`, `lxml` és `openpyxl` csomagokat használja. Linuxon grafikus asztali környezet szükséges. A csomagban lévő `start.sh` kifejezetten Linuxra készült; ez nem Windows-telepítő.

### Első indítás EndeavourOS / Arch Linux alatt

1. Csomagold ki a ZIP-et egy tetszőleges könyvtárba.
2. Nyiss terminált a kicsomagolt program főkönyvtárában.
3. Ha még nincs Python és Tkinter, telepítsd:

   ```bash
   sudo pacman -S python tk
   ```

4. Add meg az indítási jogot, majd indítsd el:

   ```bash
   chmod +x start.sh
   ./start.sh
   ```

Az indító a program könyvtárában `.venv` nevű elkülönített Python-környezetet hoz létre, és szükség esetén telepíti a Python-függőségeket. Az első indításhoz ezért internetkapcsolat kellhet. **Nem szükséges és nem ajánlott** a függőségeket rendszerszinten `sudo pip` paranccsal telepíteni.

Később általában elegendő a `./start.sh` parancs.

## 3. Az első használat: fordulók importálása

A kereső csak a már beolvasott fordulókban tud keresni.

1. Kattints az **Adatbázis-kezelő** gombra.
2. Válaszd a **HTML-mappa importálása** lehetőséget.
3. Jelöld ki azt a könyvtárat, amelyben a mentett TF-fordulók HTML-fájljai vannak.
4. Várd meg az importálás végét. A főablak állapotsora és a százalékos folyamatjelző tájékoztat az előrehaladásról.
5. Az importálás végén ellenőrizd a jelzett fájl- és hibaszámot.

A program több feldolgozófolyamattal is tud importálni. Az **Importálási feldolgozók** beállításnál az **Automatikus** az ajánlott kiindulási érték. A már változatlan fájlokat a program igyekszik kihagyni.

**Ne mozgasd el és ne töröld az eredeti HTML-fájlokat** az importálás után. Egyes keresési módok, a harci események és a forrásforduló megnyitása továbbra is igényelhetik az eredeti fájlokat.

### Ha már használtál korábbi verziót

1. Zárd be a régi programot.
2. Készíts biztonsági másolatot a régi `data/tudasbazis.sqlite3` fájlról.
3. Másold át a fájlt az új verzió `data/` mappájába.
4. Indítsd el az 1.9.7.8-as verziót.

A varázslatkereséshez szükséges új index automatikusan létrejöhet. **Az első nem harci varázslatkeresés hosszabb lehet**, mert ekkor épülhet fel a korábban importált fordulók indexe. A későbbi keresések ezt az indexet használják.

## 4. A főablak áttekintése

A felső **Keresési felület** választóval két fő munkamód között válthatsz:

- **Kulcsszavas keresés** – közvetlen keresés, különféle keresési módokkal és szűrőkkel.
- **Szabad kérdés** – magyar nyelvű kérdést írsz, a program előbb értelmezi, majd jóváhagyás után keres.

A felső sávban található az **Adatbázis-kezelő**, az **AI beállítások**, a **Keresési diagnosztika** jelölőnégyzet és a **Naplómappa** gomb is.

Az eredmények táblázatának oszlopai:

| Oszlop | Jelentés |
|---|---|
| **Karakter** | A fordulóhoz tartozó karakter |
| **Forduló** | A forduló száma |
| **Előfordulás** | Az adott fordulóban felismert egyezések vagy események száma |
| **Egyezés** | Az egyezés típusa, ha az adott keresés értelmezi |
| **Szövegkörnyezet (első találat)** | Részlet a találat környezetéből |

Egy táblázatsor általában **egy fordulót** jelöl; egy fordulón belül több előfordulás is lehet. A sor kijelölése további részleteket mutathat. **Dupla kattintással** megnyithatod az eredeti HTML-fordulót.

A **Találatok exportálása** gombbal CSV- vagy XLSX-fájl készíthető. Az **Alaphelyzet** törli a keresési feltételeket és az aktuális eredményeket.

## 5. Kulcsszavas keresés

Válaszd a **Kulcsszavas keresés** felületet, majd írd be a keresett szót vagy kifejezést. A program rövid késleltetéssel automatikusan elindíthatja a keresést; nincs szükség külön indítógombra.

A karakterválasztóval egy adott karakterre vagy **Minden karakter** értékkel az összes importált karakterre szűrhetsz.

### 5.1. Pontos kifejezés

A megadott szöveg előfordulásait keresi. Akkor hasznos, ha pontosan tudod, milyen kifejezés szerepelhet a fordulóban.

**Példa:** `garling kristály`

### 5.2. Intelligens keresés

Összetettebb, ÉS/VAGY/NEM logikájú kereséshez való. A kereső a szöveges feltételek alapján ad találatokat; ez még nem jelenti a játékbeli esemény bizonyítását.

### 5.3. Objektumkeresés

A **Objektum kiválasztása** gombbal az enciklopédiai katalógusból választhatsz **tárgyat, szörnyet vagy varázslatot**. A katalógusban névrészlet vagy `#azonosító` alapján kereshetsz.

Az objektumkereső név szerinti előfordulásokat és bizonyos egyértelműen típusjelölt azonosítókat ismer fel. A puszta szám nem számít automatikusan tárgy- vagy varázslathivatkozásnak.

Tárgy esetén a **Tárgyesemény** szűrő értékei:

- **Összes említés** – a tárgyra utaló szövegek.
- **Megszereztem** – a karakter tárgyszerzésére utaló események.
- **Használtam** – a tárgy használatára utaló események.

Az eseményszűrő **csak tárgyaknál** használható. A tárgyesemény-felismerés szövegmintákon alapul: összetett vagy szokatlan megfogalmazású esetek kimaradhatnak.

### 5.4. Harci események

A **Harci események** keresési módban választható:

- **Összes harc**
- **Győzelem**
- **Menekülés**
- **Halál**
- **Ismeretlen**

Az **Időszak** mezőben az utolsó 50, 100 vagy 200 fordulóra, illetve az összes importált fordulóra szűrhetsz. Szörnyet is kiválaszthatsz az objektumválasztóval; üres keresőmező esetén az összes szörnyre vonatkozik a keresés.

**Példa:** ha az utóbbi 100 fordulóban történt halálokat keresed, válaszd a **Halál** eredményt és az **Utolsó 100 forduló** időszakot.

A csataeredmény és a konkrét ellenfél azonosítása összetett harcokban nem feltétlenül hibátlan; a fontos találatokat ellenőrizd az eredeti fordulóban.

## 6. Szabad kérdés – keresés magyar mondatokkal

Ez a kezdők számára gyakran a legkényelmesebb felület.

1. A **Keresési felület** választóban válaszd a **Szabad kérdés** módot.
2. Írj egy magyar nyelvű kérdést.
3. Kattints az **1. Kérdés értelmezése** gombra.
4. Nézd át a megjelenő keresési tervet.
5. Szükség esetén módosítsd a feltételeket.
6. Kattints a **2. Keresés indítása** gombra.
7. Tekintsd át a találatokat, majd szükség esetén exportáld őket.

**Fontos:** a kérdés értelmezése önmagában **még nem futtatja le a keresést**.

### Kipróbálható kérdések

- `Mikor szereztem garling kristályt?`
- `Mikor használtam sáfrányport?`
- `Mikor varázsoltam mágiafeloldást?`
- `Mikor varázsoltam savzuhatagot?`
- `Mikor menekültem el egy harcból?`
- `Mikor győztem le egy adott szörnyet?`

A kérdésértelmezés nem korlátlan általános nyelvi megértés. Ha nem érti pontosan a kérdést, fogalmazd át egyszerűbben, vagy módosítsd az értelmezett keresési tervet.

### A keresési terv mezői

A program a kérdés alapján megjelenítheti a **Típus**, **Harci eredmény**, **Tárgyesemény**, **Keresett kifejezés**, **Utolsó N forduló** és **Találatok** mezőket. Az utóbbi lehet **Összes**, **Legutóbbi** vagy **Legelső**.

A keresés típusa belsőleg például `battle`, `item`, `text`, `spell` vagy `npc` lehet. Ezek a harci, tárgy-, szöveges, varázslat- és NPC-keresésnek felelnek meg.

A **Tárgy / szörny kiválasztása** gombbal opcionálisan pontosíthatod a kérdés tárgyát, ha a név többértelmű. Az **Objektum törlése** eltávolítja ezt a megkötést.

## 7. Varázslatok keresése – az 1.9.7.8 fontos újdonsága

A program a csomagolt **Varázslatok összefoglaló.html** enciklopédia **hatás** oszlopa alapján két csoportra osztja a varázslatokat:

| A „hatás” értéke | Keresési út |
|---|---|
| `támadó` vagy `védekező` | Harci szövegek vizsgálata |
| Bármilyen más érték | `V` / `VV` parancsok keresése |

A két kategória egymást kizárja.

### 7.1. Nem harci, V/VV varázslatok

A `V` és `VV` parancsokban a varázslatok azonosítója szerepel. A program ezeket külön SQLite-indexben tárolja, így az index felépítése után **nem kell minden kereséskor végigolvasnia az összes fordulót**.

**Példa:** `Mikor varázsoltam mágiafeloldást?` – a mágiafeloldás azonosítója `#75`.

A `VV 109 75 365` parancs egy #75-ös előfordulást tartalmaz. A `VV 75 75 109` parancs kettőt. A `VV 171 171 171` parancs **nem** számít #75-ös találatnak.

A sikeres és sikertelen varázslási **kísérletek egyaránt számítanak**.

**Első keresés:** az index esetleges feltöltése miatt hosszabb ideig tarthat.

**Későbbi keresések:** a már felépített indexből rendszerint lényegesen gyorsabban futnak. A sebesség a saját adatbázis méretétől és állapotától függ.

### 7.2. Harci varázslatok

A harci varázslatok a harcok szövegében, név szerint jelennek meg. Ezeket a kereső a harci szöveg alapján próbálja felismerni.

**Példa:** `Mikor varázsoltam savzuhatagot?`

A programnak különbséget kell tennie a karakter saját varázslása, az ellenfél varázslása és az egyszerű említés között. Emiatt a harci keresés lassabb lehet, és a forrásforduló ellenőrzése különösen fontos.

## 8. AI beállítások – opcionális segítség

Az **AI beállítások** ablakban a program **helyi Ollama** modellt használhat a kérdés értelmezésének támogatására. A forráskód szerinti alapértelmezett modell: `qwen3:1.7b`.

Az AI nem feltétele a működésnek: a program helyi, szabályalapú értelmezővel is használható. A helyi AI a kérdés szövegét kapja meg, nem a teljes fordulóadatbázist.

Az AI segíthet a keresési terv elkészítésében, de a tényleges találatokat a keresőmotor szolgáltatja. A keresési tervet mindig ellenőrizd, mielőtt elindítod a keresést.

## 9. Találatok megtekintése és exportálása

A találatok táblázatában kiválaszthatsz egy fordulót, és a részletező mezőben megvizsgálhatod a szövegkörnyezetet. Az eredeti forduló megnyitható dupla kattintással vagy a **Forduló megnyitása** gombbal, ahol ez a gomb megjelenik.

A **Találatok exportálása** lehetőséggel:

- **CSV** – táblázatkezelők és más programok számára.
- **XLSX** – Excelben és LibreOffice Calcban használható formátum.

A mentési párbeszédben válaszd ki a helyet és a fájlnevet. Az export az aktuális találati listára vonatkozik, nem az egész adatbázisra.

A **Forduló** és **Előfordulás** oszlopok fejléceire kattintva rendezheted az eredményeket; a kulcsszavas felületen külön rendezési választó is van.

## 10. Adatbázis-kezelés és újraindexelés

Az **Adatbázis-kezelő** ablakban található:

- **HTML-mappa importálása** – új fordulók beolvasása.
- **Fordulók újraindexelése** – a korábban beolvasott fordulók ismételt feldolgozása.
- **Importálási feldolgozók** – a párhuzamos import beállítása.
- **Keresési feldolgozók** – a kereséshez használt feldolgozók beállítása.

Újraindexelésre akkor lehet szükség, ha régi verzióból hoztál át adatbázist, vagy a kereshető tartalom feldolgozási szabályai megváltoztak. Ez a művelet sok fordulónál időigényes lehet.

Az újraindexeléshez az eredeti HTML-fájloknak elérhetőnek kell lenniük. Előtte készíts biztonsági másolatot az adatbázisról.

## 11. Keresési diagnosztika és hibakeresés

A felső **Keresési diagnosztika** jelölőnégyzet bekapcsolásával a program részletes teljesítménynaplót készít. A **Naplómappa** gombbal megnyithatod a naplókat tartalmazó könyvtárat.

A keresési napló alapértelmezett fájlja:

`logs/search_performance.log`

A napló tartalmazhatja a keresés típusát, azonosítóját, eredményszámát, teljes futási idejét, CPU-idejét és egyes feldolgozási szakaszok idejét. A nem harci varázslatoknál például az index feltöltése, az SQL-lekérdezés és az eredmények összeállítása külön is mérhető.

Ha lassú a keresés, érdemes a diagnosztikát bekapcsolni, majd a napló megfelelő sorát megőrizni.

## 12. Gyakori problémák és megoldások

### Nem indul a program

Ellenőrizd, hogy a terminál a program könyvtárában áll-e, a `start.sh` futtatható-e, és telepítve van-e a Python és a Tkinter. Indítsd terminálból, hogy a hibaüzenet látható legyen.

### `externally-managed-environment` hiba

Ne telepítsd kézzel a függőségeket a rendszer Python-környezetébe. Használd a csomagolt `./start.sh` indítót, amely `.venv` környezetet hoz létre.

### Nincsenek találatok

Ellenőrizd, hogy a megfelelő HTML-mappát importáltad-e, nincs-e túl szűk karakterszűrő vagy időszak, és a keresett objektum valóban szerepel-e az importált fordulókban. Szabad kérdésnél ellenőrizd a keresési tervet is.

### Az eredeti HTML nem nyílik meg

Lehetséges, hogy az importálás után áthelyezted vagy törölted a forrásfájlt. Állítsd vissza az eredeti helyére, vagy importáld újra a megfelelő mappából.

### Az első varázslatkeresés lassú

A nem harci varázslatoknál ez az index egyszeri felépítése miatt előfordulhat. Próbáld meg másodszor is ugyanazt a keresést. Ha továbbra is lassú, kapcsold be a **Keresési diagnosztika** lehetőséget.

### Egy tárgy szerepel a fordulóban, de nincs „Megszereztem” találat

A tárgy említése nem feltétlenül tárgyszerzés. A program csak bizonyos, felismerhető szerzési mintákat tekint eseménynek. Ellenőrizd a forrásfordulót.

### A kérdés értelmezése után semmi sem történik

Ez a kétlépcsős működés része: az **1. Kérdés értelmezése** után külön rá kell kattintani a **2. Keresés indítása** gombra.

## 13. Adatbiztonság és mentés

A legfontosabb saját adatod a `data/tudasbazis.sqlite3` fájl. Rendszeresen készíts róla biztonsági másolatot, különösen verzióváltás és újraindexelés előtt.

A biztonsági mentést **a program bezárása után** végezd, hogy ne másolj éppen módosítás alatt álló SQLite-adatbázist.

Őrizd meg az eredeti HTML-fordulókat is. Az adatbázis és a forrásfájlok együtt biztosítják a legteljesebb működést.

## 14. Ajánlott első próba – 5 perc alatt

1. Indítsd el a programot a `./start.sh` paranccsal.
2. Importálj egy kisebb mappát TF-fordulókkal az **Adatbázis-kezelő** ablakból.
3. Válaszd a **Kulcsszavas keresés** módot, és keress egy ismert szót.
4. Nyiss meg egy találatot dupla kattintással.
5. Válts a **Szabad kérdés** felületre.
6. Írj be egy egyszerű kérdést, például: `Mikor szereztem garling kristályt?`
7. Kattints az **1. Kérdés értelmezése**, majd a **2. Keresés indítása** gombra.
8. Exportáld a találatokat XLSX-formátumban.

Ha ez sikerül, már ismered a program legfontosabb munkafolyamatát.

---

### Rövid fogalomtár

**Forduló:** a játék egy feldolgozott körének HTML-naplója.  
**Importálás:** a HTML-fordulók beolvasása a kereshető adatbázisba.  
**Index:** előre elkészített keresési segédadat, amely gyorsítja a lekérdezéseket.  
**V/VV:** a nem harci varázslatok használatához kapcsolódó parancsok.  
**FTS / szövegkeresés:** szavak és kifejezések keresése a feldolgozott szövegben.  
**SQLite:** a program helyi adatbázis-kezelője.  
**Ollama:** opcionális helyi AI-környezet a kérdések értelmezéséhez.  
**CSV/XLSX:** a találatok exportálására szolgáló táblázatos fájlformátumok.

*Ez a kézikönyv a TF Fordulókereső 1.9.7.8 csomagjának README-fájlja, változásnaplója és tényleges felületi forráskódja alapján készült.*
