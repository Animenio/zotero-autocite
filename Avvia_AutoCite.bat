@echo off
chcp 65001 >nul
cd /d "%~dp0"
if "%~1"=="" (
    echo Trascina un documento Word .docx su questo file .bat.
    echo Oppure esegui py zotero_autocite.py "C:\percorso\paper.docx" --auto-import
    pause
    exit /b 1
)
py "%~dp0zotero_autocite.py" "%~1" --auto-import
if errorlevel 1 (
    echo.
    echo Controlla il messaggio di errore e il README.md
)
echo.
pause
