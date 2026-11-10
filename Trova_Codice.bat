@echo off
chcp 65001 >nul
cd /d "%~dp0"
set /p Q=Cerca un articolo nel catalogo (parte del titolo/DOI):
py autocite_catalog.py list "%Q%" --limit 40
pause
