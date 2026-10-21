@echo off
rem ===========================================================================
rem  F13-Demo starten – per Doppelklick oder in PowerShell:  .\start.cmd
rem  Erkennt einen Firmen-Proxy (HTTPS-Prüfung), startet alle Container, prüft sie,
rem  wärmt die Modelle vor und öffnet den Browser.
rem  Beim ersten Mal braucht es Internet (Images, Frontend-Build, Modelle, ca. 15 Min.).
rem  Danach funktioniert der Start auch offline.
rem ===========================================================================
chcp 65001 >nul
setlocal
cd /d "%~dp0"
rem Fortschritt als einfache Zeilen. Die animierte Anzeige stapelt in der Konsole
rem neue Zeilen, sobald eine Meldung breiter als das Fenster ist.
set "COMPOSE_PROGRESS=plain"
rem Frontend-Port aus .env lesen (Standard 9999).
set "FRONTEND_PORT=9999"
for /f "tokens=1,* delims==" %%a in ('findstr /b "FRONTEND_PORT=" .env') do set "FRONTEND_PORT=%%b"

echo.
echo [1/6] Prüfe, ob Rancher Desktop läuft ...
docker version >nul 2>&1
if errorlevel 1 (
  echo.
  echo FEHLER: Docker antwortet nicht. Bitte Rancher Desktop starten,
  echo warten bis es "Running" meldet, und dann start.cmd erneut ausführen.
  goto :fehler
)

echo.
echo [2/6] Prüfe, ob ein Firmen-Proxy HTTPS neu signiert ...
echo       (Siehe config\zertifikate\README.md)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0werkzeuge\firmenzertifikat.ps1"
if errorlevel 1 (
  echo.
  echo WARNUNG: Firmenzertifikat nicht eingerichtet. Downloads aus den Containern
  echo          ^(z. B. Parser-Modelle^) können scheitern. Siehe config\zertifikate\README.md
)

echo.
echo [3/6] Starte alle Container und warte, bis sie bereit sind ...
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
echo [4/6] Lade die Wissensdatenbank „Pokémon-Regeln“ ...
echo       (Nur beim ersten Mal oder wenn sich die Dokumente geändert haben.)
docker compose run --rm wissensbasis
if errorlevel 1 (
  echo.
  echo WARNUNG: Wissensdatenbank nicht geladen. Die Recherche mit hochgeladenen Dateien
  echo          funktioniert trotzdem. Details:  docker compose logs rag
)

echo.
echo [5/6] Prüfe alle Dienste ...
docker compose run --rm pruefen
if errorlevel 1 (
  echo.
  echo WARNUNG: Mindestens eine Prüfung ist fehlgeschlagen ^(siehe oben^).
)

echo.
echo [6/6] Wärme die Modelle vor ^(erste Antwort wird sonst langsam^) ...
docker compose run --rm warmup

echo.
echo Fertig. Die Demo läuft unter http://localhost:%FRONTEND_PORT%
start "" http://localhost:%FRONTEND_PORT%
echo Zum Beenden: stopp.cmd
echo.
pause
exit /b 0

:fehler
echo.
pause
exit /b 1
