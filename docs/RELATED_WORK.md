# Existing ecosystem and scope of contribution

This project is **not** a claim that Zotero has no citation-scanning or bibliography-generation capability. Relevant existing workflows include:

- **Zotero RTF Scan:** https://www.zotero.org/support/rtf_scan — scans citation markers in RTF and builds a bibliography through a separate workflow.
- **Official Zotero Word processor plugin:** https://www.zotero.org/support/word_processor_plugin_usage — inserts/edits live citations and updates citations/bibliographies with Refresh.
- **Identifyer for Zotero (independent project):** https://github.com/JonasBaath/identifyer-for-zotero — approaches conversion of existing unlinked citations into Zotero fields. Evaluate current functionality and discuss overlap before making novelty claims.
- **Better BibTeX for Zotero:** https://retorque.re/zotero-better-bibtex/ — provides stable and portable citation keys / interoperability in BibTeX-style workflows.

## Possible AutoCite contribution

AutoCite's narrow experiment combines (a) user-controlled compact aliases, (b) DOI/OpenAlex/Crossref bibliographic lookup with discrepancy checking, (c) authorized Zotero library/collection import and duplicate protections, and (d) conversion of explicit markers to live citations in Word.

The most valuable prospective Zotero enhancement is **safe, supported in-document resolution of structured identifiers**, not merely another generator of APA text. A key open question is whether to use Zotero item keys, Better BibTeX keys, or a shared mapping export rather than proprietary local numeric aliases.

Compatibility and comparisons have not been independently benchmarked against all external tools.
