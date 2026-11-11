# DRAFT ONLY — NOT A PULL REQUEST

Proposed discussion title: Add safe conversion of structured citation placeholders in open Word documents

## Problem

Researchers currently using a short citation-code workflow must convert each placeholder to a live Zotero citation through separate steps or manually add references individually. AutoCite has demonstrated a copy-based workflow in Word, but cannot operate natively in the currently open document.

## Proposed small-scope change

Introduce a read-only syntax scanner and source resolver, feeding a native Zotero integration operation to turn explicitly identified placeholders into editable citation fields. All fields and bibliography updates should be managed by Zotero's existing integration session. The first upstream contribution would not require OpenAlex, Crossref, Python or the AutoCite SQLite alias database.

## Motivation

Used for a daily academic writing workflow in a university department. The goal is reduced repetitive manual insertion and improved auditability, not replacing Zotero's existing citation system.

## References

- Our experimental code: https://github.com/Animenio/zotero-autocite
- Existing Zotero note-link field conversion: `Zotero.Integration.Session._insertNoteIntoDocument` / `Document.convertPlaceholdersToFields`
- Zotero Windows Word bridge: https://github.com/zotero/zotero-word-for-windows-integration

## Test evidence

Offline tests in `upstream-prep/`; live Word integration is NOT YET IMPLEMENTED in this branch. A PR should only be opened after native Word integration, rollback and compatibility tests pass, and after maintainers confirm the desired architecture.

## Open questions for maintainers

1. Prefer a command inside `zotero/zotero` or a separate word processor integration/plugin?
2. Extend `convertPlaceholdersToFields` to accept a safe plaintext span map or add a dedicated Word-native adapter?
3. Is a Windows-first experimental implementation acceptable, or is cross-platform parity mandatory?
4. Should portable Zotero keys be the only accepted marker in core, with custom aliases owned by independent plugins?

**Do not submit this draft as a PR until test coverage and maintainer guidance are available.**
