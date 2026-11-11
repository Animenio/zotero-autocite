# DRAFT ONLY — NOT A PULL REQUEST

Proposed discussion title: Add safe conversion of structured citation placeholders in open Word documents

## Problem

Researchers currently using a short citation-code workflow must convert each placeholder to a live Zotero citation through separate steps or manually add references individually. AutoCite has demonstrated both a copy-based workflow and a separate Python COM proof of concept that converts markers in the currently open Word document. The latter was manually validated with Zotero Refresh and Add/Edit Citation; it is not integrated into Zotero's official Word plugin.

## Proposed small-scope change

Introduce a read-only syntax scanner and source resolver, feeding a native Zotero integration operation to turn explicitly identified placeholders into editable citation fields. All fields and bibliography updates should be managed by Zotero's existing integration session. The first upstream contribution would not require OpenAlex, Crossref, Python or the AutoCite SQLite alias database.

## Motivation

Used for a daily academic writing workflow in a university department. The goal is reduced repetitive manual insertion and improved auditability, not replacing Zotero's existing citation system.

## References

- Our experimental code: https://github.com/Animenio/zotero-autocite
- Existing Zotero note-link field conversion: `Zotero.Integration.Session._insertNoteIntoDocument` / `Document.convertPlaceholdersToFields`
- Zotero Windows Word bridge: https://github.com/zotero/zotero-word-for-windows-integration

## Test evidence

The preparation branch now contains a Zotero-API scoped resolver, a native citation batch planner,
a Word story safety preflight, a Session registration prototype, a transaction coordinator,
and a separately compilable C++17 UTF-16 marker validator.

Evidence to date:
- Independent AutoCite Word Live FieldFix proof of concept was validated by the tester with
  Microsoft Word Desktop, Zotero Refresh and Add/Edit Citation.
- An independent local run passed 66/66 Python tests.
- 31 original Node tests plus 16 additional local bridge smoke cases passed; the full
  expanded test suite on GitHub still requires confirmation.
- The portable C++17 range validator compiled with GCC using `-Wall -Wextra -Werror
  -Wconversion -Wsign-conversion -DNDEBUG`, and its runtime assertions passed.

**Still missing:** an actual Zotero client command, C++ OLE Automation scanner/inserter,
JS/ctypes exports, Word ribbon localization and multi-architecture Visual Studio builds.
The existing tests DO NOT certify this as a working Zotero extension.
A PR should only be opened after real upstream integration tests, rollback and
compatibility checks pass, and after maintainers confirm the intended architecture.

## Open questions for maintainers

1. Prefer a command inside `zotero/zotero` or a separate word processor integration/plugin?
2. Extend `convertPlaceholdersToFields` to accept a safe plaintext span map or add a dedicated Word-native adapter?
3. Is a Windows-first experimental implementation acceptable, or is cross-platform parity mandatory?
4. Should portable Zotero keys be the only accepted marker in core, with custom aliases owned by independent plugins?

**Do not submit this draft as a PR until test coverage and maintainer guidance are available.**
