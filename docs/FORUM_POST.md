# Proposed Zotero Forums post (draft — review before publishing)

**Suggested category:** Feature Requests / Developer discussion, as appropriate on the forum.

**Suggested title:** Proposal + working proof of concept: convert structured citation markers to editable Zotero citations in Word

Hello Zotero team and community,

I'm a PhD researcher developing **Zotero AutoCite**, an independent, free, open-source proof of concept that converts short reference markers in Word (for example, `[[Z:00017]]`) into editable Zotero citations and a Zotero-managed bibliography.

I know Zotero already offers RTF Scan and its Word plugin, and that third-party work such as Identifyer addresses related citation-conversion workflows. I am not proposing to duplicate those features without understanding the overlap.

Our specific use case is a manuscript drafted with **structured reference identifiers**. The current beta can register sources through DOI-first OpenAlex/Crossref lookup, store a short-code mapping in a local catalog, resolve or (when authorized) import an item into a selected Zotero collection, and generate a new Word document containing native Zotero citation fields and a bibliography field. It retains unresolved markers and generates a diagnostic log.

We have **42 passing automated tests** and limited user-run Windows + Word + Zotero validation, but this is still an experimental proof of concept. Importantly, it **does not yet** convert the currently open document in-place or extend Zotero's native Refresh button. The field serialization currently depends on Word OOXML, which may be fragile.

I would appreciate guidance on:

1. Whether such bulk structured-marker resolution is better designed as a Zotero feature or a separate Word/Zotero plugin;
2. Whether there is a supported API for creating/updating live Zotero citation fields in a document;
3. Whether Zotero/Better BibTeX keys would be preferable to local aliases for portable workflows;
4. Whether maintainers would be interested in discussing an isolated proof of concept, including how to avoid overlap with existing tools.

**Project repository:** [INSERT THE PUBLIC GITHUB REPOSITORY URL]

**Technical description:** see `docs/ZOTERO_PROPOSAL.md` in the repository.

Happy to provide reproducible test files and a short demo video. Thank you for any guidance on the most useful direction for a contribution.
