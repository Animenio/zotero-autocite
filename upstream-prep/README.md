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

## Zotero-native resolver candidate (first upstream-guided increment)

The new [`zoteroNativeLookup.mjs`](src/zoteroNativeLookup.mjs) delegates item
identification to the real Zotero APIs rather than a Python catalog, external
API, or hand-built CSL field. It supports only existing, explicitly scoped
`[[ZOTERO:user/ITEMKEY]]` and `[[ZOTERO:group:ID/ITEMKEY]]` sources.

Its [test cases](test/zoteroNativeLookup.test.mjs) use mocked Zotero APIs and
check identity, library isolation, missing/deleted items, lookup errors,
and compatibility with the read-only planner. **They do not test the live
Zotero application or Word.** This candidate code is marked
`AGPL-3.0-or-later`; the independent AutoCite Desktop code retains its own
license.

Read [the official contribution rules and engineering gates](docs/UPSTREAM_CONTRIBUTION_RULES.md)
before creating any upstream patch or modifying a Zotero Word template.

## Zotero Session and Word-native research spike

We now also have staged, independently reviewable experimental layers:

- [`nativeCitationBatch.mjs`](src/nativeCitationBatch.mjs): converts scoped Zotero
  keys into numeric `Zotero.Item.id` values and `citationItems: [{id}]`, never
  serializing Word field JSON.
- [`wordStoryPreflight.mjs`](src/wordStoryPreflight.mjs): rejects stale marker
  text, unsupported Word stories, field collisions and unsafe state.
- [`sessionCitationRegistration.mjs`](src/sessionCitationRegistration.mjs):
  creates citations via the **real Zotero Session/Citation API shapes**,
  after a native adapter has already inserted valid temporary fields.
- [`wordSessionCoordinator.mjs`](src/wordSessionCoordinator.mjs):
  outlines the strictly checked scan → verified backup → temporary field →
  Session registration → update → commit/rollback sequence.
- [`MarkerRangeValidator.cpp`](native/windows/MarkerRangeValidator.cpp):
  portable C++17 UTF-16 range validation. It has been compiled and tested
  locally with GCC under strict warnings and `-DNDEBUG`. This is not yet
  linked into the official Zotero Word native DLL.
- The [Windows native integration contract](docs/NATIVE_WORD_INTEGRATION_CONTRACT.md)
  maps these stages to Zotero's actual Core and WinWord entrypoints.

**Critical limitation:** the Session and Word coordinator modules are mocks/
interface sketches, not executed inside Zotero. Real C++ COM operations, the
JS/ctypes declarations, ribbon VBA and localization are **not yet implemented**.

The local check executed 31 original Node tests plus 16 additional bridge
smoke cases successfully. The full expanded GitHub test suite and the native
Windows CI jobs still require separate confirmation.

## Scope and status

| Capability | Status |
|---|---|
| Parse, validate and locate supported markers | Implemented, unit-tested |
| Resolve using injected, read-only lookups | Implemented, unit-tested |
| Refuse mismatched DOI/library/item key | Implemented, unit-tested |
| Build and validate a transactional native edit plan | Implemented in pure JS, simulated tests |
| Prepare native Zotero Session citation inputs | Candidate implemented; mocked tests |
| Verify Word UTF-16 ranges and existing-field overlap | C++ validator implemented; no COM DLL integration |
| Register new fields via Zotero.Integration.Session | Experimental adapter only; live Zotero test missing |
| Replace placeholders in **currently open Word** | **Not implemented** |
| Call Zotero native integration/refresh | **Not wired to official integration.js** |
| Create or import library entries from OpenAlex | **Not in upstream scope** |
| Compile and test Zotero's Windows C++ bridge | **Not performed** |

Next steps and acceptance tests: [UPSTREAM_INTEGRATION_PLAN.md](docs/UPSTREAM_INTEGRATION_PLAN.md) and [TEST_MATRIX.md](docs/TEST_MATRIX.md).
