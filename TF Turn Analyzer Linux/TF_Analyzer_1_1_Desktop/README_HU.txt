TF Analyzer 1.1 Desktop Edition – Linux
Indítás: ./start.sh (szükség esetén chmod +x start.sh inditas.sh)
Első indítás internetet igényelhet. EndeavourOS: sudo pacman -S python python-pip
A start.sh kizárólag saját .venv környezetbe telepít. Qt grafikus környezet szükséges.
Régi adatbázis: leállított alkalmazások mellett másold a tf_analyzer.sqlite3 fájlt az új könyvtárba. Előtte készíts mentést. A séma változatlan.
Nexus interfész: /teljes/út/start.sh --fordulo "/teljes/út/fordulo.mhtml"
A már futó példány helyi Qt socketen fogadja a fájlt. A Nexus 1.3 kódját ez a csomag nem módosítja. A Nexus kontextusmenüjében az indítási paramétert és a már futó példány esetén is történő átadást külön kell beépíteni.
A fájlimport SHA-256 szerint deduplikál, nem fordulószám szerint. Az export a teljes kiválasztott táblázatot menti, nem a szövegszűrt nézetet.
A három elemzőmodul a 0.6.6-ból változatlan. A hiányzó HTML esetén a régi szöveges tartalékfeldolgozás működik.
1.1: választható harci mutatók, összesített és átlagos rangsor, Top 20/50/Mind, kattintható diagram, dupla kattintással megnyitható csaták, magyar oszlopnevek. Nettó ÉP: a játék közölt értéke, negatív = veszteség. Az eredeti szöveg a két csatastatisztika közötti szakasz, köztes eseményeket is tartalmazhat. Az elemzőmotor változatlan; okozott sebzés a meglévő sebzés mező, nem az opcionális összes sebzés mező. Teszt: Keiko 1671 (231 csata), Scott 2887 (516 csata), aggregált nettó és darabszám egyezik. Qt futtatás nem tesztelt (PySide6 nem elérhető).
