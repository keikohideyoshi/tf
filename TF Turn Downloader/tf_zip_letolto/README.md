# TF ZIP Letöltő 1.1 – grafikus verzió

EndeavourOS/Arch Linux: `sudo pacman -S python python-pip tk`

Indítás a kicsomagolt mappában: `./start.sh`

- **ZIP-ek letöltése + HTML**: megnyílik a Chromium. Bejelentkezés után kattints a **Bejelentkezés kész** gombra. A ZIP-ek letöltése után a HTML-ek automatikusan kigyűjtésre kerülnek.
- **HTML-ek kigyűjtése**: a megadott mappában található ZIP-ekből offline, böngésző nélkül gyűjt.
- Az eredeti ZIP-ek megmaradnak; a HTML-ek a `HTML` almappába kerülnek, lapos szerkezetben, ZIP-név előtaggal.
- A Chromium munkamenetprofilja: `~/.local/share/tf-zip-letolto/browser-profile`. A jelszót a program nem kéri el és nem menti külön.
- A műveletek naplója az ablakban látható. A letöltés hibáit a program naplózza.

Korábbi terminálos használat továbbra is lehetséges: `python tf_zip_letolto.py --html-only` vagy `./start.sh --cli`.
