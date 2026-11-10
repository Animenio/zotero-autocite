@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo Incolla un DOI; il programma recupera i metadati Crossref nel catalogo locale.
set /p DOI=DOI:
if "%DOI%"=="" exit /b 1
py autocite_catalog.py add-doi "%DOI%"
pause
