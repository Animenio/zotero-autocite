# Contributing to Zotero AutoCite

Thanks for your interest in this independent research software project. The current code is a beta proof of concept.

Before proposing code changes, open an issue describing the use case and possible interaction with existing Zotero functionality. Avoid making claims of official Zotero support.

1. Fork/clone the project.
2. Use Python 3.10+; install `requirements.txt`.
3. Run `python -m unittest -v` before and after changes.
4. Include regression tests for changes to marker parsing, OOXML/Word fields, Zotero writes, or data migration.
5. Prefer supported Zotero API methods; do not directly edit the Zotero internal database.
6. Redact all file paths, private documents, personal bibliography data, tokens, and local logs from issues and test fixtures.

Please keep pull requests narrowly scoped and clearly describe version coverage, mock tests, and any live Windows/Zotero testing performed.