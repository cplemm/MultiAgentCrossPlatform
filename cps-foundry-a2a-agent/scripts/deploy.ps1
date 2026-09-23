[CmdletBinding()]
param(
    [string]$AgentName = "market-research-agent",

    [string]$ModelDeployment = "gpt-5.4-mini"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

azd env get-values *> $null
if ($LASTEXITCODE -ne 0) {
    throw "No active azd environment. Run: azd env new cps-a2a-demo"
}

azd env set AZURE_AI_MODEL_DEPLOYMENT_NAME $ModelDeployment | Out-Null
azd up --no-prompt

if ($LASTEXITCODE -ne 0) {
    throw "azd up failed."
}

$projectEndpoint = azd env get-value AZURE_AI_PROJECT_ENDPOINT
if (-not $projectEndpoint) {
    $projectEndpoint = azd env get-value AZURE_AIPROJECT_ENDPOINT
}
if (-not $projectEndpoint) {
    throw "The deployed project endpoint was not found in the azd environment."
}

$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    python -m venv (Join-Path $repoRoot ".venv")
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to create the Python virtual environment."
    }
}

& $venvPython -m pip install --requirement (Join-Path $repoRoot "requirements.txt")
if ($LASTEXITCODE -ne 0) {
    throw "Unable to install the Prompt Agent dependencies."
}

$env:FOUNDRY_PROJECT_ENDPOINT = $projectEndpoint
$env:AZURE_AI_MODEL_DEPLOYMENT_NAME = $ModelDeployment
$env:FOUNDRY_AGENT_NAME = $AgentName

& $venvPython (Join-Path $PSScriptRoot "create-prompt-agent.py")
if ($LASTEXITCODE -ne 0) {
    throw "Prompt Agent creation failed."
}

& "$PSScriptRoot\enable-a2a.ps1" `
    -ProjectEndpoint $projectEndpoint `
    -AgentName $AgentName
