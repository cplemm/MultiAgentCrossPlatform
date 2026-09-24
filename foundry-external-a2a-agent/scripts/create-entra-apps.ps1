[CmdletBinding()]
param(
    [string]$ApiDisplayName = "External A2A Graph Profile API",
    [string]$OAuthDisplayName = "Foundry External A2A OAuth Client",
    [switch]$SkipAdminConsent
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\common.ps1"

$tenantId = az account show --query tenantId --output tsv
if (-not $tenantId) {
    throw "Sign in with az login before creating Entra applications."
}

$apiClientId = Get-AzdValue "EXTERNAL_API_CLIENT_ID"
if (-not $apiClientId) {
    $apiApp = az ad app create `
        --display-name $ApiDisplayName `
        --sign-in-audience AzureADMyOrg `
        --output json | ConvertFrom-Json
    $apiClientId = $apiApp.appId
    Set-AzdValue "EXTERNAL_API_CLIENT_ID" $apiClientId
}
$apiApp = az ad app show --id $apiClientId --output json |
    ConvertFrom-Json
Ensure-ServicePrincipal $apiClientId

$scopeId = Get-AzdValue "EXTERNAL_API_SCOPE_ID"
if (-not $scopeId) {
    $existingScope = @(
        $apiApp.api.oauth2PermissionScopes |
            Where-Object { $_.value -eq "access_as_user" }
    ) | Select-Object -First 1
    $scopeId = if ($existingScope) {
        $existingScope.id
    } else {
        [guid]::NewGuid().ToString()
    }
    Set-AzdValue "EXTERNAL_API_SCOPE_ID" $scopeId
}

Invoke-GraphPatch -ObjectId $apiApp.id -Body @{
    identifierUris = @("api://$apiClientId")
    api = @{
        requestedAccessTokenVersion = 2
        oauth2PermissionScopes = @(
            @{
                adminConsentDescription = (
                    "Allow the application to call the external A2A agent " +
                    "on behalf of the signed-in user."
                )
                adminConsentDisplayName = "Access the external A2A agent"
                id = $scopeId
                isEnabled = $true
                type = "User"
                userConsentDescription = (
                    "Allow this application to call the external A2A agent " +
                    "on your behalf."
                )
                userConsentDisplayName = "Access the external A2A agent"
                value = "access_as_user"
            }
        )
    }
}

$graphAppId = "00000003-0000-0000-c000-000000000000"
$graphUserRead = "e1fe6dd8-ba31-4d61-89e7-88639da4683d"
az ad app permission add `
    --id $apiClientId `
    --api $graphAppId `
    --api-permissions "$graphUserRead=Scope" `
    --output none

$oauthClientId = Get-AzdValue "FOUNDRY_OAUTH_CLIENT_ID"
if (-not $oauthClientId) {
    $oauthApp = az ad app create `
        --display-name $OAuthDisplayName `
        --sign-in-audience AzureADMyOrg `
        --output json | ConvertFrom-Json
    $oauthClientId = $oauthApp.appId
    Set-AzdValue "FOUNDRY_OAUTH_CLIENT_ID" $oauthClientId
}
$oauthApp = az ad app show --id $oauthClientId --output json |
    ConvertFrom-Json
Ensure-ServicePrincipal $oauthClientId

az ad app permission add `
    --id $oauthClientId `
    --api $apiClientId `
    --api-permissions "$scopeId=Scope" `
    --output none

$azureCliClientId = "04b07795-8ddb-461a-bbee-02f9e1bf7b46"
Invoke-GraphPatch -ObjectId $apiApp.id -Body @{
    api = @{
        requestedAccessTokenVersion = 2
        oauth2PermissionScopes = @(
            @{
                adminConsentDescription = (
                    "Allow the application to call the external A2A agent " +
                    "on behalf of the signed-in user."
                )
                adminConsentDisplayName = "Access the external A2A agent"
                id = $scopeId
                isEnabled = $true
                type = "User"
                userConsentDescription = (
                    "Allow this application to call the external A2A agent " +
                    "on your behalf."
                )
                userConsentDisplayName = "Access the external A2A agent"
                value = "access_as_user"
            }
        )
        preAuthorizedApplications = @(
            @{
                appId = $oauthClientId
                delegatedPermissionIds = @($scopeId)
            },
            @{
                appId = $azureCliClientId
                delegatedPermissionIds = @($scopeId)
            }
        )
    }
}

$apiSecret = Reset-AppSecret `
    -AppId $apiClientId `
    -DisplayName "external-a2a-demo-active"
$oauthSecret = Reset-AppSecret `
    -AppId $oauthClientId `
    -DisplayName "foundry-a2a-oauth-active"

Set-AzdValue "AZURE_TENANT_ID" $tenantId
Set-AzdValue "EXTERNAL_API_CLIENT_SECRET" $apiSecret
Set-AzdValue "FOUNDRY_OAUTH_CLIENT_SECRET" $oauthSecret
Set-AzdValue "EXTERNAL_API_SCOPE" (
    "api://$apiClientId/access_as_user"
)

if (-not $SkipAdminConsent) {
    az ad app permission admin-consent --id $apiClientId --output none
    if ($LASTEXITCODE -ne 0) {
        throw "Admin consent failed for the external API application."
    }
    az ad app permission admin-consent --id $oauthClientId --output none
    if ($LASTEXITCODE -ne 0) {
        throw "Admin consent failed for the Foundry OAuth application."
    }
} else {
    $userObjectId = az ad signed-in-user show --query id --output tsv
    if (-not $userObjectId) {
        throw "Unable to resolve the signed-in user for delegated consent."
    }
    az ad app permission grant `
        --id $apiClientId `
        --api $graphAppId `
        --scope User.Read `
        --consent-type Principal `
        --principal-id $userObjectId `
        --output none
    if ($LASTEXITCODE -ne 0) {
        throw "Current-user consent failed for Microsoft Graph User.Read."
    }
    az ad app permission grant `
        --id $oauthClientId `
        --api $apiClientId `
        --scope access_as_user `
        --consent-type Principal `
        --principal-id $userObjectId `
        --output none
    if ($LASTEXITCODE -ne 0) {
        throw "Current-user consent failed for the external A2A API."
    }
    Write-Warning (
        "Tenant-wide consent was skipped. Delegated consent was granted only " +
        "for the currently signed-in user."
    )
}

$apiSecret = $null
$oauthSecret = $null
Write-Host "Entra applications are ready."
Write-Host "External API client ID: $apiClientId"
Write-Host "Foundry OAuth client ID: $oauthClientId"
