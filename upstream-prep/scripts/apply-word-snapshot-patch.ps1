# SPDX-License-Identifier: AGPL-3.0-or-later
# Apply two READ-ONLY Word snapshot patches to a CLEAN standalone Zotero
# Word for Windows checkout; never install or update Word/Zotero.
param(
	[Parameter(Mandatory = $true)]
	[string]$ZoteroWordRepository,
	[switch]$Apply
)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path -LiteralPath $ZoteroWordRepository).Path
$patchDir = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\patches\zotero-word-for-windows-integration')).Path
$patches = @(
	(Join-Path $patchDir '0001-main-story-readonly-snapshot.patch'),
	(Join-Path $patchDir '0002-main-story-field-ranges.patch')
)
foreach ($p in $patches) {
	if (-not (Test-Path -LiteralPath $p)) { throw "Patch mancante: $p" }
}
foreach ($name in @(
	'build\zoteroWinWordIntegration\document.cpp',
	'build\zoteroWinWordIntegration\zoteroWinWordIntegration.h',
	'components\zoteroWinWordIntegration.mjs'
)) {
	if (-not (Test-Path -LiteralPath (Join-Path $repo $name))) {
		throw "Repository Zotero Word non riconosciuta: manca $name"
	}
}
Push-Location -LiteralPath $repo
try {
	$inside = & git rev-parse --is-inside-work-tree
	if ($LASTEXITCODE -ne 0 -or "$inside".Trim() -ne 'true') {
		throw 'La cartella indicata non è una repository Git.'
	}
	$dirty = & git status --porcelain
	if ($LASTEXITCODE -ne 0 -or -not [string]::IsNullOrWhiteSpace(($dirty -join [Environment]::NewLine))) {
		throw 'La copia Git contiene modifiche: usare un clone pulito.'
	}

	# Disposable Git worktree checks both patches without editing target.
	$temp = Join-Path ([IO.Path]::GetTempPath()) ("autocite-word-check-" + [guid]::NewGuid().ToString('N'))
	& git worktree add --quiet --detach $temp HEAD
	if ($LASTEXITCODE -ne 0) { throw 'Impossibile creare il worktree di controllo.' }
	try {
		Push-Location -LiteralPath $temp
		try {
			foreach ($p in $patches) {
				& git apply --check --ignore-whitespace $p
				if ($LASTEXITCODE -ne 0) { throw "Patch incompatibile: $p" }
				& git apply --ignore-whitespace $p
				if ($LASTEXITCODE -ne 0) { throw "Applicazione di prova fallita: $p" }
			}
			& git diff --check
			if ($LASTEXITCODE -ne 0) { throw 'git diff --check non superato.' }
		}
		finally { Pop-Location }
	}
	finally {
		& git worktree remove --force $temp
		if ($LASTEXITCODE -ne 0) {
			Write-Warning "Rimuovere manualmente il worktree temporaneo: $temp"
		}
	}
	Write-Host 'Entrambe le patch sono compatibili; checkout principale invariato.'
	if (-not $Apply) {
		Write-Host 'Per applicare le patch al clone, ripetere con -Apply.'
		return
	}
	$applied = @()
	try {
		foreach ($p in $patches) {
			& git apply --check --ignore-whitespace $p
			if ($LASTEXITCODE -ne 0) { throw "Verifica finale fallita: $p" }
			& git apply --ignore-whitespace $p
			if ($LASTEXITCODE -ne 0) { throw "Applicazione fallita: $p" }
			$applied += $p
		}
		& git diff --check
		if ($LASTEXITCODE -ne 0) { throw 'Whitespace non valido.' }
	}
	catch {
		for ($i = $applied.Count - 1; $i -ge 0; $i--) {
			& git apply --reverse --ignore-whitespace $applied[$i]
		}
		throw
	}
	Write-Host 'Patch applicate SOLO al clone dei sorgenti. Nessun plugin Word installato.'
	& git status --short
}
finally {
	Pop-Location
}
