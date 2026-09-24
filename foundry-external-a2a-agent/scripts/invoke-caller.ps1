[CmdletBinding()]
param(
    [string]$InputText = "Who am I? Verify my delegated identity.",
    [string]$PreviousResponseId
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\common.ps1"

$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
$env:FOUNDRY_PROJECT_ENDPOINT = Get-FoundryProjectEndpoint
$env:FOUNDRY_CALLER_AGENT_NAME = Get-AzdValue "FOUNDRY_CALLER_AGENT_NAME"

$arguments = @(
    "$PSScriptRoot\invoke-caller.py"
    "--input"
    $InputText
)
if ($PreviousResponseId) {
    $arguments += @("--previous-response-id", $PreviousResponseId)
}
& $python @arguments
if ($LASTEXITCODE -ne 0) {
    throw "Foundry caller invocation failed."
}

