# TF Fordulókereső 1.9.7.7

- A varázslatokat a mellékelt `Varázslatok összefoglaló.html` enciklopédia **ötödik, hatás** oszlopa szerint választjuk szét.
- `támadó` és `védekező`: kizárólag harci szöveges keresés.
- Minden más hatás: kizárólag a pontos, már meglévő V/VV varázslatazonosító-index használata.
- A nem harci keresés **nem** vizsgálja a harci szövegeket, nem futtat harci FTS-előszűrést, és indexelt fordulóknál nem olvassa a HTML-t.
- Az ismeretlen enciklopédia-azonosító nem vezet találathoz; nem tippelünk kategóriát.
- A sikeres és sikertelen V/VV kísérletek között továbbra sincs különbség, az ismételt varázslatok külön események.
- 47 automatikus teszt, köztük besorolás és harci/HTML-olvasás tiltásának tesztje.

**Megjegyzés:** Az első kereséskor a régi importok parancsindexének egyszeri feltöltése időbe telhet. A teljes felhasználói adatbázison végzett időmérés még szükséges.
