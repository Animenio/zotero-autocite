# Native Word ↔ Zotero Session integration: implementation contract

**Status:** experimental design backed by pure-JavaScript tests, **not** yet a compiled Windows Word plugin.
**Date:** 2026-11-11
**Licensing:** new proposal modules AGPL-3.0-or-later; original Word VBA macro in the upstream repo has GPLv3-or-later license.

## Confirmed upstream call graph

- Word ribbon VBA macro -> \`ZoteroCommand(...)\` -> \`Zotero.Integration.execCommand()\`
- \`Zotero.Integration.execCommand()\` loads the active Word document and \`Session\`, then calls the matching \`Zotero.Integration.Interface\` method.
- \`Session.getFields(true)\` reads the Word plugin's native field list, including preexisting citations.
- \`Zotero.Integration.CitationField\`, \`Zotero.Integration.Citation\`, \`Session.addCitation()\`, and \`Session.updateDocument()\` own citation and bibliography updates. New citation inputs are of the form \`citationItems: [{id: zoteroItem.id}]\`, not raw Word CSL JSON.
- \`zoteroWinWordIntegration.mjs\` calls C++ via js-ctypes.
- The Windows \`document.cpp\` starts a Word \`UndoRecord\` when the document is acquired, and closes it from \`complete()\`. **The new feature must reuse that record rather than nesting a second Word undo record.**
- The C++ \`insertFieldRaw()\` already uses \`CFields.Add(... wdFieldQuote ...)\` to create an actual Word field. This prevents the incomplete-field bug encountered in the first Python COM prototype.

Sources:
- https://github.com/zotero/zotero/blob/main/chrome/content/zotero/xpcom/integration.js
- https://github.com/zotero/zotero/blob/main/test/tests/integrationTest.js
- https://github.com/zotero/zotero-word-for-windows-integration/blob/main/components/zoteroWinWordIntegration.mjs
- https://github.com/zotero/zotero-word-for-windows-integration/blob/main/build/zoteroWinWordIntegration/document.cpp
- https://github.com/zotero/zotero-word-for-windows-integration/blob/main/build/zoteroWinWordIntegration/zoteroWinWordIntegration.h
- https://github.com/zotero/zotero-word-for-windows-integration/blob/main/build/template/Zotero.dotm/word/vbaProject.bin/Zotero.bas

## Staged JavaScript components in this preparation branch

| File | Purpose | Mutates Word? |
| --- | --- | --- |
| \`src/placeholderParser.mjs\` | Parse supported markers and UTF-16 offsets | No |
| \`src/zoteroNativeLookup.mjs\` | Resolve explicit Zotero library and item key against real APIs | No |
| \`src/resolutionPlanner.mjs\` | Reject ambiguous/missing markers; deduplicate lookups | No |
| \`src/nativeCitationBatch.mjs\` | Construct \`citationItems:[{id}]\` with validated numeric Zotero IDs | No |
| \`src/wordStoryPreflight.mjs\` | Check main-story metadata, marker offsets, field overlap and safety | No |
| \`src/sessionCitationRegistration.mjs\` | Experimental calls to official Session/Citation classes; requires preinserted fields | Yes, indirectly through Session |
| \`src/wordSessionCoordinator.mjs\` | Coordinate Word snapshot, backup, temp fields, Session, and rollback | Yes, through a future adapter |

The last two modules are **integration sketches**, not validated with the real Zotero client.

## Coordinate system: JS versus native C++

- The JavaScript `wordStoryPreflight.mjs` snapshot reports `fieldRanges`
  **relative** to `snapshot.text`; its `storyStart` shifts approved
  replacements into Word's absolute coordinate system.
- The native `MarkerRangeValidator` accepts all ranges in **absolute**
  Word story coordinates and compares to a UTF-16 story snapshot.
- Therefore, any JS/ctypes adapter MUST convert existing-field ranges
  into story-relative offsets before JavaScript preflight, but use absolute
  coordinates for the final C++ validator and the Word COM Range.
- The native adapter MUST check `Range.Text` again before each insertion;
  the initial snapshot alone is not a complete safety guarantee.
- Word C++ `getDocument()` already opens a custom UndoRecord; adapter
  `beginUndoTransaction()` means **adopt/reuse** it rather than nesting a second.

## Required Windows-native adapter contract (not yet implemented)

The new Word plugin bridge should expose operations matching:

1. \`readMainStorySnapshot()\` — return Word's main-text story text, story-start offset, existing Word field spans, read-only/saved/revision state. **Text offsets in JS are UTF-16 code units; the native layer must confirm that each marker corresponds to exactly the expected Word range text.**
2. \`verifyStorySnapshot(snapshot)\` — re-read the same Word story and return strict equality before edits; include field spans, not only the text.
3. \`createVerifiedBackup()\` — persist a separate document copy with no source overwrite, validate it as a usable DOCX and verify content. Do not use \`SaveCopyAs\` if unsupported; do not copy a stale unsaved source.
4. \`beginUndoTransaction()\` — **adopt the existing Word UndoRecord** started by Zotero's C++ \`getDocument()\`, rather than calling \`StartCustomRecord()\` twice.
5. \`replaceRangeWithTemporaryField({start,end,expectedText})\` — ensure the Word range still contains precisely that plaintext marker; replace it with a native Word citation field created via \`insertFieldRaw()\`, with temporary code, and return its native field handle.
6. \`commitUndoTransaction()\` — close/complete Zotero's existing undo record; return true only if confirmed.
7. \`rollbackUndoTransaction()\` — attempt full undo of inserted fields on error and return an honest success/failure result. Word undo is **not an atomic transaction**; the verified backup remains the recovery source.

**Do not repurpose** \`convertPlaceholdersToFields()\` for plaintext markers. In the upstream source it specifically converts Zotero note hyperlinks to fields, and it is not a general plaintext range scanner.

## Zotero Core command sketch (not yet patched)

The eventual \`Zotero.Integration.Interface.prototype.convertCitationPlaceholders\` should:

1. Initialize the Zotero document Session with valid style and field type.
2. Ask the native Word adapter for the main-story snapshot.
3. Use the read-only Zotero resolver and run the full-document preflight. If even one marker is unresolved or unsafe, abort the batch; no partial conversion by default.
4. Display **localized** preview and ask for explicit user confirmation.
5. Create a verified backup.
6. Replace markers **in reverse range order** with temporary fields through the native Word layer.
7. Re-fetch fields with \`Session.getFields(true)\`; identify each inserted field with \`Field.equals()\`; reject missing/ambiguous identity.
8. Build \`new Zotero.Integration.CitationField(nativeField)\` and \`new Zotero.Integration.Citation(citationField,{citationItems:[{id:item.id}],properties:{}},noteIndex)\`, register via \`Session.addCitation(...)\`, and call \`Session.updateDocument(...)\`.
9. Commit Word changes and save the updated Zotero Session data through the existing \`execCommand\` lifecycle. Do not manually manufacture CSL field strings.
10. On any failure, roll back the Word edit if possible, discard/reinitialize the modified Session state and provide the backup path for recovery.

**Open architecture question:** whether Session registration of freshly inserted temporary fields can be performed safely using \`updateFromDocument(false)\` or requires a dedicated Session method. This MUST be answered using Zotero's real \`integrationTest.js\` and live Word, not by mock success alone.

## Required native validation before PR

- Visual Studio 2022 + Office; build for Win32, x64 and ARM64 as specified upstream.
- Windows Word Live: user library, group library, missing, malformed and duplicate item keys; preserved existing citations; multiple markers in one paragraph and tables.
- Binary-compare unrelated existing fields; ensure all new fields contain begin/separate/end and editable Zotero citation data.
- Verify Zotero Refresh + Add/Edit Citation after insertion.
- Word unsaved document, Track Changes, password-protected document, stale text and failed backup must fail safely.
- Failure injection: fail before first field, after first field and during Session formatting. Verify both Undo and backup recovery.
- Test notes, text boxes and headings remain out-of-scope until supported by the native adapter.
- Official Zotero test suite, not just Node tests; locally compile VBA via Debug → Compile Project and use the repository's unpack-template hooks.
- User-visible messaging must be localized, not embedded English.

## Current blocker

The feature is not present in Zotero's C++ library, JS/ctypes wrapper or Word template. The native interfaces above and their strict COM behavior still require implementation and Windows compilation. The testable modules in this branch are an engineering scaffold, not a deployable Zotero plugin.
