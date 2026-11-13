# TF – Utasítás lap konvertáló 1.1

Linuxos grafikus alkalmazás `.ods` és `.xlsx` utasításlapok feldolgozására.

## Telepítés EndeavourOS / Arch Linux alatt

Terminálban:

```bash
sudo pacman -S python python-openpyxl python-odfpy tk
```

Indítás a kibontott mappában:

```bash
./inditas.sh
```

Ha a disztribúciód nem tartalmaz `python-odfpy` csomagot, telepítheted külön virtuális környezetbe is:

```bash
sudo pacman -S python python-openpyxl tk
python -m venv --system-site-packages .venv
.venv/bin/pip install odfpy
.venv/bin/python konvertalo.py
```

## Használat

1. Add meg a négyjegyű karakterszámot, a számlaszámot (kezdő nullával), a fordulószámot és a küldő jelszót.
2. Válassz ODS vagy XLSX fájlt.
3. Kattints a **Konvertálás** gombra.
4. Ellenőrizd a két külön fülön a kimenetet, majd mentsd el külön-külön vagy együtt `.txt` formátumban.

A program nem tárolja a jelszót. A kimeneti TXT-fájlok **tartalmazzák** a jelszót, ezért kezeld őket bizalmasan.

## Feldolgozási szabályok

- BUL: A oszlop parancsai, B–D oszlop paraméterei.
- Normál UL: automatikus keresés a 40 soros, három paraméteroszlopot összegző `SUM`/`SZUM` képlet hivatkozásai alapján. A képlet a parancsoszloptól jobbra található három oszlopra mutasson.
- Mindkét UL maximum 40 parancsot tartalmazhat; a hiányzó paraméterek értéke 0.
- Az üres parancssorok kimaradnak; a kimeneti parancsok újra sorszámozódnak.
- `ELLSZ`: kizárólag az 1000-nél kisebb numerikus paraméterek összege.
- A BUL fejlécében `BEALL=OFF` szerepel, a normál UL-ben nem.
- Minden parancs önálló sorba kerül; a fejléc és a lábléc is külön sor.
- A táblázat formázását és a normál UL-től jobbra található adatokat figyelmen kívül hagyja.

A normál UL felismeréséhez a képletnek a 1–40. sor paramétertartományára kell hivatkoznia (például `SUM(K1:M40)`). Ha ettől eltérő szerkezetű fájlokat is használsz, a felismerés módosítható.

## 1.1-es változáslista

- „Utasítás Lap konvertáló” cím.
- Az alcímben „utasításlap” helyett „UL”.
- Modern, sötét grafikus téma.
- „Bezárás” gomb az ablak alján.
- A konvertálási szabályok változatlanok.
