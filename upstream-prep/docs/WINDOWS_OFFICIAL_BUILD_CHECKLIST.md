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

## First local Visual Studio build after patch application

The native patch has been applied in an independent clone, affecting only:
`build/zoteroWinWordIntegration/document.cpp`,
`build/zoteroWinWordIntegration/zoteroWinWordIntegration.h`, and
`components/zoteroWinWordIntegration.mjs`.

Open the exact official solution from **Windows Command Prompt**:

```cmd
start "" "%USERPROFILE%\Downloads\zotero-word-for-windows-integration\build\zoteroWinWordIntegration\zoteroWinWordIntegration.sln"
```

In Visual Studio 2022 select **Release | x64**, then **Build > Build Solution**
(or press Ctrl+Shift+B). Use the **Desktop development with C++**
toolchain with MSVC v143, Windows SDK and C++ MFC libraries if prompted.

**Important verification:** the official README mentions `imports.h`,
but a file at `build/zoteroWinWordIntegration/imports.h` is absent from
the inspected upstream tree, and the `.vcxproj` does not reference it.
Do **not** create or modify an `imports.h` file until a compiler error
actually identifies a missing import.

The project defines a custom build command copying the DLL into the clone's
own `install/` directory. This is a **local build artifact**, not an
installation into the user's Zotero/Word programs. Do **not** manually
copy the DLL into active Word/Zotero directories or replace `Zotero.dotm`.

If the build fails, capture the first compiler error plus its file/line
and the final `Succeeded/Failed` summary; do not send only the last
linker error. If the solution cannot be opened or Visual Studio 2022 is not
installed, install VS using the official Microsoft installer rather than
attempting to compile with Python or `sudo`.

This build step is pending: no successful native Visual Studio compilation
has yet been reported.

## November 12, 2026 — first real MSVC Release x64 build

The user successfully applied the first two read-only native patches to a separate Zotero Word source clone, opened the solution in Visual Studio 2022 Community and started **Release | x64**. The compiler reported:

```
document.cpp(580,47): error C2228: expression before .Item must have class/struct/union type
Actual type: LPDISPATCH
document.cpp(1129,23): warning C4018: signed/unsigned comparison
Build: 0 succeeded, 1 failed
```

Diagnosis confirmed from the official source: `get_StoryRanges()` returns an
`LPDISPATCH`. Its wrapper `CStoryRanges` must be constructed before
invoking the `Item(1)` method. The official `document.cpp` already uses
this exact pattern in other functions. The C4018 warning is unrelated and
non-fatal.

Corrected patch **0003**:
```cpp
CStoryRanges stories = doc->comDoc.get_StoryRanges();
CRange story = stories.Item(1);
```

A local clone with 0001 and 0002 already applied is **dirty by design**,
so the full patch-script check **must not** be rerun on that checkout.
Instead apply 0003 directly or change those two lines in Visual Studio.
The user subsequently applied the equivalent two-line correction manually
in the existing Visual Studio checkout and reran the MSVC build:

```
Configuration: Release x64
document.cpp(1130,23): warning C4018: signed/unsigned comparison
Generated: build/zoteroWinWordIntegration/x64/Release/zoteroWinWordIntegration.dll
Compilation: 1 succeeded, 0 failed
```

**Result: native DLL compilation PASS (MSVC v143, Release x64).**
This establishes compile/link success only. The two newly exported functions
have not yet been checked via PE exports, invoked through js-ctypes, or tested
with a real Word main story. The existing C4018 warning remains nonblocking.

Next safe read-only smoke test: open **Visual Studio 2022 > Tools > Command
Line > Developer Command Prompt**, then inspect the generated DLL without
installing or executing it:

```cmd
dumpbin /exports "%USERPROFILE%\Downloads\zotero-word-for-windows-integration\build\zoteroWinWordIntegration\x64\Release\zoteroWinWordIntegration.dll" | findstr /I "getMainStorySnapshot getMainStoryFieldRanges"
```

The inspection must list both exports. If one is absent, stop and check the
header declarations and DLL being inspected; **do not install this DLL**.
A DLL export check does not validate field geometry or the behavior of COM
objects in Word.

## November 12, 2026 — PE export inspection PASS

After the corrected Visual Studio 2022 Community **Release | x64**
compile succeeded, the tester used the **Visual Studio 2022 Developer
Command Prompt v17.14.45** to inspect the built DLL:

```cmd
dumpbin /exports "%USERPROFILE%\Downloads\zotero-word-for-windows-integration\build\zoteroWinWordIntegration\x64\Release\zoteroWinWordIntegration.dll" | findstr /I "getMainStorySnapshot getMainStoryFieldRanges"
```

Actual output:

```text
18   11 000053C0 getMainStoryFieldRanges
19   12 00005130 getMainStorySnapshot
```

**Result: both intended API names are exported by the Release x64 DLL.**
This proves link/export visibility only. The new functions have **not**
been invoked through `js-ctypes` or tested against Microsoft Word COM;
valid field span coordinates, CString ownership, and runtime safety remain
open validation tasks. Do not install the DLL or overwrite `Zotero.dotm`.

Next non-invasive validation: compile `Release | Win32` using the official
VS2022 solution, confirm its two exports, then (if relevant SDK/tools
are installed) try `Release | ARM64`. Never run or install artifacts
until the isolated runtime harness is ready.

## Stage F — experimental read-only native snapshot patch (current increment)

The three patches (two new APIs and the C2228 correction) implement **only read access** to Word's main-story text, and
the boundaries of its existing Word fields, through C++ and matching JS/ctypes
methods. It does not support conversion, Word backup, saved/revision-state checking,
or a user-visible Word ribbon button. The field-range API emits absolute
Word offsets, while the JavaScript preflight requires offsets *relative* to the
snapshot story start. A future adapter must subtract that start only after
confirming a consistent snapshot.

Patches, applied in order:
- `upstream-prep/patches/zotero-word-for-windows-integration/0001-main-story-readonly-snapshot.patch`
- `upstream-prep/patches/zotero-word-for-windows-integration/0002-main-story-field-ranges.patch`
- `upstream-prep/patches/zotero-word-for-windows-integration/0003-fix-com-story-ranges-wrapper.patch`

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
