# TF Nexus 1.0
EndeavourOS / Arch Linux, Python és PySide6. Kicsomagolás után `./start.sh`. Az első indítás szükség esetén telepíti a pyside6 csomagot, rendszerfrissítés nélkül. Arch részleges frissítése nem támogatott: függőségi hiba esetén ne erőltesd a telepítést. Az asztali menühöz `./install-desktop.sh` (előbb futtasd a start.sh-t).

A hat előkészített kártya útvonala üres. Szerkesztés vagy jobb kattintás, majd Tallózás. Dupla kattintás vagy Indítás gomb indít. A szkript saját mappájából fut. A kártyák az Összes nézetben, üres kereső mellett húzhatók át. Kedvencek a jobb gombos menüben. A konfiguráció a config.json fájlban van, mentése config.json.bak. A naplók a logs mappában találhatók. A négy téma és a háttér azonnal váltható.

A folyamatfigyelés Linux munkamenet-azonosító alapján működik, a Nexus bezárása után is. A külön munkamenetbe leváló alkalmazások vagy külsőleg indított példányok nem feltétlenül felismerhetők. Az i3 felülbírálhatja az ablakméretet és pozíciót. A grafikus futás ebben a build környezetben nem volt tesztelhető.
