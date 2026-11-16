# TF Fordulókereső 1.9.1 – hibajavítás

## Javítás

A TF harci beszámolókban a halál/menekülés jelzése és a győzelmi TP gyakran a `<p class=csata>...</p>` lezárása UTÁN található. A korábbi feldolgozó csak a csatabekezdésben keresett, így a halálos csatákat nem találta meg. Az 1.9.1 a közvetlenül következő eredményszöveget is a csatához rendeli, de megáll a következő parancsnál/csatánál.

Az eseményindex verziója 2-re, a teljes index verziója 4-re változott, így a régi hibásan gyorsítótárazott eredmények nem használhatók fel. Az új indexhez a programban futtasd le a fordulók újraindexelését. A kereső az újraindexelés előtt is képes a régi eseményindex helyett az eredeti HTML-t feldolgozni, de lassabb lehet.

A tárgykereső forráskódja nem változott.

## Ellenőrzés

A 2081-es karakter 289. fordulójában a program 27 csatát, köztük 2 vámpír őrszem elleni halálesetet ismer fel. Mindkét természetes nyelvű kérdés (`Mikor ölt meg vámpír őrszem?`, `Mikor ölt meg valamilyen szörny?`) 2 eseményt ad vissza ebben a fordulóban. Az automatikus tesztek sikeresek.

## Telepítés

Csomagold ki az új verziót. Ha a régi adatbázist szeretnéd megtartani, a korábbi `data/tudasbazis.sqlite3` fájlt másold át az új `data` mappába, majd indítsd `./start.sh` paranccsal. A régi programot előtte zárd be. Az eredeti HTML-fájlok elérhetők kell maradjanak az adatbázisban tárolt útvonalakon.
