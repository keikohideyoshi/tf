# TF Fordulókereső 1.9.7.9 – Linux

A felhasználó által feltöltött 1.9.7.8 Linux-változat továbbfejlesztése.

## Újdonságok

- **Alkímiáztam** esemény az Objektumkeresés és Szabad kérdés tárgyesemény-választójában.
- Aranytermő ládikó: kizárólag a `[TÁRGYNÉV ládikóba->` szerkezet számít, a tárgy enciklopédiai nevével összevetve. A `Szerzeményed: N TÁRGYNÉV` bevezetőből a darabszám is felismerhető.
- Alkímiázó üst: csak a valódi `table.par` HTML-parancstáblák `H 341 TÁRGYAZONOSÍTÓ DARABSZÁM` parancsai számítanak; a tárgyat az azonosító alapján azonosítjuk.
- Az alkímiázási események a **Megszereztem** és **Használtam** eseményektől függetlenek. Egy ládikóba került szerzemény a szerzéskeresésben továbbra is megjelenhet.
- A szabad kérdéses kereső felismeri a „hányszor”, „hány alkalommal”, „hány darab” megfogalmazásokat. Az eseményszámot és a fordulók számát közli; alkímiázásnál a darabszámot is összegzi, ha minden eseménynél ismert.
- Az utolsó N forduló szűrése az összesítést is az adott időszakra korlátozza.

## Korlátok

- Az üst parancsának pontos ellenőrzéséhez a mentett eredeti HTML-fordulóknak a korábbi elérési úton rendelkezésre kell állniuk.
- A ládikós esemény csak akkor ismerhető fel, ha a tárgynév és a `ládikóba->` kifejezés ugyanabban az importált szövegblokkban található.
- A **hányszor** eseményeket számol, nem a tárgyak darabszámát. A darabszámot a „hány darab” kérdés kéri. A **Megszereztem** és **Használtam** eseményekből a teljes darabszám még nem számítható megbízhatóan; ilyenkor a program ezt jelzi.
- A teljes felhasználói adatbázis nem állt rendelkezésre, ezért a teljesítményt és az összes történeti HTML-változatot helyi mintatesztekkel lehetett ellenőrizni.

## Indítás és teszt

```bash
./start.sh
python -m unittest discover -s tests -q
```

A tesztkészlet 57 tesztet tartalmaz (50 korábbi és 7 új).
