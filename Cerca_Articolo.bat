@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Ricerca per DOI esatto (consigliata) o titolo/autore. OpenAlex e Crossref.
py autocite_catalog.py search
echo.
pause
