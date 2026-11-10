# Known limitations and unresolved technical issues

1. **No native, in-place Word conversion.** v0.5 creates a new `.docx`. The optional VBA macro is a launcher, not a true Zotero/Word extension.
2. **Zotero Refresh remains manual.** It does not recognize arbitrary AutoCite markers; it refreshes live Zotero fields only.
3. **OOXML coupling.** The project inserts Zotero fields directly via OOXML. Future Zotero releases may not accept or may change this representation.
4. **Syntax coverage.** Multiple references in one Zotero citation field, narrative citations, and automatic conversion of unmarked `(Author, Year)` text are not implemented.
5. **Document coverage.** Complex pre-existing fields, notes, footers, comments, textboxes, hyperlinks, and some structured objects are skipped or unsupported.
6. **Matching.** The resolver favors exact DOI/key/alias matches; records without DOI can be ambiguous; OpenAlex/Crossref metadata can differ, including publication years.
7. **Portability.** `[[Z:00001]]` belongs to a local SQLite catalog, not a global registry. Sharing a Word file without the mapping may leave markers unresolved.
8. **Platform.** The workflow is designed and tested primarily on Windows with Word Desktop and Zotero; no formal macOS or Linux Word-plugin support claim.
9. **API quotas.** Metadata discovery depends on external service availability and policy/rate limits.
10. **Research integrity.** A resolved citation does not guarantee that the cited paper supports the scientific statement.

## Priorities before a stable release

- Obtain Zotero developer guidance on supported Word/plugin APIs.
- Add one-step in-place conversion with backups/undo and robust Word-field handling.
- Add transportable mapping/export format and Better BibTeX interoperability.
- Develop independent cross-version integration tests and failure-injection tests.
- Improve source metadata review and narrative/cluster citation support.
