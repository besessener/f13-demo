@echo off
rem ===========================================================================
rem  F13-Demo starten – per Doppelklick oder in PowerShell:  .\start.cmd
rem  Startet alle Container, prüft sie, wärmt die Modelle vor und öffnet den Browser.
rem  Beim ersten Mal braucht es Internet (Images, Frontend-Build, Modelle, ca. 15 Min.).
rem  Danach funktioniert der Start auch offline.
rem ===========================================================================
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo.
echo [1/4] Prüfe, ob Rancher Desktop läuft ...
docker version >nul 2>&1
if errorlevel 1 (
  echo.
  echo FEHLER: Docker antwortet nicht. Bitte Rancher Desktop starten,
  echo warten bis es "Running" meldet, und dann start.cmd erneut ausführen.
  goto :fehler
)

echo.
echo [2/4] Starte alle Container und warte, bis sie bereit sind ...
echo       (Beim ersten Mal: Frontend bauen + Modelle laden, das dauert.)
docker compose up -d --wait --wait-timeout 1800
if errorlevel 1 (
  echo.
  echo FEHLER: Nicht alle Container sind bereit. Übersicht:
  docker compose ps -a
  echo.
  echo Details zu einem Dienst:  docker compose logs ^<dienst^>
  goto :fehler
)

echo.
echo [3/4] Prüfe alle Dienste ...
docker compose run --rm pruefen
if errorlevel 1 (
  echo.
  echo WARNUNG: Mindestens eine Prüfung ist fehlgeschlagen ^(siehe oben^).
)

echo.
echo [4/4] Wärme die Modelle vor ^(erste Antwort wird sonst langsam^) ...
docker compose run --rm warmup

echo.
echo Fertig. Die Demo läuft unter http://localhost:9999
start "" http://localhost:9999
echo Zum Beenden: stopp.cmd
echo.
pause
exit /b 0

:fehler
echo.
pause
exit /b 1
