[CmdletBinding()]
param(
    [string]$AgentName = "external-profile-orchestrator"
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\common.ps1"

$projectEndpoint = Get-FoundryProjectEndpoint
$connectionName = Get-AzdValue "EXTERNAL_A2A_CONNECTION_NAME"
$model = Get-AzdValue "AZURE_AI_MODEL_DEPLOYMENT_NAME"
if (-not $connectionName) {
    $connectionName = "external-graph-profile-oauth"
}
if (-not $model) {
    $model = "gpt-5.4-mini"
}

$python = Join-Path (Split-Path -Parent $PSScriptRoot) `
    ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Run scripts\install-dev.ps1 before creating the caller agent."
}

$env:FOUNDRY_PROJECT_ENDPOINT = $projectEndpoint
$env:EXTERNAL_A2A_CONNECTION_NAME = $connectionName
$env:EXTERNAL_A2A_BASE_URL = Get-AzdValue "EXTERNAL_A2A_BASE_URL"
$env:AZURE_AI_MODEL_DEPLOYMENT_NAME = $model
$env:FOUNDRY_CALLER_AGENT_NAME = $AgentName
& $python "$PSScriptRoot\create-caller-agent.py"
if ($LASTEXITCODE -ne 0) {
    throw "Unable to create the Foundry caller agent."
}

Set-AzdValue "FOUNDRY_CALLER_AGENT_NAME" $AgentName
Write-Host "Foundry caller agent is ready: $AgentName"
