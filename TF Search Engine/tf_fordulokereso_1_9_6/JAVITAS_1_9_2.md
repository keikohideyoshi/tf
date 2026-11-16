# 1.9.2 – Tárgynevek ragozása

A tárgyesemény-keresés most felismeri a `skorpiókarom` (#911) ragozott alakjait (`skorpiókarmot`, `skorpiókarmok`, `skorpiókarmokat`). A 2081-es karakter 328. fordulójában a `szereztél 1 skorpiókarmot` loot szöveg öt alkalommal fordul elő.

A meglévő eseményfeltételek és az adatbázis szerkezete változatlan; nincs szükség újraindexelésre, mert a javítás a lekérdezés során működik. A korábbi tárgykereső többi működése változatlan.
