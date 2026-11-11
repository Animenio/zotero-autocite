# Native integration test matrix — acceptance criteria

## Verified in this preparation branch

Run: `cd upstream-prep && npm test` (Node 20+).

The parser and resolution planner have offline tests covering:
- Alias normalization with meaningful leading zeros
- DOI recognition, exact DOI identity check, error on mismatched DOI
- Personal/group item key parsing and exact library + key verification
- Unknown/invalid placeholders retained
- Duplicate references resolved only once, citations counted separately
- Ambiguous and missing sources blocked
- Native adapter transaction with descending offsets, rollback and fail-closed default
- No mutation of document source text during planning

## Not yet verified — required before upstream PR

| Scenario | Expected behavior | Environment |
|---|---|---|
| Word open, 2 short codes to same item | Two editable citation fields, one bibliography item | Windows + Word + Zotero |
| Existing Word citation fields | Existing fields intact, new fields recognized | Windows + Word + Zotero |
| Unresolved and ambiguous codes | No incorrect field; warning and audit log | Windows + Word + Zotero |
| Wrong group/library scope | Refuse citation, no cross-library substitution | Windows + Zotero personal/group libraries |
| Citation in table, heading, styled text | Formatting preserved | Word desktop |
| Notes/footnotes/headers and text boxes | Either verified support or explicit refusal, no corruption | Word desktop |
| Track Changes enabled | No incorrect field operations | Word desktop |
| User cancels/throws mid-operation | Undo restores source document, clear failure message | Word desktop |
| Word 32-bit/64-bit | Native bridge stable on target architectures | Supported Word/Windows |
| Zotero Refresh / Add/Edit Citation | Fields are fully editable after conversion | Word + Zotero |
| Repeat operation | No extra library items or citation duplicates | Word + Zotero |
| Large document (500+ codes) | Bounded runtime, no hang | Word + Zotero |
| Zotero version differences | Compatibility verified against supported release | Word + Zotero |
| Mac and LibreOffice | Explicitly excluded or independently tested | macOS / LibreOffice |

## Public API considerations

- No automatic publication import as a hidden side effect of a Word command.
- User consent for any optional external metadata lookup.
- Local catalog backups; no upload of private bibliography or manuscripts.
- Automated tests run without opening or rewriting the source `.docx`.

Passing unit tests proves only scanner/planner behavior; it does not establish the future Word-native integration.
