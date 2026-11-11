# SPDX-License-Identifier: AGPL-3.0-or-later
# Applies ONLY the read-only Word main-story snapshot patch to a CLEAN
# standalone Zotero Word for Windows source checkout. Does NOT install Word code.
param(
	[Parameter(Mandatory = $true)]
	[string]$ZoteroWordRepository,
	[switch]$Apply
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path -LiteralPath $ZoteroWordRepository).Path
$patch = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\patches\zotero-word-for-windows-integration\0001-main-story-readonly-snapshot.patch')).Path

$requiredFiles = @(
	'build\zoteroWinWordIntegration\document.cpp',
	'build\zoteroWinWordIntegration\zoteroWinWordIntegration.h',
	'components\zoteroWinWordIntegration.mjs'
)
foreach ($name in $requiredFiles) {
	if (-not (Test-Path -LiteralPath (Join-Path $repo $name))) {
		throw "Questa non sembra essere la repository Zotero Word ufficiale: manca $name"
	}
}

Push-Location -LiteralPath $repo
try {
	$inside = (& git rev-parse --is-inside-work-tree 2>&1)
	if ($LASTEXITCODE -ne 0 -or "$inside".Trim() -ne 'true') {
		throw 'La cartella indicata non è una repository Git.'
	}
	$dirty = & git status --porcelain
	if ($LASTEXITCODE -ne 0 -or @($dirty).Count -gt 0) {
		throw 'Working tree non pulito: salva o annulla le modifiche prima di applicare la patch.'
	}
	& git apply --check --ignore-space-at-eol $patch
	if ($LASTEXITCODE -ne 0) {
		throw 'Patch incompatibile con questi sorgenti: non è stata applicata.'
	}
	if (-not $Apply) {
		Write-Host 'PATCH COMPATIBILE: verifica completata in sola lettura.'
		Write-Host 'Per applicare, ripeti aggiungendo -Apply.'
		return
	}
	& git apply --ignore-space-at-eol $patch
	if ($LASTEXITCODE -ne 0) {
		throw 'git apply ha restituito un errore: controlla git status.'
	}
	& git diff --check
	if ($LASTEXITCODE -ne 0) {
		throw 'git diff --check segnala problemi di whitespace.'
	}
	Write-Host 'PATCH APPLICATA alla copia dei sorgenti. Nessun plugin Word installato o sostituito.'
	& git status --short
}
finally {
	Pop-Location
}
