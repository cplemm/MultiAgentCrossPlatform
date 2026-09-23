[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$PrincipalObjectId,

    [ValidateSet("User", "Group", "ServicePrincipal")]
    [string]$PrincipalType = "Group",

    [Parameter(Mandatory)]
    [string]$AgentResourceId
)

$ErrorActionPreference = "Stop"
$foundryAgentConsumerRole = "eed3b665-ab3a-47b6-8f48-c9382fb1dad6"

az role assignment create `
    --assignee-object-id $PrincipalObjectId `
    --assignee-principal-type $PrincipalType `
    --role $foundryAgentConsumerRole `
    --scope $AgentResourceId `
    --output none

if ($LASTEXITCODE -ne 0) {
    throw "Unable to grant Foundry Agent Consumer."
}

Write-Host "Granted Foundry Agent Consumer to $PrincipalObjectId."

