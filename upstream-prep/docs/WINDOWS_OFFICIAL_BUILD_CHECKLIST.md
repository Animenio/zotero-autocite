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

## November 12, 2026 — first Win32 native build PASS

The tester ran Visual Studio 2022 Release | Win32 using the same
read-only patches and C2228 wrapper correction. Output:

```text
document.cpp(1130,23): warning C4018 (signed/unsigned mismatch)
Generated: build/zoteroWinWordIntegration/Release/zoteroWinWordIntegration.dll
Compilation: 1 succeeded, 0 failed
```

The build also created the corresponding .lib/.exp files and executed
the upstream project's custom local copy command. **Win32 compile/link
PASS; its two required exports have not yet been checked.** This is not
evidence of correct Word COM runtime behavior.

Inspect the Win32 DLL via the Visual Studio Developer Command Prompt:

```cmd
dumpbin /exports "%USERPROFILE%\Downloads\zotero-word-for-windows-integration\build\zoteroWinWordIntegration\Release\zoteroWinWordIntegration.dll" | findstr /I "getMainStorySnapshot getMainStoryFieldRanges"
```

Both export names must appear before proceeding to ARM64. No installation
or replacement of an active Word template or Zotero plugin is required.

## November 12, 2026 — Win32 export inspection PASS

The tester inspected both independently compiled DLLs in the
Visual Studio 2022 Developer Command Prompt v17.14.45.

```text
x64 /Release/:
 18  11 000053C0 getMainStoryFieldRanges
 19  12 00005130 getMainStorySnapshot

Win32 /Release/:
 18  11 00004DF0 _getMainStoryFieldRanges@12
 19  12 00004B90 _getMainStorySnapshot@16
```

**Result:** PE exports are present in both x64 and Win32 binaries. The Win32
leading underscore and trailing `@N` are the normal `__stdcall` decorated
symbol names (N is the argument byte count), not a failure. The existing
Zotero JS wrapper declares functions with `ctypes.stdcall_abi` (which
automatically handles this name decoration on Windows, unlike
`ctypes.winapi_abi`). Sources: Mozilla js-ctypes ABI documentation and
Microsoft's documentation on `__stdcall` exported names.

Next: **Release | ARM64** using Visual Studio 2022 and the official
Zotero Word integration solution. Compile success and PE exports
must each be checked separately.

Do not install or execute the experimental DLL in the production Zotero
installation. Real Microsoft Word COM runtime and js-ctypes calls remain
untested.

## November 12, 2026 — ARM64 MSBuild OutputPath failure (fix prepared)

The tester selected **Release | ARM64** in Visual Studio 2022 Community and
the build failed at the MSBuild project-property validation stage, before
compiling `document.cpp`, with:

```text
Microsoft.Common.CurrentVersion.targets(843,5):
BaseOutputPath/OutputPath is not set for zoteroWinWordIntegration.vcxproj
Configuration='Release' Platform='ARM64'
Build: 0 succeeded, 1 failed (0.333 seconds)
```

Inspection of upstream `build/zoteroWinWordIntegration/zoteroWinWordIntegration.vcxproj`
confirmed an explicit `OutDir` and `IntDir` are defined for
`Release|Win32`, but no equivalent declarations exist for
`Release|ARM64`. This lack is consistent with the observed error.

Prepared **0004** to set only the ARM64 output and intermediate
directories, preserving the successful x64 and Win32 configurations:

```xml
<OutDir Condition="'$(Configuration)|$(Platform)'=='Release|ARM64'">$(SolutionDir)$(Platform)\$(Configuration)\</OutDir>
<IntDir Condition="'$(Configuration)|$(Platform)'=='Release|ARM64'">$(Platform)\$(Configuration)\</IntDir>
```

The user can set the same values in Visual Studio's project
**Properties > Configuration Properties > General**, selecting
**Configuration=Release, Platform=ARM64** (not All Configurations/Platforms).
The expected output path becomes
`build/zoteroWinWordIntegration/ARM64/Release/zoteroWinWordIntegration.dll`.

**Status: corrective patch prepared, not yet compiled/tested.** If a
subsequent error reports absent ARM64 tools/MFC libraries, add the
corresponding Visual Studio components. Do not reinstall the integration
or rerun the complete patch script over the intentionally dirty checkout.

## November 12, 2026 — ARM64 compiler toolset missing (MSB8020)

After setting the ARM64 output/intermediate paths, Visual Studio 2022
Release | ARM64 progressed past the MSBuild output configuration error.
The next error is:

```text
Microsoft.CppBuild.targets(463,5): error MSB8020
Cannot find build tools for v143 (Platform Toolset = 'v143').
Build: 0 succeeded, 1 failed (0.244 seconds).
```

Given the successful Release | Win32 and Release | x64 MSVC v143
builds, this points specifically to the optional **ARM64/ARM64EC
compiler toolset**, rather than the C++ sources. Install from
Visual Studio Installer > Modify > Individual components:
- MSVC v143 – VS 2022 C++ ARM64/ARM64EC build tools (Latest).
- C++ MFC for latest v143 build tools (ARM64/ARM64EC), because
  the project config specifies `UseOfMfc=Static`.
- Windows SDK if the installer reports the relevant dependency absent.

Confirmed official Microsoft Visual Studio 2022 Build Tools component IDs:
`Microsoft.VisualStudio.Component.VC.Tools.ARM64` and
`Microsoft.VisualStudio.Component.VC.MFC.ARM64`.

Do **not** retarget the project toolset or reinstall the Zotero plugin.
After modifying Visual Studio, retry Release | ARM64 and inspect the
generated DLL exports. The Win32 and x64 build/export successes remain valid.

## November 12, 2026 — ARM64 MFC requirement confirmed (MSB8041)

After the ARM64 v143 compiler/toolset installation, the Visual Studio GUI
build showed an unqualified failure. The developer prompt's explicit MSBuild
invocation identified the missing dependency:

```text
msbuild zoteroWinWordIntegration.vcxproj /t:Build /p:Configuration=Release /p:Platform=ARM64 /v:normal /nologo
Microsoft.CppBuild.targets(504,5): error MSB8041:
MFC libraries are required for this project.
Build: 0 warnings, 1 error, 0.14 sec.
```

The ARM64 v143 compiler is now detected; **C++ MFC for latest v143 build
tools (ARM64/ARM64EC)** must also be installed via **Visual Studio Installer
> Modify > Individual components > search MFC**. Zotero's project uses
`UseOfMfc=Static`. Microsoft's MSB8041 documentation confirms that these
libraries are not installed by default and must match the toolset and target
architecture. Do not retarget the solution or disable MFC to bypass the error.

Status: ARM64 compilation remains pending; x64 and Win32 build and PE export
checks have already passed. No test of the Word COM execution path yet.

## November 12, 2026 — ARM64 MFC toolset-version mismatch confirmed

After MFC v143 ARM64 installation, `MSB8041` persisted. Direct MSBuild
property evaluation and disk inspection revealed the cause:

```text
MFC_KeyFile = C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.42.34433\atlmfc\lib\ARM64\mfcs140.lib
VCToolsVersion = 14.42.34433
VCToolsInstallDir = ...\MSVC\14.42.34433\
PlatformShortName = ARM64
SpectreLibs = (empty)
```

However, `where /R "<VS>\VC\Tools\MSVC" mfcs140.lib` found ARM64
MFC library in **14.44.35207** and legacy **14.16.27023**, but not 14.42.
Therefore the ARM64 MFC component is installed and the failure is caused by
an obsolete/default `VCToolsVersion` selection. The v141 14.16 toolset must
not be used to compile this v143 project.

Safest next step: try nonpersistent MSBuild command-line override
`/p:VCToolsVersion=14.44.35207`. First check evaluated
`MFC_KeyFile` with `-getProperty`, then build if correct.

```cmd
msbuild "%USERPROFILE%\Downloads\zotero-word-for-windows-integration\build\zoteroWinWordIntegration\zoteroWinWordIntegration.vcxproj" /p:Configuration=Release /p:Platform=ARM64 /p:VCToolsVersion=14.44.35207 -getProperty:MFC_KeyFile,VCToolsVersion,VCToolsInstallDir
msbuild "%USERPROFILE%\Downloads\zotero-word-for-windows-integration\build\zoteroWinWordIntegration\zoteroWinWordIntegration.vcxproj" /t:Build /p:Configuration=Release /p:Platform=ARM64 /p:VCToolsVersion=14.44.35207 /v:normal /nologo
```

Microsoft Learn confirms the `VCToolsVersion` override and explicitly
documents how `MSB8041` derives `MFC_KeyFile` from that version and
architecture. Status: diagnosed, **ARM64 build with override not yet run**.
Do not add blind packages, copy MFC files between MSVC versions, retarget
to `v141`, or install experimental DLLs in production.

## November 13, 2026 — ARM64 Release native build PASS (MSVC 14.44.35207)

A full real MSBuild ARM64 Release compile/link succeeded after specifying the
installed toolset version whose ARM64 MFC libraries are present:

```cmd
msbuild "%USERPROFILE%\Downloads\zotero-word-for-windows-integration\build\zoteroWinWordIntegration\zoteroWinWordIntegration.vcxproj" /t:Build /p:Configuration=Release /p:Platform=ARM64 /p:VCToolsVersion=14.44.35207 /v:normal /nologo
```

Actual log: compiler `MSVC\14.44.35207\bin\HostX86\arm64\CL.exe`;
`link.exe /MACHINE:ARM64`; compiled `document.cpp`, `field.cpp`,
`utilities.cpp`; created
`build/zoteroWinWordIntegration/ARM64/Release/zoteroWinWordIntegration.dll`
plus its `.lib` and `.exp`; custom build step copied
`install/libzoteroWinWordIntegration_ARM64.dll` in the *source clone*.
Final MSBuild result **0 errors, 1 nonblocking C4018 warning**, elapsed
5.94 seconds.

This confirms all **three architectures build**: Win32, x64, ARM64.
Win32 and x64 exports have been verified, but ARM64 PE exports and machine
header were **not yet inspected**. They should be checked via:

```cmd
dumpbin /exports "%USERPROFILE%\Downloads\zotero-word-for-windows-integration\build\zoteroWinWordIntegration\ARM64\Release\zoteroWinWordIntegration.dll" | findstr /I "getMainStorySnapshot getMainStoryFieldRanges"
dumpbin /headers "%USERPROFILE%\Downloads\zotero-word-for-windows-integration\build\zoteroWinWordIntegration\ARM64\Release\zoteroWinWordIntegration.dll" | findstr /I "machine"
```

This is **compile/link success only**, not evidence of runtime Word COM
correctness or Zotero JS integration. No native DLL has been intentionally
installed into the user's active Zotero deployment as part of this test.

## November 13, 2026 — ARM64 PE export and machine header inspection PASS

The tester inspected the actual ARM64 Release DLL after the first
successful MSVC v143 (14.44.35207) cross-build.

```text
dumpbin /exports "...\ARM64\Release\zoteroWinWordIntegration.dll"
18   11 00006008 getMainStoryFieldRanges
19   12 00005DB0 getMainStorySnapshot

dumpbin /headers "...\ARM64\Release\zoteroWinWordIntegration.dll"
AA64 machine (ARM64)
```

**Result: all three official architectures are now compile/link PASS and
both new API names are present in each PE export table.** Specifically:
x64 exports both undecorated names; Win32 exports
`_getMainStoryFieldRanges@12` and `_getMainStorySnapshot@16`
(correct stdcall decorations); ARM64 exports both undecorated names and
the PE header confirms machine type AA64. No ARM64 *runtime* test was run.

### Runtime safety condition before live Word test

Despite both new API bodies being read-only, the **existing** Zotero
`getDocument()` function is *not side-effect-free*. It can modify Word
TrackRevisions, view/revisions display, and start a custom undo record.
Therefore smoke testing must use a disposable Word document in a
separate test instance with no active user documents. On success or error,
pair `getDocument()` with the appropriate `cleanup()`,
`complete()`, and `freeDocument()` calls, and close the disposable
document without saving unwanted changes. An isolated harness is
recommended; do not use a production document or replace an installed
Zotero DLL for this test.

The next stage is to validate returned text, absolute Word coordinates,
field exclusion spans and error handling *against real Word*, prior to
adding any mutating placeholder-conversion command or user-facing UI.

## November 13, 2026 — isolated Word COM native read-only smoke test prepared

The tester was provided a **standalone Windows Python script** named
`test_zotero_word_native_readonly.py` as a generated conversation attachment.
Its source has been syntax-checked (`python -m py_compile`), but is **not yet
executed on Windows**; the local machine's test result is pending.

Prerequisites: 64-bit Python, `pywin32`, Microsoft Word and the known-good
locally compiled x64 DLL at
`%USERPROFILE%\Downloads\zotero-word-for-windows-integration\build\zoteroWinWordIntegration\x64\Release\zoteroWinWordIntegration.dll`.

Safety constraints encoded in the script:
- Refuses to run if any existing `WINWORD.EXE` process is detected.
- Uses `DispatchEx('Word.Application')` for its own hidden test instance.
- Creates a disposable .docx in a temporary directory and closes it
  **without saving further changes** before removing that directory.
- Loads the experimental DLL with `ctypes.WinDLL`; does not install or copy
  any file into Zotero or Word templates.
- Reads `getMainStorySnapshot` and `getMainStoryFieldRanges`, releasing
  returned allocations through the native `freeData` export.
- Uses `cleanup()`, `complete()` and `freeDocument()` to mirror the
  existing Zotero native lifecycle; records that `getDocument()` itself
  can temporarily change document settings.
- Compares native text, start/end coordinates, and field [start,end)
  pairs with Word COM results **before and after** each native read.
- Performs a no-field test first and stops if the base snapshot disagrees;
  follows with a one-field test if the first check passes; logs precise
  differences and `offsets_reliable` separately.

Run by saving attachment in Downloads and invoking:
```cmd
py -3 "%USERPROFILE%\Downloads\test_zotero_word_native_readonly.py"
```

Need user-provided runtime output before declaring this test successful.
The test file was generated for the conversation; it is not part of the
upstream patch or a released, production-tested Zotero integration.

## November 13, 2026 — real Word runtime TEST A PASS; one-field oracle fixed

User executed first version of the isolated Windows `ctypes.WinDLL` +
`pywin32` harness using an already-built x64 DLL. The *real* Test A result:

```text
DLL x64 caricata: ...\x64\Release\zoteroWinWordIntegration.dll
[TEST A - no fields] PASS
  text_matches_word: True
  story_coordinates_match_word: True
  field_ranges_match_word: True
  document_content_unchanged: True
  offsets_reliable: True
  length_utf16: 50
  word_span_length: 50
```

The harness then stopped in Test B before calling the new native API for
that scenario:

```text
AttributeError: Item.Range
at word_state(): fields.Item(i).Range.Start
```

**Root cause: test harness bug, not native C++ failure.** Microsoft Word
`Field` objects expose `Code` and `Result` ranges, but not
`Field.Range` via this Word COM pywin32 interface. In the corrected,
conversation-delivered `test_zotero_word_native_readonly_v2.py`,
the expected field interval is calculated with the same contract as the
compiled native patch:

```python
field = fields.Item(i)
field_start = int(field.Code.Start) - 1
field_end = int(field.Result.End) + 1
```

A syntactic check with `python -m py_compile` and an isolated mock
of the Word COM objects passed. Actual Word Test B is still **pending**.
The V2 script is a conversation attachment; it is **not** part of
the published Zotero integration.

Before running the V2 script, close every `WINWORD.EXE` process after
saving work. Run:
```cmd
py -3 "%USERPROFILE%\Downloads\test_zotero_word_native_readonly_v2.py"
```

Record whether one-field `text_matches_word`,
`story_coordinates_match_word`, `field_ranges_match_word`,
and `document_content_unchanged` pass; separately record whether
`offsets_reliable` remains true in the presence of a Word field.
The test must not modify the production Zotero integration.

## November 13, 2026 — real Word runtime TEST A + TEST B PASS; global text offsets UNSAFE

The Windows user ran the improved `test_zotero_word_native_readonly_v2.py`
against the exact built x64 Zotero Word DLL, in an isolated Word instance
with all pre-existing `WINWORD.EXE` processes closed. Full verified output:

| Check | TEST A (no fields) | TEST B (one Word field) |
| --- | --- | --- |
| text_matches_word | True | True |
| story_coordinates_match_word | True | True |
| field_ranges_match_word | True | True |
| document_content_unchanged | True | True |
| offsets_reliable | True | **False** |
| length_utf16 | 50 | **70** |
| word_span_length | 50 | **103** |

In TEST B, `word_ranges = [[49, 102]]` and
`native_ranges = [[49, 102]]`: both the native field span and Word COM
agree exactly. There was no observed document content modification.
The test harness reports **PASS**, as designed, because it checks read
correctness and no content mutation, not whether global text offsets are
safe for edits.

**Critical boundary:** with an existing Word field, the full story's
`Range.Text` UTF-16 length was 70, but `Range.End-Range.Start` was 103.
The 33-position discrepancy proves that a global raw-text index must NOT
be added to `storyStart` to determine an edit location. The existing
`offsetsReliable=false` hard stop in `wordStoryPreflight.mjs` is
correct for the current representation; do not weaken or remove it.

**Next proof-of-concept (not yet run on Windows):** a new standalone V3
Python harness checks whether the gaps *outside* verified field intervals
have exact UTF-16 text lengths, and validates two marker locations before
and after an existing field against actual `Word.Range(start,end).Text`.
It also tests UTF-16 indexing with a non-BMP emoji. The V3 harness
refuses to treat any segment with a length mismatch as safe.

The field-free-segment strategy is tentative: even if V3 passes, the
native C++/js-ctypes bridge still needs an API returning independently
validated segment text and absolute Word coordinates; no safe
mutating conversion is authorized. Complex Word constructs (tables,
tracked changes, content controls, nested fields) need separate tests.
**The V3 script has passed Python syntax and isolated mock checks only,
not a Windows Word runtime test.**

## November 13, 2026 — live TEST C/D PASS; native verified segment patch 0005 prepared

The user ran `test_zotero_word_native_readonly_v3.py` successfully on a
disposable Microsoft Word document using the compiled x64 DLL. The full
real-world report shows **all four tests PASS** and no document content
changes.

Test C (field between two markers):
```text
text_matches_word: True
story_coordinates_match_word: True
field_ranges_match_word: True
document_content_unchanged: True
offsets_reliable: False
length_utf16: 79
word_span_length: 113
```

Test D (Word COM field-free segment mapping):
```json
{
  "field_count": 1,
  "segments": [
    {"start":0, "end":27, "word_span_length":27, "text_length_utf16":27, "offsets_reliable":true},
    {"start":82, "end":113, "word_span_length":31, "text_length_utf16":31, "offsets_reliable":true}
  ],
  "marker_positions": {
    "{AUTOCITE:BEFORE}": [[9,26]],
    "{AUTOCITE:AFTER}": [[90,106]]
  },
  "all_segments_reliable": true,
  "all_markers_unique": true,
  "pass": true,
  "document_content_unchanged": true
}
```

**Conclusion:** simple segments outside Word fields can be mapped reliably
when each span is individually read and validated. The global Word
snapshot remains unsafe (`offsets_reliable=false`) and this behavior
must not be disabled.

Prepared GitHub native patch:
`upstream-prep/patches/zotero-word-for-windows-integration/0005-verified-main-story-field-free-segment.patch`

It adds a read-only `getVerifiedMainStorySegment(doc,start,end,&text)`
C++ API and JS/ctypes wrapper:
- checks main-story bounds and a 16-million UTF-16-unit maximum;
- enumerates existing fields and **rejects overlap**;
- rejects internally invalid field geometry;
- duplicates a `CRange` and checks that Word preserves the requested
  absolute start/end;
- compares returned text UTF-16 length against the coordinate span;
- rejects embedded NUL and releases allocated text via `freeData()`.

The patch was validated against official sources with the existing three
native patches applied **in memory**, and added to the ordered clean-clone
patch script and CI applicability checks. It has **not yet compiled or run
on the user's Windows PC**.

For the *already modified* Windows source clone, apply patch 0005 only,
then recompile **Release | x64** and verify its new exported name:
```cmd
dumpbin /exports "%USERPROFILE%\Downloads\zotero-word-for-windows-integration\build\zoteroWinWordIntegration\x64\Release\zoteroWinWordIntegration.dll" | findstr /I "getVerifiedMainStorySegment"
```

The conversation-delivered `test_zotero_word_native_readonly_v4.py`
adds **TEST E**: verifies the new native API directly against Word COM
field-free ranges and explicitly checks that reading a protected field
is rejected. It still creates only a disposable test document. Its Python
syntax was checked, but real Windows test remains pending.

**Scope:** no citation mutation, Zotero field insertion, or production
plugin installation. Do not treat a successful V3 Python COM mapping
as direct evidence that the new native API has passed.

## November 13, 2026 — patch 0005 installer-script fix (pending Windows retry)

The tester tried the first `apply-autocite-segment-patch.ps1` script
against the already-modified source clone. The script aborted at its first
command:

```text
git.exe : error: patch failed: components/zoteroWinWordIntegration.mjs:114
at apply-autocite-segment-patch.ps1 line 31
git apply --reverse --check --ignore-whitespace ...
```

**Diagnosis:** the first script tried `git apply --reverse --check`
on patch 0005 **before** verifying it was applied. If the patch is
not applied, the reverse check is expected to fail. With PowerShell
`$ErrorActionPreference='Stop'`, Git's stderr was surfaced as a
terminating `NativeCommandError` before the forward apply check.
The error does **not** establish that the forward patch is incompatible,
and the script did not reach the source-mutating operation.

A corrected conversation attachment
`apply-autocite-segment-patch-v2.ps1` was created. It checks the marker
in all three expected source files, refuses partially present edits,
captures Git nonzero exit codes/stderr safely, runs forward
`git apply --check` before touching source files, and validates that the
patch is present after application. The Windows result is **pending**.

Retry using the corrected script from the Downloads directory:

```cmd
powershell -NoProfile -ExecutionPolicy Bypass -File "%USERPROFILE%\Downloads\apply-autocite-segment-patch-v2.ps1"
```

**Do not run the V4 Python live test until the 0005 patch is successfully
applied, the Release x64 DLL has been rebuilt, and the new export is
verified with `dumpbin`.**

## November 13, 2026 — patch 0005 applied successfully in source clone

User ran the corrected Windows PowerShell `apply-autocite-segment-patch-v2.ps1` against the existing Zotero Word source clone. Actual output:

```text
[OK] Controllo preliminare git apply --check superato.
[OK] Patch 0005 applicata ai sorgenti C++ e JavaScript del clone.
[OK] Verifica post-applicazione e git diff --check superate.
 M build/zoteroWinWordIntegration/document.cpp
 M build/zoteroWinWordIntegration/zoteroWinWordIntegration.h
 M build/zoteroWinWordIntegration/zoteroWinWordIntegration.vcxproj
 M components/zoteroWinWordIntegration.mjs
 M install/libzoteroWinWordIntegration.dll
 M install/libzoteroWinWordIntegration_ARM64.dll
 M install/libzoteroWinWordIntegration_x64.dll
?? autocite_zotero/
```

The four modified source/project files are expected from staged patches
0001–0005; `install/*.dll` binaries in this **source checkout** had been
changed by prior successful local build copy steps. The unrelated/untracked
`autocite_zotero/` directory should be preserved, not removed or committed
automatically.

**Next:** use Visual Studio 2022 with `Release | x64` and rebuild the
patched native project, verify `getVerifiedMainStorySegment` in the
generated PE export table, then run `test_zotero_word_native_readonly_v4.py`
with every `WINWORD.EXE` process closed. The script was inspected: its
`main()` does invoke `probe_native_segment_api()` after Test D and expects
five reports. **The new API's live Word Test E remains unverified.**

Do not install or swap the generated DLL into the production Zotero
application.

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
