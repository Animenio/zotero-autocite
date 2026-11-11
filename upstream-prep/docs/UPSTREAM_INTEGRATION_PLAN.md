# Upstream integration strategy (review draft — not sent to Zotero)

Prepared 2026-11-11, based on publicly accessible upstream repositories on their `main` branches.

## 1. Which repository should own the feature?

| Existing upstream source | Verified responsibility | Proposed change |
|---|---|---|
| `zotero/zotero`, `chrome/content/zotero/xpcom/integration.js` | Citation session, field/citation update, bibliography and refresh | Add a narrowly scoped `convertCitationPlaceholders` integration command and source resolution; *only if approved* |
| `zotero/zotero`, `test/tests/integrationTest.js` | Dummy document adapter tests for the Zotero integration protocol | Add simulated integration tests that prove correct citation/bibliography state |
| `zotero/zotero-word-for-windows-integration`, `build/template/Zotero.dotm/word/vbaProject.bin/Zotero.bas` | Word UI and command forwarding via VBA | Add a dedicated "Convert Placeholders" command rather than overriding Refresh |
| `zotero/zotero-word-for-windows-integration`, `components/zoteroWinWordIntegration.mjs` | JS/ctypes wrapper of native bridge | Expose any required safe document-scanning/range operation |
| `zotero/zotero-word-for-windows-integration`, `build/zoteroWinWordIntegration/document.cpp` | OLE Automation access to open Word document, fields and stories | Locate supported plaintext ranges and perform native field replacement with tracked undo |

Upstream links:
- https://github.com/zotero/zotero/blob/main/chrome/content/zotero/xpcom/integration.js
- https://github.com/zotero/zotero/blob/main/test/tests/integrationTest.js
- https://github.com/zotero/zotero-word-for-windows-integration/blob/main/README.md
- https://github.com/zotero/zotero-word-for-windows-integration/blob/main/components/zoteroWinWordIntegration.mjs
- https://github.com/zotero/zotero-word-for-windows-integration/blob/main/build/zoteroWinWordIntegration/document.cpp
- https://github.com/zotero/zotero-word-for-windows-integration/blob/main/build/template/Zotero.dotm/word/vbaProject.bin/Zotero.bas
- https://github.com/zotero/zotero/blob/main/.gitmodules (Windows integration is a submodule)

## 2. Confirmed reusable mechanism and its limits

The core `Zotero.Integration.Session._insertNoteIntoDocument` calls `this._doc.convertPlaceholdersToFields(...)` after `insertText(...)`. Its input consists of special temporary **hyperlinks** created in the inserted Zotero note; the Windows C++ implementation enumerates those links and replaces them with fields. It does not detect arbitrary literal markers such as `[[Z:06937]]` in the body of a pre-existing document. Reuse its document-field insertion semantics, **not** a claim of drop-in plaintext support.

Existing Zotero Word flow: `Zotero.dotm` sends a `ZoteroCommand` through the Windows message mechanism → Zotero command handler/integration session → `ZoteroWinWordIntegration` JS bridge → native Word OLE Automation. Citation session/CSL handling is already in Zotero; AutoCite must not duplicate it.

## 3. Recommended architecture and scope

1. **Phase A — pure parsing and read-only resolution (this branch).** Keep syntax handling independent of Word, DOIs and local aliases in injected resolvers, and return a plan with both exact text spans and explicit errors. Default to refusing any conversion when unresolved sources remain, unless the user opts into partial conversion.
2. **Phase B — native Zotero integration command.** Zotero resolves item identity against a particular personal/group library; use Zotero's own citation/session serialization, not hand-written `ADDIN ZOTERO_ITEM CSL_CITATION` code. A native document adapter must map validated text spans to Word ranges, reject overlaps with existing Zotero fields, and insert live fields while preserving formatting.
3. **Phase C — Word UI.** Add an explicit ribbon button (not a hidden side effect of Zotero Refresh). Call Zotero's standard integration update *after* a successful transaction. Show unresolved markers in a review summary.
4. **Phase D — cross-platform review.** Decide with maintainers whether to extend the Mac and LibreOffice integrations or expose the feature as Windows-only initially. Do not imply broad support prematurely.

For first upstream review, keep **automatic OpenAlex/Crossref import** and the custom SQLite alias catalog separate from core. A core-only first PR should resolve existing Zotero records using an explicit, safely scoped identifier. Legacy aliases remain supported in AutoCite Desktop behind a catalog bridge. This avoids making Zotero depend on the Python application or an external bibliographic API.

## 4. Data-contract decisions

- Exact DOI must match the resolved record's DOI, or require manual confirmation. Absent metadata are not silently accepted.
- `[[ZOTERO:user/ITEMKEY]]` and `[[ZOTERO:group:ID/ITEMKEY]]` explicitly scope the 8-character item key.
- `[[Z:06937]]` is only meaningful alongside the local AutoCite catalog. Never treat 06937 as a globally portable Zotero identifier.
- Unresolved, ambiguous, mismatched, malformed and inaccessible records stay as written and appear in an error report.
- Repeated markers resolve once and create separate citation fields associated with the **same** Zotero item.
- Do not access arbitrary document hyperlinks, send manuscript contents to third-party services, or modify existing Zotero fields.

## 5. Boundary / draft API (proposal, not an existing API)

```js
const textSnapshot = await documentAdapter.readVisibleTextWithRanges(); // TO DEVELOP
const plan = await buildCitationPlan(textSnapshot.text, zoteroResolver);
const result = await applyNativeConversion(plan, documentAdapter);
if (result.status === 'APPLIED_PENDING_ZOTERO_REFRESH') {
  await integrationSession.updateDocument(); // illustrate intent; final API and call signature require validation
}
```

This is conceptual pseudocode. The JavaScript helper in this branch produces offsets within a string snapshot. The Word-native adapter must map these to OLE Automation ranges, taking into account story ranges, tracked revisions, Word fields, Unicode, notes and paragraphs. Directly applying text offsets to Word COM ranges is **unsafe** without this mapping and validation.

## 6. PR sequence after maintainer alignment

- **PR 1 (zotero/zotero):** parser/resolver integration + tests; perhaps only an internal interface until native Word support is ready.
- **PR 2 (zotero/zotero-word-for-windows-integration):** corresponding native range conversion and an explicit command in the template, with Windows Word integration evidence.
- **PR 3 (optional):** user experience, alias portability, cross-platform support, docs.

These are logical steps, not promises about which repository maintainers will prefer. Zotero may require a single coordinated patch series; the decision should be made after reviewing the forum reply.

## 7. Development setup and remaining blockers

The official Word-for-Windows repository documents Visual Studio 2022 and installed Microsoft Office for building the C++ library, with Win32, x64 and ARM64 targets. Its `.dotm` template requires testing in the oldest supported Word release. This environment lacks installed Word/Visual Studio, so no native Windows binary has been built or tested here.

We should not open a PR while the Word-native adapter, UI, and end-to-end Word tests remain unimplemented. This branch provides tangible code, checks and an architectural proposal to shorten work once maintainers comment.

## 8. License and contribution

AutoCite's existing source is MIT. Zotero's upstream repository uses GPL-family licenses, so a future contribution must be submitted under terms appropriate to the specific upstream files, with contributor rights and license compatibility verified. No upstream code was copied into the files added in this preparation branch.
