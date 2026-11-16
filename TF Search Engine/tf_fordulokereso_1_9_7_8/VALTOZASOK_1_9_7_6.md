# TF Fordulókereső 1.9.7.6

## V/VV varázslatkeresés gyorsítása

- Új, SQLite-indexelt `tf_spell_cast` tábla: varázslat-ID, forduló, parancssorrend, pozíció és megjelenítendő részlet.
- A korábban importált fordulók parancsai a meglévő tömörített `tf_event_index` gyorsítótárból egyszer kerülnek át az új indexbe, nem szükséges újraimportálni őket.
- Az újonnan importált fordulókhoz az index automatikusan létrejön mindkét importálási útvonalon.
- A V/VV keresés ismételt futtatásakor nincs fordulónkénti parancskicsomagolás.
- Az azonos varázslat ismételt kiadása több eseményt jelent, sikertől függetlenül.
- A harci varázslások eddigi felismerési szabályait nem módosítottuk, így a gyorsulás nagysága az adatbázisban lévő harci eseményektől függ.
- A keresési napló varázslatkeresésre továbbra sem tartalmaz szakaszonkénti időmérést; a teljes futásidőt rögzíti.

## Ellenőrzés

44 automatikus teszt sikeres, köztük három új index/regressziós teszt.
A felhasználó teljes adatbázisán nem történt teljesítménymérés; a korábbi 22 esemény / 19 forduló eredményét azon kell ellenőrizni.
