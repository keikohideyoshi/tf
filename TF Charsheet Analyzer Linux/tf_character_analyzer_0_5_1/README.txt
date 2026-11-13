TF Character Analyzer 0.5.1
=========================

Indítás EndeavourOS / Arch Linux alatt:
  sudo pacman -S python python-beautifulsoup4 tk
  ./start.sh

Az indító futtatható jogosultsággal van csomagolva. Ha egy fájlkezelő
kicsomagoláskor elveszíti ezt a jogosultságot: chmod +x start.sh

A program HTML, HTM, MHTML és MHT fordulókat dolgoz fel.
Több fájl is kijelölhető egyszerre. Az adatokat a program könyvtárában
létrejövő tf_karakterlapok/tf_karakterek.sqlite3 tárolja.
Az újabb import nem törli a korábban feldolgozott más fordulókat.
Azonos forduló újraimportálásakor annak adatai frissülnek.

A fájlválasztó ablakban a Mégse gomb megnyomása után is újragenerálható
az összes korábban importált karakter fejlődéstörténeti jelentése.

A tf_karakterlapok/Keiko_Hideyoshi_fejlodestortenet.html fájlt
Firefoxban nyisd meg. A jelentésben a kezdő és záró forduló
interaktívan változtatható, minden statisztika azonnal újraszámolódik.

Parancssori használat (opcionális):
  ./start.sh -o tf_karakterlapok fordulo1.html fordulo2.mhtml

Fontos: ha a korábbi 0.4-es verzióval már több fordulót importáltál,
őrizd meg a régi tf_karakterlapok/tf_karakterek.sqlite3 fájlt!
Másold át ugyanebbe az útvonalba az új program mappájába, és az
újrahasználja a teljes archívumot. Ne írd felül a saját adatbázisodat
a csomag teszt/ mappájában lévő négyfordulós mintával.

Szintlépési ütem: a kiválasztott időszakban megfigyelt fordulóközök /
pozitív szintváltozás. Hiányzó forduló esetén nem becsülünk ütemet.
Az átlagos TP és szörnyölés a kiválasztott, betöltött fordulókra
vonatkozik; hiányzó értékek kimaradnak az átlag nevezőjéből.

A teszt/ mappa az 1679–1682. fordulók demonstrációs jelentését,
és négyfordulós tesztadatbázist tartalmazza.

0.5.1: Szintlépési ütem a két szélső ismert szintből, fix harciérték-sorrend, ikonokkal ellátott ragadós navigáció, automatikus böngészőmegnyitás.
