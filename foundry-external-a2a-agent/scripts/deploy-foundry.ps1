[CmdletBinding()]
param(
    [string]$Location = "swedencentral",
    [string]$ModelDeployment = "gpt-5.4-mini"
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\common.ps1"

Set-AzdValue "AZURE_LOCATION" $Location
Set-AzdValue "AZURE_AI_MODEL_DEPLOYMENT_NAME" $ModelDeployment
azd up --no-prompt
if ($LASTEXITCODE -ne 0) {
    throw "Foundry provisioning failed."
}

$endpoint = Get-FoundryProjectEndpoint
Set-AzdValue "FOUNDRY_PROJECT_ENDPOINT" $endpoint
Write-Host "Foundry project endpoint: $endpoint"

