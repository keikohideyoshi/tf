# TF Fordulókereső 1.9.3

- Az eredeti TF HTML `JavaScript:Enc(0,N,...)` hivatkozása a `N+1` sorszámú tárgyat, az `Enc(1,N,...)` a `N+10` sorszámú szörnyet azonosítja. A kereső a forrás HTML-ben azonosító alapján is keres; ahol van ilyen találat, nem duplázza meg a név szerinti találatokat. Az azonosítók az ismert mintafordulókban ellenőrzöttek.
- A tárgy megszerzéséhez/használatához továbbra is eseményre utaló, közvetlen szövegkörnyezet szükséges; a puszta Enc-hivatkozás nem bizonyít megszerzést.
- A szabad szavas kérdéshez **külön**, opcionális tárgy- vagy szörnyválasztó került. Az enciklopédiai név részlete vagy `#szám` alapján gépelés közben frissülő listából lehet választani. A választás felülírja a kérdésből felismert objektumot, de megtartja a felismert eseménytípust.
- A `Garmhuun familiárissal` alakot már a helyi szabályalapú értelmező is felismeri.
- A felső mező elé bekerült a `Kulcsszavas keresés:` felirat.
- A meglévő adatbázis tovább használható, **újraindexelés nem szükséges** az Enc-hivatkozásokhoz, mivel a program az eredeti HTML-t olvassa. Az eredeti forrásfájloknak elérhetőnek kell maradniuk.
- A tárgyesemények értelmezése konzervatív: nem minden TF-fogalmazás ismerhető fel automatikusan. Az Enc-link nélküli esetekben a korábbi szöveges keresés marad.
