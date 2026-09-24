$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$venv = Join-Path $root ".venv"
if (-not (Test-Path $venv)) {
    python -m venv $venv
}
$python = Join-Path $venv "Scripts\python.exe"
Write-Host "Restoring Python packages into $venv..."
& $python -m pip install `
    -r "$root\src\external-agent\requirements-dev.txt" `
    "azure-ai-projects>=2.7.0" `
    "azure-identity>=1.25.0" `
    "PyYAML>=6.0"
if ($LASTEXITCODE -ne 0) {
    throw "Dependency installation failed."
}
Write-Host "Development dependencies installed in $venv"
