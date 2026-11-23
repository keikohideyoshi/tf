# TF Fordulókereső 1.9.7.10 – Linux

Az 1.9.7.9-es Linux-verzióra épül.

- Az **AI beállítások** ablak új **Ollama indítása** gombot kapott.
- Az ablak ellenőrzi a helyi Ollama API-t (`127.0.0.1:11434`). Ha már fut, az indítógomb inaktív.
- Ha nem fut, az `ollama serve` parancsot külön, a GUI-t nem blokkoló háttérfolyamatban indítja el, és ellenőrzi a szolgáltatás elérhetőségét.
- Hiányzó Ollama vagy sikertelen indítás esetén érthető visszajelzést ad. Nem kér rendszergazdai jogosultságot.
- Az Ollama-folyamat a Fordulókereső bezárása után is futhat; a program nem állítja le automatikusan.
- A gomb a helyi gépen telepített Ollamát indítja; nem telepíti újra és nem tölti le automatikusan a modellt.
- A programablak verziófelirata frissült.

Ellenőrzés: 61 automatikus Python-teszt sikeres. A tényleges GUI-indítást és Ollama-kapcsolatot a felhasználó Linux-gépén szükséges kipróbálni.
