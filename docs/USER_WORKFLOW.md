# User workflow: AI-assisted drafting and Zotero citations

## A. Register sources

1. In AutoCite's **Search article** screen, search **by DOI first** where possible, or by title/author and explicitly select a result.
2. Compare its title, author list, publication date and venue with the publisher's source. OpenAlex and Crossref dates may differ (online first vs issue year).
3. Register the verified bibliographic record. AutoCite returns an alias such as `[[Z:00017]]`.
4. Repeat for other papers. Use **Catalog and codes → Export CSV** when a collaborator or a writing assistant needs the code-to-source mapping.

## B. Draft with compact markers

An example request to an assistant:

> Use only articles present in the attached AutoCite CSV. When a claim needs a citation, insert the matching `[[Z:NNNNN]]` alias rather than an author–year placeholder. Do not invent an alias or source. Identify unsupported claims separately.

**Validation is still a research task.** A valid code only identifies a paper; it does not prove that the cited paper supports the sentence. Read the source and check claims before submission.

## C. Convert the Word document

Use a copy of your manuscript and insert a standalone `[[ZBIB]]` where its Zotero-managed bibliography should appear. Save and close Word, run AutoCite's **Convert Word**, then open the generated `.docx` and choose **Zotero → Refresh**.

The converter produces: `NAME_Zoterizzato.docx`, `NAME_Zoterizzato_LOG.csv`, and `NAME_Zoterizzato_riepilogo.json`. Unresolved markers remain visible; inspect the log.

## D. Re-run and collaborate

Codes are *local catalog aliases*, not interchangeable global research identifiers. When two people work on the manuscript, share the CSV mapping (and, when appropriate, a managed export/import strategy) before writing. Avoid merging two independent catalogs by blindly combining numeric aliases. The local database is the source of truth for mapping and Zotero IDs.

The current macro `ZoteroAutoCite_Word_05.bas` offers an optional button to launch the copy-based conversion from Word Desktop, but the document still opens as a separate converted copy and Zotero Refresh remains manual.
