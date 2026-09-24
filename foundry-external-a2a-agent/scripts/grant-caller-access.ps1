[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$PrincipalObjectId,

    [ValidateSet("User", "Group", "ServicePrincipal")]
    [string]$PrincipalType = "Group"
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\common.ps1"

$projectId = Get-AzdValue "AZURE_AI_PROJECT_ID"
if (-not $projectId) {
    throw "AZURE_AI_PROJECT_ID is missing from the azd environment."
}
$foundryAgentConsumerRole = "eed3b665-ab3a-47b6-8f48-c9382fb1dad6"
az role assignment create `
    --assignee-object-id $PrincipalObjectId `
    --assignee-principal-type $PrincipalType `
    --role $foundryAgentConsumerRole `
    --scope $projectId `
    --output none
if ($LASTEXITCODE -ne 0) {
    throw "Unable to grant Foundry Agent Consumer."
}
Write-Host "Granted Foundry Agent Consumer on the calling project."

