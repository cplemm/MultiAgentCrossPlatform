$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Run scripts\install-dev.ps1 first."
}

$env:PYTHONPATH = Join-Path $root "src\external-agent"
& $python -m pytest "$root\src\external-agent\tests" --quiet
if ($LASTEXITCODE -ne 0) {
    throw "Unit tests failed."
}

& $python -m compileall -q "$root\src\external-agent" "$root\scripts"
if ($LASTEXITCODE -ne 0) {
    throw "Python syntax validation failed."
}

$parseErrors = @()
Get-ChildItem "$root\scripts" -Filter "*.ps1" | ForEach-Object {
    $tokens = $null
    $errors = $null
    [System.Management.Automation.Language.Parser]::ParseFile(
        $_.FullName,
        [ref]$tokens,
        [ref]$errors
    ) | Out-Null
    $parseErrors += $errors
}
if ($parseErrors.Count -gt 0) {
    $parseErrors | Format-List
    throw "PowerShell parser validation failed."
}
Write-Host "Local validation passed."

