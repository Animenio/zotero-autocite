# SPDX-License-Identifier: AGPL-3.0-or-later
# Check or apply both READ-ONLY Zotero Word source patches.
# This script does NOT install or modify Word/Zotero applications.
param(
    [Parameter(Mandatory = $true)]
    [string]$ZoteroWordRepository,
    [switch]$Apply
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path -LiteralPath $ZoteroWordRepository).Path
$patchDir = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\patches\zotero-word-for-windows-integration')).Path
$patchNames = @(
    '0001-main-story-readonly-snapshot.patch',
    '0002-main-story-field-ranges.patch'
)

foreach ($name in @(
    'build\zoteroWinWordIntegration\document.cpp',
    'build\zoteroWinWordIntegration\zoteroWinWordIntegration.h',
    'components\zoteroWinWordIntegration.mjs'
)) {
    if (-not (Test-Path -LiteralPath (Join-Path $repo $name))) {
        throw "Questa non sembra la repository Zotero Word ufficiale: manca $name"
    }
}

# ZIP extraction or editors on Windows can give .patch files CRLF endings.
# Normalize temporary COPIES to LF so Git never interprets their CR as trailing spaces.
$stageDir = Join-Path ([IO.Path]::GetTempPath()) ('autocite-patches-' + [guid]::NewGuid().ToString('N'))
[void](New-Item -Path $stageDir -ItemType Directory)
$staged = @()
try {
    $utf8 = [System.Text.UTF8Encoding]::new($false)
    foreach ($name in $patchNames) {
        $source = Join-Path $patchDir $name
        if (-not (Test-Path -LiteralPath $source)) { throw "Patch mancante: $source" }
        $destination = Join-Path $stageDir $name
        $text = [IO.File]::ReadAllText($source)
        $crlf = [string][char]13 + [string][char]10
        $lf = [string][char]10
        $text = $text.Replace($crlf, $lf).Replace([string][char]13, $lf)
        [IO.File]::WriteAllText($destination, $text, $utf8)
        $staged += $destination
    }

    Push-Location -LiteralPath $repo
    try {
        $inside = & git rev-parse --is-inside-work-tree
        if ($LASTEXITCODE -ne 0 -or "$inside".Trim() -ne 'true') {
            throw 'La cartella indicata non e una repository Git.'
        }
        $dirty = & git status --porcelain
        if ($LASTEXITCODE -ne 0 -or -not [string]::IsNullOrWhiteSpace(($dirty -join [Environment]::NewLine))) {
            throw 'Il clone Git contiene gia modifiche: utilizzare un clone pulito.'
        }

        # Verify the entire patch sequence in an independent temporary worktree.
        $scratch = Join-Path ([IO.Path]::GetTempPath()) ('autocite-word-check-' + [guid]::NewGuid().ToString('N'))
        & git worktree add --quiet --detach $scratch HEAD
        if ($LASTEXITCODE -ne 0) { throw 'Creazione del worktree di controllo fallita.' }
        try {
            Push-Location -LiteralPath $scratch
            try {
                foreach ($p in $staged) {
                    & git -c core.whitespace=cr-at-eol apply --check --ignore-whitespace $p
                    if ($LASTEXITCODE -ne 0) { throw "Patch incompatibile: $p" }
                    & git -c core.whitespace=cr-at-eol apply --ignore-whitespace $p
                    if ($LASTEXITCODE -ne 0) { throw "Applicazione di prova fallita: $p" }
                }
                & git -c core.whitespace=cr-at-eol diff --check
                if ($LASTEXITCODE -ne 0) { throw 'git diff --check non superato.' }
            }
            finally { Pop-Location }
        }
        finally {
            & git worktree remove --force $scratch
            if ($LASTEXITCODE -ne 0) {
                Write-Warning "Rimuovere il worktree temporaneo: $scratch"
            }
        }

        Write-Host 'ENTRAMBE LE PATCH COMPATIBILI: clone originale invariato.'
        if (-not $Apply) {
            Write-Host 'Per applicarle al clone, ripeti aggiungendo -Apply.'
            return
        }

        $applied = @()
        try {
            foreach ($p in $staged) {
                & git -c core.whitespace=cr-at-eol apply --check --ignore-whitespace $p
                if ($LASTEXITCODE -ne 0) { throw "Verifica finale fallita: $p" }
                & git -c core.whitespace=cr-at-eol apply --ignore-whitespace $p
                if ($LASTEXITCODE -ne 0) { throw "Applicazione fallita: $p" }
                $applied += $p
            }
            & git -c core.whitespace=cr-at-eol diff --check
            if ($LASTEXITCODE -ne 0) { throw 'Whitespace non valido nel clone modificato.' }
        }
        catch {
            for ($i = $applied.Count - 1; $i -ge 0; $i--) {
                & git -c core.whitespace=cr-at-eol apply --reverse --ignore-whitespace $applied[$i]
                if ($LASTEXITCODE -ne 0) {
                    Write-Warning ('Rollback non riuscito per ' + $applied[$i])
                }
            }
            throw
        }
        Write-Host 'PATCH APPLICATE SOLO AL CLONE DEI SORGENTI (non a Word/Zotero).'
        & git status --short
    }
    finally { Pop-Location }
}
finally {
    Remove-Item -LiteralPath $stageDir -Recurse -Force -ErrorAction SilentlyContinue
}
