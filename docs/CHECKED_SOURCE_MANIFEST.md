# Source preparation notes

- Based on the user-tested source package `Zotero_AutoCite_Desktop_0.5_BETA.zip`.
- All core Python source, `.bat` launchers, two `.bas` Word macros and public synthetic `.docx` fixtures were preserved.
- The existing Italian README and quick-start were retained as `docs/ORIGINAL_README_IT.md` and `docs/LEGACY_QUICKSTART_IT.md`; changelogs were moved into `docs/`.
- The desktop screenshot was moved to `assets/autocite-desktop-preview.png`.
- New public-facing English documentation, a license, `.gitignore`, and CI were added.
- The code was not refactored or modified; the automation tests were run against the original extracted project.

**Important:** Before the first public release, project ownership/licensing and all external service policies should be reviewed by the maintainer. This manifest does not constitute a security certification.
