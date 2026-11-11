# AutoCite Word Live FieldFix — manual end-to-end validation

**Date:** 2026-11-11  
**Status:** PASS for the tested Windows Word prototype, **NOT** an upstream Zotero integration or Zotero PR.  
**Evidence type:** Local automated tests, document inspection, and explicit manual verification reported by the tester. The Word UI results were not executed independently by GitHub CI.

## Tested configuration

- Microsoft Windows build 10.0.26300.9974, desktop Microsoft Word (exact Word build not captured)
- Python 3.14 64-bit, pywin32 312
- Zotero Desktop with an indexed personal/group collection of 6,938 items
- Example existing Zotero item key `HJVM9AMK`; DOI `10.1016/j.techfore.2016.08.019`
- Independent Python Word Live Alpha **FieldFix** (Microsoft Word COM), **not** the official Zotero Word integration's C++ implementation
- Source document: `Test_AutoCite_06_FieldFix_RETRY_PULITO.docx`
- Backup: `Test_AutoCite_06_FieldFix_RETRY_PULITO_AutoCite_BACKUP_20261111_183736.docx`
- Output before Zotero Refresh: `Test_AutoCite_06_FieldFix_DOPO_CONVERSIONE.docx`

## Checks performed

| Check | Evidence/result |
| --- | --- |
| Parser / plan | Dry-run identified 3 of 3 `[[Z:06937]]` markers; 0 unknown |
| Backup | Copy generated before any document edit |
| Preflight | Live Word temporary DOCX had complete, readable citation field |
| FieldFix COM insertion | Word reported 3 fields inserted in the currently open file |
| OOXML structural audit before Refresh | 8 `ADDIN ZOTERO_ITEM CSL_CITATION` fields plus 1 bibliography; 9 begin, 9 separate, 9 end; 0 remaining marker strings |
| Existing citation protection | 5 existing fields preserved by pre-Refresh document comparison |
| Field values | New fields associated with Zotero key `HJVM9AMK`, matching DOI |
| Visual integrity | Table, paragraph styling, and bibliography retained |
| Zotero Refresh | Tester reported successful Refresh and normal visible citations, no JSON field-code leakage |
| Add/Edit Citation | Tester explicitly reported all checks working after opening the new citations |
| Bibliography | Single reference entry after Refresh, not duplicated |
| Unit tests | 23/23 focused Python Word Live tests; earlier 66/66 Python and 31/31 JavaScript in the FieldFix package (these are not live Word CI tests) |

The initial Word COM insertion attempt **failed** during Zotero Refresh because generated fields lacked the `separate` field character and their visible result was outside the field. That defect was fixed in FieldFix, rechecked in a temporary live Word document, and the successful test was rerun from the clean backup. The original faulty document should **not** be used as evidence.

## What this does NOT establish

- Not yet implemented in `zotero/zotero` or `zotero/zotero-word-for-windows-integration`.
- COM Alpha is a separate Python prototype. Its working FieldFix source was delivered as a test ZIP; this validation record does not mean that code has been pushed into this GitHub branch.
- Does not prove compatibility with Word 32-bit, ARM64, macOS, LibreOffice, tracked changes, headers, footnotes, protected documents, ambiguous library identifiers, or production-scale manuscripts.
- Does not prove crash-safe rollback under unexpected process termination.
- Does not provide an official build of Zotero's Windows C++ bridge.

## Upstream readiness gates

1. Port the tested field representation and identity resolution to Zotero's *own* citation/session API rather than hand-generating field JSON in the official integration.
2. Implement a safe Word range adapter in `zotero-word-for-windows-integration`; preserve existing fields and support a validation/backup protocol.
3. Add a Word ribbon command and Zotero command dispatch with explicit user confirmation.
4. Run upstream unit/integration tests and real Word tests in each declared supported configuration.
5. Get maintainer architectural feedback before opening coordinated upstream PRs.

Related: [Upstream integration plan](UPSTREAM_INTEGRATION_PLAN.md), [Test matrix](TEST_MATRIX.md), and [PR draft](PR_DRAFT.md).
