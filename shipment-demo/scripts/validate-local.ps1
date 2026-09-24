$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$orchestrator = Join-Path $root "src\orchestrator"

Push-Location $orchestrator
try {
    uv sync --group dev
    uv run pytest --quiet
    uv run python -m compileall -q .
} finally {
    Pop-Location
}

$planner = Join-Path $root "src\recovery-planner"
$env:PYTHONPATH = $planner
& "$orchestrator\.venv\Scripts\python.exe" `
    -m pytest "$planner\tests" --quiet
if ($LASTEXITCODE -ne 0) {
    throw "Recovery Planner Hosted Agent tests failed."
}

$componentVenv = Join-Path $root ".component-venv"
if (-not (Test-Path $componentVenv)) {
    uv venv --python 3.13 $componentVenv
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to create the Python 3.13 component environment."
    }
}
$componentPython = Join-Path $componentVenv "Scripts\python.exe"
uv pip install `
    --python $componentPython `
    --index-url https://packagefeedproxy.microsoft.io/pypi/simple `
    -r "$root\src\policy-bridge\requirements-dev.txt" `
    -r "$root\src\supplier-agent\requirements.txt"
if ($LASTEXITCODE -ne 0) {
    throw "Component dependency installation failed."
}

$env:PYTHONPATH = "$root\src\policy-bridge"
& $componentPython -m pytest "$root\src\policy-bridge\tests" --quiet
if ($LASTEXITCODE -ne 0) {
    throw "Policy bridge tests failed."
}

Push-Location "$root\src\supplier-agent"
try {
    $env:PYTHONPATH = "$root\src\supplier-agent"
    & $componentPython -m pytest tests --quiet
    if ($LASTEXITCODE -ne 0) {
        throw "Supplier A2A tests failed."
    }
} finally {
    Pop-Location
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
