# TF Fordulókereső 1.9.7.3 – célzott tárgykeresési gyorsítás

A 1.9.7.2 diagnosztikában 3 836 317 szövegblokk feldolgozása során az `item_event_recognition` 222,62 másodpercet igényelt.

- A tárgyesemény-felismerés először a szükséges cselekvési igét vagy zsákmánybevezető kifejezést keresi.
- Azokat a blokkokat, amelyekben ilyen nincs, a program nem normalizálja és nem bontja mondatokra.
- Csak a cselekvést tartalmazó szövegrészekben történik Unicode-normalizálás és tárgynév-azonosítás.
- Az eredeti tárgyazonosító-, tagadás-, távolság-, és Enc-link felismerési szabályok változatlanok.
- A diagnosztika két új számlálót mutat: `blocks_skipped_no_action`, `blocks_with_action`.
- Nincs adatbázis-migráció vagy újraimportálás.

A sebességnyereséget a teljes felhasználói adatbázison még mérni kell; a korábbi 47 találat / 43 forduló eredményt ellenőrizni kell.
