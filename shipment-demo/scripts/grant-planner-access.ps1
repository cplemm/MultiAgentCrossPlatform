$ErrorActionPreference = "Stop"
. "$PSScriptRoot\common.ps1"

$projectId = Get-AzdValue "AZURE_AI_PROJECT_ID"
$projectEndpoint = Get-FoundryProjectEndpoint
if (-not $projectId) {
    throw "AZURE_AI_PROJECT_ID is missing from the azd environment."
}

$raw = (azd auth token --scope "https://ai.azure.com/.default" |
    Out-String).Trim()
$headers = @{
    Authorization = [string]::Concat("Bearer", [char]32, $raw)
}
$orchestrator = Invoke-RestMethod `
    -Uri (
        "$projectEndpoint/agents/shipment-recovery-orchestrator" +
        "?api-version=v1"
    ) `
    -Headers $headers
$principalId = $orchestrator.instance_identity.principal_id
if (-not $principalId) {
    throw "The orchestrator agent identity could not be resolved."
}

$plannerScope = "$projectId/agents/shipment-recovery-planner"
$roleId = "eed3b665-ab3a-47b6-8f48-c9382fb1dad6"
$existing = az role assignment list `
    --assignee-object-id $principalId `
    --scope $plannerScope `
    --query "[?roleDefinitionId && ends_with(roleDefinitionId, '$roleId')].id | [0]" `
    --output tsv
if (-not $existing) {
    az role assignment create `
        --assignee-object-id $principalId `
        --assignee-principal-type ServicePrincipal `
        --role $roleId `
        --scope $plannerScope `
        --output none
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to grant Foundry Agent Consumer on the planner."
    }
}
Write-Host (
    "Granted orchestrator identity Foundry Agent Consumer on " +
    "shipment-recovery-planner."
)
