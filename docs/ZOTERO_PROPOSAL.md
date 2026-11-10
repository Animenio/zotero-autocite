# Technical proposal for Zotero maintainers

**Subject:** Structured in-text markers → live Zotero citations: request for integration guidance and possible contribution

## Problem statement

Researchers sometimes create or receive drafts where sources are represented by identifiers (DOI, Zotero item key, BibTeX key, or a compact alias exported from a local reference catalog). Replacing each reference manually in Word is tedious and error-prone. Zotero supports existing citation-scanning workflows, and the official Word plugin maintains live fields once inserted. The missing workflow we wish to explore is **bulk conversion of explicitly marked identifiers inside an open Word document into live, editable Zotero citations, ideally with a managed Zotero bibliography**.

## Proof of concept

The independent open-source **Zotero AutoCite v0.5 beta** currently:

1. Retrieves/validates bibliographic data using OpenAlex and Crossref, favoring exact DOI lookup.
2. Assigns persistent local short aliases (`[[Z:00017]]`) mapped to metadata and, when available, Zotero item identities.
3. Reads Zotero's local library, optionally creates missing items with user authorization in a preselected collection, and checks for potential duplicates.
4. Converts marked references into `ADDIN ZOTERO_ITEM CSL_CITATION` fields in a **new** `.docx` and adds a Zotero bibliography field.
5. Reports unresolved/ambiguous/inconsistent markers in a CSV/JSON log.

We observed the basic workflow functioning in a limited Windows + Word + Zotero user trial, including two identical markers producing a single bibliography entry, and a separate live-field edit check via Add/Edit Citation. Automated tests (42) pass with mocked interfaces. This remains a beta and not a production-supported integration.

## What it does **not** do

The current app does **not** operate in-place on the Word document currently open; does **not** hook the native Zotero Refresh command; does **not** use a Zotero-endorsed field-writing API; and does **not** claim novel citation parsing compared with RTF Scan, Identifyer, or other extensions.

## Questions for maintainers

1. Is bulk resolution of structured markers an appropriate upstream feature, or better developed as a separate Zotero/Word extension?
2. Is there a supported API for creating native Zotero Word citation fields from a supplied item identity, rather than emitting OOXML directly?
3. Can a separate Word add-in safely call or coordinate with Zotero's Refresh process without changing its existing ribbon control?
4. Would Zotero keys or Better BibTeX citekeys be preferable to local numeric aliases? What identifiers are stable and portable across users/libraries?
5. Are there recommended test harnesses or compatibility guidelines for Windows Word plugin integration?
6. Would maintainers prefer an isolated proof-of-concept PR, a design discussion first, or collaboration with existing citation-conversion projects?

## Safety and design principles

- No silent fuzzy matches or invented references.
- No direct edits to Zotero's internal SQLite database.
- No public API writes without user authorization.
- Preserve source documents and unresolved markers; produce auditable logs.
- Test independently across Zotero and Word versions before claiming compatibility.

## Suggested next steps

First: discuss architecture and overlap on the Zotero Forums and/or zotero-dev mailing list. Second: share a reproducible test and repo source. Third: implement a narrow proof of concept using **supported** interfaces if one exists. Only after that should a PR against Zotero itself be considered.

**References:**

- Zotero local API: https://www.zotero.org/support/dev/web_api/v3/local_api
- Zotero Word plugin: https://www.zotero.org/support/word_processor_plugin_usage
- Zotero developer documentation: https://www.zotero.org/support/dev/
- Zotero RTF Scan: https://www.zotero.org/support/rtf_scan
- Identifyer: https://github.com/JonasBaath/identifyer-for-zotero
