@echo off
chcp 65001 >nul
cd /d "%~dp0"
py autocite_catalog.py export-csv
pause
