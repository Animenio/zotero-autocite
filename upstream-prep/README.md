# AutoCite → Zotero upstream integration preparation

This directory is a reviewable **preparation branch** for a possible future upstream contribution. No changes have been made to Zotero's repositories, and **this is not yet a Zotero plugin, a working Word add-in, or a pull request**.

The proof-of-concept v0.5 Python application remains on our `main` branch. This experiment explores a small, dependency-free JavaScript component that could be adapted to Zotero's native JavaScript integration code, rather than transplanting Python and manually generating OOXML into Zotero.

## Evidence-based rationale

- Zotero's `chrome/content/zotero/xpcom/integration.js` owns citation sessions, live field processing, bibliographies and refresh.
- The Windows integration submodule uses `Zotero.dotm` VBA command dispatch, a JavaScript ctypes bridge and a C++ OLE Automation library for Word documents.
- Zotero already implements `Document.convertPlaceholdersToFields` to convert **temporary note hyperlinks** to live citation fields. It is **not** a general-purpose plaintext `[[Z:...]]` converter. Reusing its field insertion approach is preferable to writing Word OOXML ourselves.

Relevant upstream files are cited in [UPSTREAM_INTEGRATION_PLAN.md](docs/UPSTREAM_INTEGRATION_PLAN.md).

## What's implemented here

- `src/placeholderParser.mjs`: pure scanner of supported `[[...]]` markers, reporting exact ranges and invalid syntax.
- `src/resolutionPlanner.mjs`: read-only, deterministic, cached bibliography lookup with strict identity verification and ambiguity reporting.
- `src/nativeTransaction.mjs`: adapter boundary for a future Word-native insertion, with fail-closed default, descending edit order and rollback hooks.
- `test/`: Node built-in tests exercising the above **without access to Zotero, Word, or network services**.

`npm test` (or `node --test test/*.test.mjs`) runs the tests with Node 20+ and no package installation.

## Proposed marker contracts

```
[[Z:06937]]                         Local AutoCite alias (requires the user's registry)
[[ZOTERO:user/ABCDEFGH]]           Existing Zotero item, personal library
[[ZOTERO:group:12345/ABCDEFGH]]   Existing Zotero item, explicitly scoped group
[[ZDOI:10.1016/j.techfore.2016.08.019]]  Exact DOI match
```

The portable syntax is **proposed for discussion**; it is not recognized by the existing Zotero Word plugin. Legacy aliases such as `[[Z:06937]]` are **not globally unique**: they must not be interpreted without the correct local catalog. Missing and ambiguous references never result in fabricated citations.

## Scope and status

| Capability | Status |
|---|---|
| Parse, validate and locate supported markers | Implemented, unit-tested |
| Resolve using injected, read-only lookups | Implemented, unit-tested |
| Refuse mismatched DOI/library/item key | Implemented, unit-tested |
| Build and validate a transactional native edit plan | Implemented, simulated tests |
| Replace placeholders in **currently open Word** | **Not implemented** |
| Call Zotero native integration/refresh | **Not implemented** |
| Create or import library entries from OpenAlex | **Not in upstream scope** |
| Compile and test Zotero's Windows C++ bridge | **Not performed** |

Next steps and acceptance tests: [UPSTREAM_INTEGRATION_PLAN.md](docs/UPSTREAM_INTEGRATION_PLAN.md) and [TEST_MATRIX.md](docs/TEST_MATRIX.md).
