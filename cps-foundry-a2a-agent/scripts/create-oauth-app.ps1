[CmdletBinding()]
param(
    [string]$DisplayName = "CPS to Foundry A2A",

    [switch]$GrantAdminConsent
)

$ErrorActionPreference = "Stop"

$foundryResourceAppId = "18a66f5f-dbdf-4c17-9dd7-1634712a9cbe"
$foundryUserImpersonationScope = "1a7925b5-f871-417a-9b8b-303f9f29fa10"

$app = az ad app create `
    --display-name $DisplayName `
    --sign-in-audience AzureADMyOrg `
    --output json | ConvertFrom-Json

if ($LASTEXITCODE -ne 0 -or -not $app.appId) {
    throw "Unable to create the Entra application."
}

az ad sp create --id $app.appId --output none
if ($LASTEXITCODE -ne 0) {
    throw "Unable to create the service principal."
}

az ad app permission add `
    --id $app.appId `
    --api $foundryResourceAppId `
    --api-permissions "$foundryUserImpersonationScope=Scope" `
    --output none

if ($LASTEXITCODE -ne 0) {
    throw "Unable to add the Foundry delegated permission."
}

if ($GrantAdminConsent) {
    az ad app permission admin-consent --id $app.appId --output none
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to grant admin consent."
    }
}

$credential = az ad app credential reset `
    --id $app.appId `
    --append `
    --display-name "cps-a2a" `
    --years 1 `
    --output json | ConvertFrom-Json

if ($LASTEXITCODE -ne 0 -or -not $credential.password) {
    throw "Unable to create the OAuth client credential."
}

Write-Host ""
Write-Host "OAuth application created."
Write-Host "Client ID: $($app.appId)"
Write-Host "Client secret: $($credential.password)"
Write-Host ""
Write-Warning "The client secret is shown only once. Store it securely."

if (-not $GrantAdminConsent) {
    Write-Host "An Entra administrator must run:"
    Write-Host "az ad app permission admin-consent --id $($app.appId)"
}

