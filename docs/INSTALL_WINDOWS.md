# Windows installation and first test

**Beta only.** Use a separate Zotero test collection and a disposable Word document.

## Prerequisites

- Windows 10/11
- Python 3.10+ from python.org (with `py` launcher), including Tkinter
- Zotero Desktop 10+ with the Microsoft Word plugin installed
- Microsoft Word desktop for Windows
- Internet access for external discovery (not required to resolve already registered local sources)

Open Zotero → Settings → Advanced → enable **Allow other applications on this computer to communicate with Zotero**. Keep Zotero running. For writes, Zotero separately requests an authorization; review it before allowing.

## Install

Download/extract the entire source folder, not a single `.pyw` file. In the extracted folder, open Command Prompt and run:

```powershell
py --version
py -m pip install -r requirements.txt
py -m tkinter
pyw AutoCite_Desktop.pyw
```

If Windows asks how to open `.pyw`, choose **Python (default windowed)**. Alternatively launch the app with `pyw AutoCite_Desktop.pyw` from the extracted folder. This is a Python application, **not** a signed installer or standalone EXE.

## Configure a safe test

1. In Zotero's personal library, create a collection named `AutoCite TEST`.
2. Open AutoCite → **Zotero and collections** → refresh collections → select and save the test collection.
3. Go to **Search article** and paste a DOI that you have verified, e.g. `10.1016/j.techfore.2016.08.019`. Review title, author, date and DOI before registering.
4. Copy the returned local code. The particular numeric suffix will differ across catalogs.
5. In Word, make a short `.docx` with a sentence containing that marker and a separate paragraph containing `[[ZBIB]]`.
6. Save and close Word. Go to **Convert Word**, choose the original file and start conversion.
7. When importing missing items, grant Zotero local-write permission only if you trust this AutoCite source and chose the destination collection.
8. Open the generated `_Zoterizzato.docx` → **Zotero → Refresh**. Open **Add/Edit Citation** on a converted reference to check the live link. Verify that the bibliography has one item per unique cited publication.
9. Inspect `_LOG.csv` and `_riepilogo.json` and verify the Zotero collection did not acquire duplicates.

The original Word file remains unchanged. Use it, not a previously converted file, when repeating the test.

## Catalog and settings

The local catalog is stored under `%APPDATA%\ZoteroAutoCite\catalogo.sqlite3`; Zotero target selection is recorded in `settings.json` in the same folder. **Back up this folder before changing computers**. Never publish its contents; it may include your private reference collection and machine-specific identifiers.

For manual troubleshooting, execute `py zotero_autocite.py "C:\\path\\paper.docx"` and consult the CSV/JSON report.
