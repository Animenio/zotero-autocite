@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo Zotero AutoCite: scegli la raccolta Zotero destinataria degli articoli nuovi.
echo Apri Zotero Desktop e abilita la comunicazione locale.
echo.
py autocite_catalog.py choose-collection
pause
