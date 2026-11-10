@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo Indicizzazione delle voci esistenti Zotero, nessuna scrittura sulla libreria Zotero.
echo.
py autocite_catalog.py sync
pause
