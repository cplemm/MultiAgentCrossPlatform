[CmdletBinding()]
param(
    [string]$DisplayName = "Shipment Purchasing Policy Bridge",
    [switch]$SkipAdminConsent
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\common.ps1"

$tenantId = az account show --query tenantId --output tsv
if (-not $tenantId) {
    throw "Run az login before creating the policy bridge application."
}

$clientId = Get-AzdValue "POLICY_BRIDGE_CLIENT_ID"
if (-not $clientId) {
    $app = az ad app create `
        --display-name $DisplayName `
        --sign-in-audience AzureADMyOrg `
        --output json | ConvertFrom-Json
    $clientId = $app.appId
    Set-AzdValue "POLICY_BRIDGE_CLIENT_ID" $clientId
}
$app = az ad app show --id $clientId --output json | ConvertFrom-Json
Ensure-ServicePrincipal $clientId

$scopeId = Get-AzdValue "POLICY_BRIDGE_SCOPE_ID"
if (-not $scopeId) {
    $existingScope = @(
        $app.api.oauth2PermissionScopes |
            Where-Object { $_.value -eq "access_as_user" }
    ) | Select-Object -First 1
    $scopeId = if ($existingScope) {
        $existingScope.id
    } else {
        [guid]::NewGuid().ToString()
    }
    Set-AzdValue "POLICY_BRIDGE_SCOPE_ID" $scopeId
}

Invoke-GraphPatch -ObjectId $app.id -Body @{
    identifierUris = @("api://$clientId")
    api = @{
        requestedAccessTokenVersion = 2
        oauth2PermissionScopes = @(
            @{
                adminConsentDescription = (
                    "Evaluate shipment recovery policy on behalf of the user."
                )
                adminConsentDisplayName = "Evaluate shipment recovery policy"
                id = $scopeId
                isEnabled = $true
                type = "User"
                userConsentDescription = (
                    "Allow shipment recovery policy evaluation on your behalf."
                )
                userConsentDisplayName = "Evaluate shipment recovery policy"
                value = "access_as_user"
            }
        )
    }
}

$powerPlatformAppId = "8578e004-a5c6-46e7-913e-12f58912df43"
$invokeScopeId = "204440d3-c1d0-4826-b570-99eb6f5e2aeb"
az ad app permission add `
    --id $clientId `
    --api $powerPlatformAppId `
    --api-permissions "$invokeScopeId=Scope" `
    --output none

$secret = Reset-AppSecret `
    -AppId $clientId `
    -DisplayName "shipment-policy-bridge-active"

Set-AzdValue "AZURE_TENANT_ID" $tenantId
Set-AzdValue "POLICY_BRIDGE_CLIENT_SECRET" $secret
Set-AzdValue "POLICY_BRIDGE_AUDIENCE" "api://$clientId"
Set-AzdValue "POLICY_BRIDGE_REQUIRED_SCOPE" "access_as_user"

if (-not $SkipAdminConsent) {
    az ad app permission admin-consent --id $clientId --output none
    if ($LASTEXITCODE -ne 0) {
        throw "Admin consent failed for the policy bridge application."
    }
}

$secret = $null
Write-Host "Policy bridge application is ready."
Write-Host "Client ID: $clientId"
