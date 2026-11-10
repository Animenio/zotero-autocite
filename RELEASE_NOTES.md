# Release notes — AutoCite v0.5 beta (public proof of concept)

Initial documentation-oriented open-source beta distribution.

- Windows desktop GUI (Tkinter) for DOI-first lookup, catalog alias registration/export, Zotero collection selection, and conversion of Word `.docx` copies.
- Zotero field conversion based on the verified v0.4.2 engine; authorized local Zotero API import, ambiguity/duplicate checks and CSV/JSON diagnostic logs.
- Optional Word VBA macro to initiate copy-based conversion. It does not replace or hook Zotero Refresh.
- Public README, developer proposal, technical overview, privacy guidance, roadmap, reproducible demo, contributing and CI configuration.
- 42 offline Python unit tests passing on the source checked in 2026-11-10; live Word/Zotero compatibility is known only from a limited user-run trial.

Known limitations are detailed in docs/LIMITATIONS.md. This is **not** an official Zotero release.