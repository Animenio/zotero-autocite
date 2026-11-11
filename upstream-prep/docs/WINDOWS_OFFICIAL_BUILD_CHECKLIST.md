# Windows build and official acceptance checklist

Prepared 2026-11-11. This is an **engineering checklist, not an upstream PR or tested native Zotero build**.

## Official sources checked

- Zotero source setup: https://www.zotero.org/support/dev/source_code
- Zotero desktop development: https://www.zotero.org/support/dev/client_coding/building_the_desktop_app
- Zotero client contribution rules: https://github.com/zotero/zotero/blob/main/CONTRIBUTING.md
- Windows Word integration build instructions: https://github.com/zotero/zotero-word-for-windows-integration/blob/main/README.md
- Official integration test reference: https://github.com/zotero/zotero/blob/main/test/tests/integrationTest.js

Always review the live guides again before a production build; the build prerequisites may change.

## Stage A — pure JavaScript candidate (safe to run now)

Open a terminal in a fresh checkout of **our own feature branch**. From the repo root:

```powershell
cd upstream-prep
node --version
npm test
```

Expected: all parser, resolver, planning, Word preflight, Session and coordinator tests pass. The expanded branch currently defines **94** Node test cases (31 original + 63 newer); verify the actual number rather than treating it as an upstream guarantee.

No instance of Word/Zotero is needed for these pure-JavaScript tests. This phase must not change a Word document or a Zotero database.

## Stage B — C++17 Word range validation

In `upstream-prep/native/windows`, compile and run the independent native validator. From an appropriate VS 2022 x64 Native Tools Command Prompt:

```cmd
cl /nologo /std:c++17 /EHsc /W4 /WX /O2 /DNDEBUG MarkerRangeValidator.cpp MarkerRangeValidatorTest.cpp /Fe:marker-validator.exe
marker-validator.exe
```

Exit code **0** means this standalone range validation test passed. This does **not** build Zotero's DLL, does not test COM and does not constitute a Word integration build.

GitHub Actions file `.github/workflows/native-range-tests.yml` separately proposes GCC Linux and MSVC Windows checks. Review their actual run status in GitHub Actions.

## Stage C — official Zotero client build (when a real integration patch exists)

Use an **isolated development profile** and follow the official Zotero build documentation. It requires Git, Git LFS, recursive cloning/submodules, Node/npm and the platform-specific prerequisites. Its Windows instructions address line endings. Do not overwrite or mix with your production Zotero profile.

Representative documented setup (run only after checking current official requirements):

```powershell
git lfs install
git clone --recursive https://github.com/zotero/zotero zotero-client
cd zotero-client
npm install
```

The desktop build/run command documented by Zotero is `app/scripts/build_and_run -r`, but check Windows shell compatibility and the up-to-date documentation before invoking it. Do not install/reinstall Zotero over the user's working version as a prerequisite for an experiment.

## Stage D — official Windows Word integration build (NOT READY YET)

Zotero Word for Windows Integration README requires:
- Visual Studio **2022**, Microsoft Office, and correct Word typelib paths in `imports.h`
- Release build for **Win32, x64 and ARM64** architectures
- Source-specific template tooling and the hook `./scripts/install_hooks.sh`
- VBA template modification through Word, `Debug > Compile Project`, and the repository's `build/template/unpack_templates.sh`

The future patch must touch *the right upstream project files*:
`build/zoteroWinWordIntegration/document.cpp`,
`build/zoteroWinWordIntegration/zoteroWinWordIntegration.h`,
`components/zoteroWinWordIntegration.mjs`, and Word template macros/ribbon only after the corresponding core command is functional.

No such complete patch has been compiled in this preparation branch.

## Stage E — acceptance tests before upstream PR

- [ ] Official Core `integrationTest.js` covers new command and successful Session-owned citation registration.
- [ ] Windows DLL compiles in the required architectures.
- [ ] Word native snapshot includes precise UTF-16 offsets and existing Word field boundaries.
- [ ] Word's existing UndoRecord is *reused*, never nested.
- [ ] Full document scope is deliberately restricted (main text body first, other stories not silently scanned).
- [ ] User approves edit after a localized preview.
- [ ] Backup validated *before* insertion, and fresh Word snapshot is compared immediately before editing.
- [ ] Existing Word and Zotero fields preserved bit-for-bit when not targeted.
- [ ] Citation inserted with native field creation and Zotero Integration Session serialization; **never handcrafted JSON/OOXML**.
- [ ] Confirmed Zotero Refresh and Add/Edit Citation after save/reopen, including a real table and multiple same-paragraph markers.
- [ ] No partially edited document if a marker is ambiguous/missing; failures and rollback reported precisely.
- [ ] Test duplicate source keys in user vs group, deleted items, unsupported markers and changed text.
- [ ] Verify real backup recovery and crash-failure limitations; do not imply an atomic Word transaction.
- [ ] Follow Zotero formatting, localization, license, tests and maintainer feature-discussion rules.

## Status

The independent Python COM **FieldFix** proof-of-concept was manually validated with Word/Zotero, but is not an upstream Word extension. The preparation branch currently contains pure-JS native-shape planning, mocked Session registration, and a standalone C++17 range validator. The full Word C++/JS-ctypes/VBA implementation remains to be built and tested.

## Stage F — experimental read-only native snapshot patch (current increment)

These two patches implement **only read access** to Word's main-story text, and
the boundaries of its existing Word fields, through C++ and matching JS/ctypes
methods. It does not support conversion, Word backup, saved/revision-state checking,
or a user-visible Word ribbon button. The field-range API emits absolute
Word offsets, while the JavaScript preflight requires offsets *relative* to the
snapshot story start. A future adapter must subtract that start only after
confirming a consistent snapshot.

Patches, applied in order:
- `upstream-prep/patches/zotero-word-for-windows-integration/0001-main-story-readonly-snapshot.patch`
- `upstream-prep/patches/zotero-word-for-windows-integration/0002-main-story-field-ranges.patch`

Safe apply script:
`upstream-prep/scripts/apply-word-snapshot-patch.ps1`

Use a **clean, separately cloned** checkout of the official repository:
```powershell
git clone https://github.com/zotero/zotero-word-for-windows-integration.git C:\dev\zotero-word-for-windows-integration
```

From the `upstream-prep` of the **freshly downloaded** AutoCite feature branch:
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\apply-word-snapshot-patch.ps1" -ZoteroWordRepository "C:\dev\zotero-word-for-windows-integration"
```
This checks compatibility without editing anything. Only after success, repeat
the exact command with `-Apply`. The script refuses a dirty worktree.

To build: open `C:\dev\zotero-word-for-windows-integration\build\zoteroWinWordIntegration\zoteroWinWordIntegration.sln`
in **Visual Studio 2022**, follow its official `imports.h` setup, select
**Release | x64**, and use **Build Solution**. Do **not** install the resulting
DLL or replace Zotero.dotm: this increment lacks a test UI command.

Important: the patch checker CI validates applicability against the official
GitHub sources, not full MSVC compilation. The actual native build remains
unconfirmed until Visual Studio reports successful compilation.

## Critical discovery: temporary Word fields are not enumerated as Zotero citations

Upstream `field.cpp` recognizes fields with prefixes
` ADDIN ZOTERO_` or ` CSL_`. An arbitrary `TEMP`-only Word field does
**not** automatically appear in a new `getFields(true)` enumeration.

Our existing `sessionCitationRegistration.mjs` and `wordSessionCoordinator.mjs`
are architectural sketches, not runnable integration commands. In the real
Zotero Word plugin, they will block if they try to locate uncoded TEMP fields
after a forced re-enumeration. A correct future feature must use Session-managed
serialization/caching and prove the field lifecycle in the official integration
tests before mutating Word documents.
