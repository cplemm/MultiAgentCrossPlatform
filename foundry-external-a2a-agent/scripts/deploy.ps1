[CmdletBinding()]
param(
    [string]$SubscriptionId = "39b4a175-7439-4dc8-b6a3-450d620159d2",
    [string]$Location = "swedencentral",
    [string]$EnvironmentName = "external-a2a-obo-demo",
    [string]$ResourceGroup = "rg-foundry-external-a2a-agent",
    [switch]$SkipAdminConsent
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "Foundry external A2A OBO demo deployment"
Write-Host "Subscription: $SubscriptionId"
Write-Host "Region:       $Location"
Write-Host "Environment:  $EnvironmentName"
Write-Host "Resource group: $ResourceGroup"
Write-Host "Expected duration: approximately 10-20 minutes."
Write-Host ""

Write-Host "[1/9] Checking Azure CLI context..."
$currentSubscription = az account show --query id --output tsv
if ($LASTEXITCODE -ne 0 -or -not $currentSubscription) {
    throw "Azure CLI sign-in check failed. Run az login and retry."
}
if ($currentSubscription -ne $SubscriptionId) {
    Write-Host "Selecting subscription $SubscriptionId..."
    az account set --subscription $SubscriptionId
    if ($LASTEXITCODE -ne 0) {
        throw "Azure subscription selection failed."
    }
} else {
    Write-Host "Azure CLI already uses the requested subscription."
}
Write-Host "Checking Azure Developer CLI authentication..."
azd auth login --check-status *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Run azd auth login before deployment."
}

Write-Host "Checking azd environment..."
$environments = @(
    azd env list --output json |
        ConvertFrom-Json
)
if ($LASTEXITCODE -ne 0) {
    throw "Unable to list azd environments."
}
$matchingEnvironment = @(
    $environments |
        Where-Object { $_.Name -eq $EnvironmentName }
) | Select-Object -First 1

if ($matchingEnvironment) {
    Write-Host "Selecting existing azd environment '$EnvironmentName'..."
    azd env select $EnvironmentName
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to select azd environment $EnvironmentName."
    }
} else {
    Write-Host "Creating azd environment '$EnvironmentName'..."
    azd env new $EnvironmentName --no-prompt
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to create azd environment $EnvironmentName."
    }
}

# Force both the Foundry provider and the Container Apps deployment to use the
# same resource group. Without this value, a fresh azd environment derives
# rg-$EnvironmentName while the external-agent script uses its own default.
azd env set AZURE_SUBSCRIPTION_ID $SubscriptionId | Out-Null
azd env set AZURE_LOCATION $Location | Out-Null
azd env set AZURE_RESOURCE_GROUP $ResourceGroup | Out-Null

Write-Host "[2/9] Installing development dependencies..."
Write-Host "      This can be quiet for one or two minutes."
& "$PSScriptRoot\install-dev.ps1"

Write-Host "[3/9] Running local validation..."
& "$PSScriptRoot\validate-local.ps1"

Write-Host "[4/9] Creating/updating Entra applications and consent..."
& "$PSScriptRoot\create-entra-apps.ps1" `
    -SkipAdminConsent:$SkipAdminConsent

Write-Host "[5/9] Building and deploying the external Container App..."
Write-Host "      The no-log ACR cloud build can be quiet for several minutes."
& "$PSScriptRoot\deploy-external-agent.ps1" `
    -SubscriptionId $SubscriptionId `
    -Location $Location `
    -ResourceGroup $ResourceGroup

Write-Host "[6/9] Provisioning the Foundry project and model..."
& "$PSScriptRoot\deploy-foundry.ps1" -Location $Location

Write-Host "[7/9] Creating the Foundry OAuth credential connection..."
& "$PSScriptRoot\create-foundry-connection.ps1"

Write-Host "[8/9] Creating the Foundry Prompt Agent caller..."
& "$PSScriptRoot\create-caller-agent.ps1"

Write-Host "[9/9] Running the delegated A2A and Graph OBO smoke test..."
& "$PSScriptRoot\smoke-test-external.ps1"

. "$PSScriptRoot\common.ps1"
$projectEndpoint = Get-FoundryProjectEndpoint
$caller = Get-AzdValue "FOUNDRY_CALLER_AGENT_NAME"
Write-Host ""
Write-Host "Deployment complete."
Write-Host "External A2A endpoint: $(Get-AzdValue 'EXTERNAL_A2A_BASE_URL')"
Write-Host "Foundry caller agent: $caller"
Write-Host (
    "Playground: $projectEndpoint/agents/$caller"
)
Write-Host ""
Write-Host "Open the caller in Foundry and ask: Who am I?"
Write-Host "Complete the OAuth consent link, then ask again."
if ($SkipAdminConsent) {
    Write-Warning (
        "Tenant-wide consent was skipped. This deployment is authorized only " +
        "for the user who ran the deployment."
    )
}
