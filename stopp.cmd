@echo off
rem ===========================================================================
rem  F13-Demo beenden – per Doppelklick oder in PowerShell:  .\stopp.cmd
rem  Stoppt alle Container. Modelle und Daten bleiben erhalten (kein "-v").
rem ===========================================================================
chcp 65001 >nul
cd /d "%~dp0"
docker compose down
echo.
echo Gestoppt. Modelle und Daten bleiben erhalten. Neu starten mit start.cmd
echo.
pause
