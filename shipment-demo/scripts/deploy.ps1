[CmdletBinding()]
param(
    [string]$SubscriptionId = "39b4a175-7439-4dc8-b6a3-450d620159d2",
    [string]$Location = "swedencentral",
    [string]$ResourceGroup = "rg-shipment-recovery-demo",
    [Parameter(Mandatory)]
    [string]$CopilotStudioEnvironmentId,
    [Parameter(Mandatory)]
    [string]$CopilotStudioSchemaName,
    [switch]$SkipAdminConsent
)

$ErrorActionPreference = "Stop"
$env:AZURE_DEV_USER_AGENT = "microsoft_foundry_skill"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

az account set --subscription $SubscriptionId
if ($LASTEXITCODE -ne 0) {
    throw "Unable to select subscription $SubscriptionId."
}
azd auth login --check-status *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Run azd auth login before deployment."
}

. "$PSScriptRoot\common.ps1"
Set-AzdValue "AZURE_SUBSCRIPTION_ID" $SubscriptionId
Set-AzdValue "AZURE_LOCATION" $Location
Set-AzdValue "AZURE_RESOURCE_GROUP" $ResourceGroup
Set-AzdValue "AZURE_AI_MODEL_DEPLOYMENT_NAME" "gpt-5.4-mini"
Set-AzdValue "COPILOT_STUDIO_ENVIRONMENT_ID" $CopilotStudioEnvironmentId
Set-AzdValue "COPILOT_STUDIO_SCHEMA_NAME" $CopilotStudioSchemaName

& "$PSScriptRoot\create-policy-app.ps1" `
    -SkipAdminConsent:$SkipAdminConsent
& "$PSScriptRoot\deploy-components.ps1" `
    -ResourceGroup $ResourceGroup `
    -Location $Location

azd up --no-prompt
if ($LASTEXITCODE -ne 0) {
    throw "Foundry provisioning or hosted-agent deployment failed."
}
& "$PSScriptRoot\grant-planner-access.ps1"
& "$PSScriptRoot\register-foundry-redirect.ps1"

Write-Host ""
Write-Host "Deployment complete."
Write-Host "Authorize the policy bridge connection on first use, then retry."
Write-Host "Publish the hosted agent from Foundry to enable Teams/M365 Activity."
