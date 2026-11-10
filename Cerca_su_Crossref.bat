@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Ricerca alternativa Crossref (gratuita).
py autocite_catalog.py search-crossref
pause
