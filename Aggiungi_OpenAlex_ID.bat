@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Aggiunta per ID OpenAlex W..., senza ancora modificare Zotero.
py autocite_catalog.py add-openalex
pause
