# TF ZIP Letöltő 1.2 – stabil indítás (EndeavourOS / Arch Linux)

A korábbi 1.1 grafikus felület és letöltési/HTML-kigyűjtési logika változatlan.

## Indítás

A kicsomagolt mappában:

```bash
./start.sh
```

A `start.sh` létrehozza a `.venv` mappát, szükség esetén csak **abba** telepíti a Playwrightot, és ha kell, letölti a hozzá illő Chromiumot. A rendszer Python-csomagjait nem módosítja, nem használ `sudo pip`-et és `--break-system-packages` kapcsolót.

A rendszeroldali előfeltételek: `python`, `tk` (GUI), valamint működő grafikus munkamenet. Ha ezek hiányoznak, az indító jelzi a szükséges `pacman` parancsot. A Playwright Chromium egyes Linux-könyvtárakat is igényelhet; ha azok hiányoznak, a böngésző hibaüzenete alapján kell pótolni őket.

## Funkciók

- **ZIP-ek letöltése + HTML:** bejelentkezés a megnyíló Chromiumban, majd a GUI **Bejelentkezés kész** gombjával folytatás.
- **HTML-ek kigyűjtése:** meglévő ZIP-ek feldolgozása a GUI-ban, új letöltés nélkül.
- **Parancssoros HTML mód:** `./start.sh --html-only --karakter TF3042` – nincs szükség pipre, Playwrightra vagy böngészőre.
- **Parancssoros letöltés:** `./start.sh --cli --karakter TF3042`

Alapértelmezett mappa: `~/Letöltések/TF/TF3042`, az összegyűjtött HTML-ek: `HTML/` almappa. A meglévő ZIP-ek és HTML-ek nem törlődnek. A Beholder-böngészőprofil a `~/.local/share/tf-zip-letolto/browser-profile` helyen marad.

## Ha korábban hibás virtuális környezet keletkezett

A program mappájában a `.venv` átnevezhető (`mv .venv .venv.regi`), ezután a `./start.sh` újra létrehozza. A letöltött ZIP-ek és a böngészőprofil ettől függetlenek.

## Megjegyzés

A ZIP-letöltés a Beholder weboldalának jelenlegi `(ZIP)` linkjeire épül. Ha a weboldal változik, a letöltési logikát módosítani kellhet. A telepítéshez az első alkalommal internetkapcsolat szükséges.
