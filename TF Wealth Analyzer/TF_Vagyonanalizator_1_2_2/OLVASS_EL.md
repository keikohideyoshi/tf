# TF Vagyonanalizátor 1.2.2 — Linux

## Indítás

```bash
chmod +x start.sh
./start.sh
```

Az indító a `.venv` virtuális környezetet használja, a csomagokat abba telepíti. Internet csak az első függőségtelepítéshez kell.

## Árlista

A `hyper_arlista.csv` tartalmazza a felhasználó által lementett Hyper összefoglaló enciklopédia **EA/VE mezőjének első számát** (1 darab aranyértéke). Az árlista automatikusan betöltődik az indításkor, nem kell külön importálni, és minden induláskor a rögzített Hyper-értékeket állítja vissza. A `0/0` nulla arany. Hiányzó árak nem számítanak automatikusan nullának.

## Használat

1. Kattints a **Fordulók importálása** gombra; válassz HTM, HTML vagy ZIP fájlokat (többet is).
2. Az **Áttekintés és grafikon** fülön felül **mindig a legnagyobb importált fordulószám** szerinti vagyon jelenik meg.
3. A grafikon az összes importált forduló időbeli vagyonváltozását mutatja, arany / tárgyak / saját bankszéf bontásban.
4. A **Fordulók** táblázat egy régebbi sorára kattintva a tárgy- és változástáblák azt a fordulót mutatják, a fő összesítés továbbra is a legújabbat.
5. A tárgyak nettó megszerzését/vesztését a két feldolgozott készlet összehasonlítása adja. A forduló közbeni forgalom ebből nem állapítható meg.
6. A **CSV export** minden forduló vagyonát exportálja.

A KT kincstárát nem számoljuk bele. A saját bankszéf igen. Ha hiányzó tárgyár van, a megjelenített vagyon **ismert minimum**, nem teljes vagyon. A grafikon is ezt az ismert értéket ábrázolja.

## Minták

A `mintak/` könyvtárban az 1700. és 1701. forduló ZIP-jei szerepelnek.

## 1.2 – Tárgyelemzés
- Összevont tárgylista, számszerűen rendezhető oszlopok, vagyonarány és nettó változás.
- Együttes szűrés: név/ID, hely, ár státusza, nettó változás, darabszám/egységérték/összérték minimum és maximum.
- TOP 10/25/50/100 összérték, egységérték vagy darabszám alapján; a teljes kiválasztott forduló készletéből, a szűrőktől függetlenül.
- A történeti nézetben kiválasztott forduló adatait mutatja; az áttekintés továbbra is a legutolsót.
- A nettó változás az előző importált fordulóhoz viszonyít; hiányzó előzmény vagy ár esetén — jelenik meg. Hiányos árazásnál a vagyonarány nem számítható pontosan.
- Meglévő adatok átvitele: bezárt program mellett másold át az 1.2 mappájából a vagyon.sqlite3 fájlt az új mappába, az első indítás előtt.

## 1.2.2 – Hibajavítás
A Tárgyak és bankszéf fülön állítsd be a feltételeket, majd kattints a **Szűrés alkalmazása** gombra. A találati táblázat a panel alatt jelenik meg, rendezhető oszlopokkal. A találatok száma, ismert összértéke és a hiányzó árak száma a táblázat felett látható. A Szűrők törlése visszaállítja a teljes listát. A főablak jobb alsó sarkában minden fülről elérhető a piros Bezárás gomb.


## 1.2.2 – Rendezési javítás
Minden táblázat nyers numerikus adatok szerint rendez; magyar területi beállítású szövegrendezés, hiányzó értékek mindig a végén. Az oszlop és irány szűrés után megmarad.
