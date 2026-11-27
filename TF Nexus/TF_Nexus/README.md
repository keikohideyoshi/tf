# TF Nexus 1.0
EndeavourOS / Arch Linux, Python és PySide6. Kicsomagolás után `./start.sh`. Az első indítás szükség esetén telepíti a pyside6 csomagot, rendszerfrissítés nélkül. Arch részleges frissítése nem támogatott: függőségi hiba esetén ne erőltesd a telepítést. Az asztali menühöz `./install-desktop.sh` (előbb futtasd a start.sh-t).

A hat előkészített kártya útvonala üres. Szerkesztés vagy jobb kattintás, majd Tallózás. Dupla kattintás vagy Indítás gomb indít. A szkript saját mappájából fut. A kártyák az Összes nézetben, üres kereső mellett húzhatók át. Kedvencek a jobb gombos menüben. A konfiguráció a config.json fájlban van, mentése config.json.bak. A naplók a logs mappában találhatók. A négy téma és a háttér azonnal váltható.

A folyamatfigyelés Linux munkamenet-azonosító alapján működik, a Nexus bezárása után is. A külön munkamenetbe leváló alkalmazások vagy külsőleg indított példányok nem feltétlenül felismerhetők. Az i3 felülbírálhatja az ablakméretet és pozíciót. A grafikus futás ebben a build környezetben nem volt tesztelhető.

## 1.1 frissítés
Zárd be a régi Nexust. Az új csomagot külön könyvtárba csomagold ki, futtasd az `./update.sh` szkriptet, és add meg a régi Nexus könyvtárát. A konfiguráció, ikonok és naplók megmaradnak. A szkript biztonsági mentést készít. A régi könyvtárból indítsd a Nexust.
A Karakterek… gombbal add meg a nevet és a fordulók mappáját. A lista 10 másodpercenként frissül, a fel nem ismert fájlokat számlálja. MHTML, MHT, HTML, HTM prioritás. A helyi fájlokat az operációs rendszer társított alkalmazása nyitja meg; MHTML esetén állíts be azt támogató böngészőt.

## 1.2 – Pantheon Edition
Nyolc új téma, egyedi SVG fantasy hátterekkel. A Témagaléria gomb színes előnézeti gombokat kínál. Raia világos téma; a többi sötét. A Fantasy háttér kapcsoló továbbra is működik. A meglévő 1.1 konfiguráció megmarad. Frissítés: zárd be a Nexust, futtasd az update.sh fájlt az új csomagból, add meg a régi könyvtárat.

## 1.3 – Saját könyvjelzők
A fejléc minden témában: Túlélők Földje alkalmazásközpont. A Könyvjelzők menüben weboldalakat (HTTP/HTTPS), fájlokat és könyvtárakat adhatsz hozzá. A kezelőben a kijelölt elem után kerül az új könyvjelző vagy elválasztó. A sorrend húzással módosítható, a változások azonnal mentődnek. A törlés csak a menüelemet érinti. A célokat a rendszer társított alkalmazása nyitja meg. Hiányzó cél esetén a könyvjelző megmarad. Frissítés az update.sh segítségével, a régi konfiguráció megőrzésével.

## 1.4 – TF Analyzer integráció
A TF Analyzer 1.1 kártyáján a Desktop Edition `start.sh` fájlját állítsd be.
A letöltött fordulók táblázatában jobb kattintás → Elemzés a TF Analyzerrel.
A Nexus a teljes fájlútvonalat `--fordulo` paraméterrel adja át; a már futó Analyzer saját helyi kommunikációja fogadja a kérést. A normál indítás változatlan.
Meglévő Nexus frissítéséhez zárd be, majd az új csomagból futtasd az `update.sh` fájlt. A konfiguráció megmarad.
