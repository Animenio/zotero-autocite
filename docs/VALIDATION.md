# Validation and reproducibility

## Automated tests

Command:

```bash
python -m pip install -r requirements.txt
python -m unittest -v
```

**Recorded result on 2026-11-10:** 42 passed, 0 failed, on the v0.5 source bundle. The suite includes:

- Recognition of DOI/key/alias markers, including Word runs and tables.
- Preservation of spaces before citations and punctuation around them.
- Non-destructive handling of missing/inconsistent references.
- Persistence of local aliases and backward-compatible catalog migration.
- DOI-first matching, OpenAlex/Crossref conflicts, and exact DOI fallback.
- Blocking potentially duplicate Zotero records.
- Local Zotero API payload construction and regression for the unavailable `/items/new` route.
- Defensive handling of repeated failed imports in one document.
- Selecting a verified Zotero collection and avoiding overwriting original/generated DOCX files.

Automated tests **mock/simulate** the external APIs and do not constitute a full end-to-end Zotero + Microsoft Word test on the CI runner.

## Limited real-world trial

Environment: a user-run Windows desktop installation with Microsoft Word and Zotero Desktop.

Scenario: register a reference to Frey & Osborne, DOI `10.1016/j.techfore.2016.08.019`; produce a short code in the local registry; convert a test manuscript containing two identical code references; run Zotero Refresh.

Observed during the conversation-based test:

1. The converter reported 2 converted citations and a bibliography field, with no unresolved markers.
2. Zotero Refresh produced two correctly formatted in-text citations and a single bibliography entry.
3. Previously, the user confirmed Add/Edit Citation recognized a generated live field for a separate Jensen & Meckling test.
4. Re-running the same source did not produce an additional Zotero record, per user confirmation.

This is **anecdotal, limited validation** and not an independent compatibility audit. It does **not** establish production readiness, guaranteed citation accuracy, or that all platform/Word/Zotero combinations are supported.

## How reviewers can reproduce

1. Download the source code and install dependencies.
2. Run the unit tests.
3. In Zotero create a new test collection.
4. In AutoCite search the Frey–Osborne DOI and register the returned code (do not hardcode `06937` unless that alias is assigned in your local catalog).
5. Write two `[[Z:YOUR_ID]]` markers into a short Word `.docx`, and add standalone `[[ZBIB]]`.
6. Convert, open the generated file, click Zotero Refresh, and check Add/Edit Citation.
7. Re-run the original and verify that duplicate items are not created.
8. Report exact Zotero/Word/Python versions and upload *redacted* logs if a failure occurs.
