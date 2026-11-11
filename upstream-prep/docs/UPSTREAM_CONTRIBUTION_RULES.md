# Zotero upstream contribution rules and implementation checkpoints

Prepared 2026-11-11 from the **official** Zotero source and development documentation.
This is internal preparation: **no GitHub issue, Zotero pull request, or upstream edit has been made.**

## 1. Official contribution process

- Zotero asks contributors to discuss feature requests in the Zotero Forums, **not** to open independent GitHub Issues for feature proposals. Their developers create issues for confirmed or agreed-upon work.
  - https://github.com/zotero/zotero/blob/main/CONTRIBUTING.md
  - https://www.zotero.org/support/dev/source_code
- Their documented patch workflow is to **fork the relevant repository, commit, and open a GitHub pull request**.
- Our feature request is already in the forum: https://forums.zotero.org/discussion/134719/feature-request-one-click-conversion-of-citation-placeholders-into-zotero-citations-in-word
- Before a PR, seek maintainer feedback on feature scope: Windows-only initially versus cross-platform requirements, and which repository should own which interfaces.

## 2. License and code ownership

- Zotero source is **AGPLv3 or later unless a specific file says otherwise**: https://www.zotero.org/support/dev/source_code
- The official Word integration VBA file (Zotero.bas) states **GPLv3 or later**, so its license cannot be inferred from the core client.
- AutoCite main application is MIT-licensed and **does not automatically become Zotero upstream code**.
- New candidate module \`src/zoteroNativeLookup.mjs\` and its tests use \`SPDX-License-Identifier: AGPL-3.0-or-later\`. These files are original integration preparation and are segregated from the MIT AutoCite desktop application.
- Verify licensing of every modified upstream file before copying any upstream source or creating a patch against it.

## 3. Zotero JavaScript coding guidelines

Official: https://www.zotero.org/support/dev/client_coding/coding_guidelines

- Tabs (display width 4); lines generally 100 characters or less.
- JavaScript strict mode and semicolons.
- Pascal/CamelCase for Zotero objects and namespaces; lower-case initial for variables/functions; preserve capitalized acronyms such as \`getID()\`.
- K&R/1TBS braces; always use braces for multiline conditionals.
- JSDoc for functions; line comments have a leading space.
- Use \`throw new Error()\` for true programming errors; avoid throwing strings.
- User-facing messages must use localization files rather than hardcoded English.
- Existing nonconforming code should not be reformatted just for style.

## 4. Verified Zotero APIs and call graph

Current main-branch source consulted:

- Core dispatch: https://github.com/zotero/zotero/blob/main/chrome/content/zotero/xpcom/integration.js
- Core integration test dummy: https://github.com/zotero/zotero/blob/main/test/tests/integrationTest.js
- Native JS wrapper: https://github.com/zotero/zotero-word-for-windows-integration/blob/main/components/zoteroWinWordIntegration.mjs
- Native Windows C++ document: https://github.com/zotero/zotero-word-for-windows-integration/blob/main/build/zoteroWinWordIntegration/document.cpp
- Word VBA commands: https://github.com/zotero/zotero-word-for-windows-integration/blob/main/build/template/Zotero.dotm/word/vbaProject.bin/Zotero.bas

Current dispatch: Word VBA's \`ZoteroCommand(name, ...)\` -> Windows message -> \`Zotero.Integration.execCommand(agent, command, docId, templateVersion)\` -> \`new Zotero.Integration.Interface(...)[command]()\` -> Word plugin's JS/ctypes wrapper -> native Windows OLE Automation.

Verified **read-only** item resolution APIs:
- \`Zotero.Libraries.userLibraryID\`
- \`Zotero.Groups.getLibraryIDFromGroupID(groupID)\`
- \`Zotero.Items.getByLibraryAndKeyAsync(libraryID, key)\`

The official test helper uses \`/^[23456789ABCDEFGHIJKLMNPQRSTUVWXYZ]{8}$/\` as the generated item-key pattern:
https://github.com/zotero/zotero/blob/main/test/content/support.js

The existing \`convertPlaceholdersToFields\` method handles **special note hyperlinks**, not arbitrary plaintext citation markers. Do not call it on plain \`[[...]]\` without a new native range adapter.

## 5. Implementation increment completed in our preparation branch

Files:
- \`upstream-prep/src/zoteroNativeLookup.mjs\`
- \`upstream-prep/test/zoteroNativeLookup.test.mjs\`
- Existing \`upstream-prep/src/resolutionPlanner.mjs\` is used by the new tests.

New behavior is **read-only** and scoped:
- Supports existing Zotero records identified by \`[[ZOTERO:user/ITEMKEY]]\` or \`[[ZOTERO:group:GROUPID/ITEMKEY]]\`.
- Looks up each record in the *exact* Zotero library and verifies returned library and item key; no cross-library fallback.
- Refuses inaccessible groups, missing items, deleted/attachment/feed items, identity mismatches, and failed lookups.
- Does not import any metadata, add Zotero items, call OpenAlex/Crossref, change a document, or create field code.
- The older \`[[Z:06937]]\` alias is **not portable**, and is intentionally left in independent AutoCite Desktop, not the initial upstream contribution.
- The candidate module does **not** yet run inside Zotero Core; it awaits integration wiring and official tests.

Validation: a new suite of 13 Node test cases has been committed. Their results must be confirmed by GitHub Actions and/or a local \`cd upstream-prep && npm test\` run; GitHub publication is not evidence of successful execution.

## 6. Build and test rules before an upstream pull request

- Zotero core: follow https://www.zotero.org/support/dev/client_coding/building_the_desktop_app
- Clone the core with \`git clone --recursive\`, use Git LFS, and follow the official Windows-specific build prerequisites. Keep \`core.autocrlf\` disabled or set to \`input\`.
- Windows integration: Visual Studio 2022 + Office; build release for Win32, x64 and ARM64 according to its README.
- Install the word-integration Git hooks using \`./scripts/install_hooks.sh\` before editing the template; keep unpacked \`.dotm\` contents synchronized and compile VBA via Word's **Debug → Compile Project**.
- Do not overwrite a user's installed Zotero Word template in the course of exploratory development.
- Add tests to the *official* \`test/tests/integrationTest.js\` when the command and native document interface are defined. Node tests alone do not count as Zotero integration tests.
- Confirm backup, range mapping, field validity, session-managed citation serialization and UI localization before PR.

## 7. Outstanding engineering work

1. Ask for / await guidance on command architecture from maintainers in the existing forum thread.
2. Provide a Zotero-side command that invokes the resolver and creates citations through Zotero's own session, not Python-generated CSL field JSON.
3. Extend the Windows JS/ctypes and C++ document interface to scan supported ranges and replace validated plaintext markers without changing existing fields.
4. Add ribbon UI and localized messages, handle user cancellation and rollback.
5. Compile and test with real Word and the supported Zotero client; include upstream unit/integration tests and patch review.
6. Only then open coordinated pull request(s).

**Status:** upstream-guidelines review complete; resolver prototype committed; native command and official PR **not yet implemented**.
