@echo off
setlocal
cd /d "%~dp0"
if not exist "adatok\tf_analyzer.sqlite3" (
 echo Meg nincs adatbazis ebben a mappaban.
 pause
 exit /b 1
)
if not exist "mentesek" mkdir "mentesek"
for /f %%T in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "STAMP=%%T"
copy /Y "adatok\tf_analyzer.sqlite3" "mentesek\tf_analyzer_%STAMP%.sqlite3"
echo Kesz. Biztonsagi mentes elmentve.
pause
