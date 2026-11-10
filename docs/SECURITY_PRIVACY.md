# Security, privacy, and data handling

## Local data

- The manuscript is processed locally with Python and `python-docx`; its full text is **not intentionally transmitted** to OpenAlex, Crossref, or another hosted service.
- DOI, search terms, and OpenAlex identifiers are sent to external APIs during discovery/verification. These third parties apply their own service policies.
- The SQLite alias registry, Word files, Zotero server ID, selected collection, and logs remain local unless the user explicitly shares or syncs them elsewhere.
- The Zotero local API should only be accessible from the user's computer. Do not bind or forward port `23119` onto the Internet.

## Write operations

- Zotero data reads use the local API. Zotero 10+ write operations require the user to allow a local API authorization dialog.
- Creating a missing item and attaching an existing item to a chosen collection are **write operations**. They may be synced by Zotero to the user's account according to Zotero settings.
- The app avoids direct modification of `zotero.sqlite`.
- A local API key granted for writing can have broad write scope; review the app before approving and use a test collection first.

## Macro risks

`ZoteroAutoCite_Word_05.bas` launches a local Python process with the active document path. It is optional and must be imported by the user. Do not globally disable Office macro security to run it; review the source first.

## Do not commit

- `%APPDATA%\ZoteroAutoCite\catalogo.sqlite3`, its backups, or `settings.json`
- API keys / environment values
- Unredacted manuscript files, personal bibliographies, or log CSV/JSON with private content
- Private Zotero group data or institution-owned datasets

The `.gitignore` excludes common generated files, but review all files before publishing.

## Limitations of this assessment

The repository preparation included a static scan for common secrets and local-path indicators, not a professional security review. No code signing, sandboxing, or external penetration testing has been performed.