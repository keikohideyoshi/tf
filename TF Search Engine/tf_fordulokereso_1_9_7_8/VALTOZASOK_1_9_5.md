# TF Fordulókereső 1.9.5

- Opcionális helyi Ollama AI a szabad kérdések értelmezéséhez. A kérdés helyben marad.
- AI funkciók gomb: állapotellenőrzés, Ollama telepítésének kezdeményezése, modellletöltés, modellválasztás.
- Automatikus AI-értelmezés, ha a kiválasztott modell fut; hiba esetén szabályalapú tartalék.
- Új harci halálfelismerés: a csata után közvetlenül következő `valt1neg` SPAN halálként azonosítandó.
- A meglévő keresés és adatbázis változatlanul használható AI nélkül is.

## Fontos

Linuxon az Ollama rendszercsomag telepítése jóváhagyást igényel. A telepítés után a szolgáltatást el kell indítani (például `sudo systemctl enable --now ollama`), majd a modellt le kell tölteni. Windows alatt a program a hivatalos letöltőoldalt nyitja meg; nem futtat automatikusan ismeretlen telepítőt.
A helyi AI a kérdést értelmezi, nem szemantikus kereső és nem önálló válaszgenerátor. Egyes összetett lekérdezések a jelenlegi keresőmotor korlátai miatt még nem támogatottak.

A korábban importált fordulókhoz az új halálfelismerés az eseményindex verzióváltása miatt az eredeti HTML-ből olvasva is működik; a gyorsabb működés érdekében ajánlott a Fordulók újraindexelése.
