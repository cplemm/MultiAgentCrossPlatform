[CmdletBinding()]
param(
    [string]$ConnectionName = "external-graph-profile-oauth"
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\common.ps1"

$projectEndpoint = Get-FoundryProjectEndpoint
$target = Get-AzdValue "EXTERNAL_A2A_BASE_URL"
$tenantId = Get-AzdValue "AZURE_TENANT_ID"
$apiClientId = Get-AzdValue "EXTERNAL_API_CLIENT_ID"
$oauthClientId = Get-AzdValue "FOUNDRY_OAUTH_CLIENT_ID"
$oauthSecret = Get-AzdValue "FOUNDRY_OAUTH_CLIENT_SECRET"
if (
    -not $target -or
    -not $tenantId -or
    -not $apiClientId -or
    -not $oauthClientId -or
    -not $oauthSecret
) {
    throw "Required OAuth or endpoint values are missing."
}

azd ai connection delete $ConnectionName `
    --project-endpoint $projectEndpoint `
    --force `
    --no-prompt `
    --output none 2>$null

$authority = (
    "https://login.microsoftonline.com/$tenantId/oauth2/v2.0"
)
$projectId = Get-AzdValue "AZURE_AI_PROJECT_ID"
$subscriptionId = Get-AzdValue "AZURE_SUBSCRIPTION_ID"
if (-not $projectId -or -not $subscriptionId) {
    throw "Foundry project resource information is missing."
}

# The Sweden Central RP currently returns HTTP 500 for custom OAuth on a
# RemoteA2A connection. A2ATool supports a non-RemoteA2A connection when
# base_url is supplied, so use a standard OAuth RemoteTool connection as the
# credential store while retaining A2A 1.0 for the actual tool call.
azd ai connection create $ConnectionName `
    --project-endpoint $projectEndpoint `
    --kind remote-tool `
    --target $target `
    --auth-type oauth2 `
    --authorization-url "$authority/authorize" `
    --token-url "$authority/token" `
    --refresh-url "$authority/token" `
    --client-id $oauthClientId `
    --client-secret $oauthSecret `
    --scopes (
        "openid profile offline_access " +
        "api://$apiClientId/access_as_user"
    ) `
    --force `
    --no-prompt `
    --output json | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Unable to create the Foundry OAuth credential connection."
}

$connection = az rest `
    --method get `
    --url (
        "https://management.azure.com$projectId/connections/" +
        "${ConnectionName}?api-version=2025-06-01"
    ) `
    --output json | ConvertFrom-Json
$redirectUrl = $connection.properties.redirectUrl
if (-not $redirectUrl) {
    throw "The Foundry connection did not return an OAuth redirect URL."
}

$existing = @(
    az ad app show `
        --id $oauthClientId `
        --query web.redirectUris `
        --output tsv
)
$redirects = @(
    $existing + $redirectUrl |
        Where-Object { $_ } |
        Sort-Object -Unique
)
az ad app update `
    --id $oauthClientId `
    --web-redirect-uris $redirects `
    --output none

if ($LASTEXITCODE -ne 0) {
    throw "Unable to register the Foundry OAuth redirect URI."
}

Set-AzdValue "EXTERNAL_A2A_CONNECTION_NAME" $ConnectionName
Set-AzdValue "EXTERNAL_A2A_CONNECTION_KIND" "RemoteTool"
Set-AzdValue "FOUNDRY_OAUTH_REDIRECT_URL" $redirectUrl
$oauthSecret = $null
Write-Host "Foundry OAuth A2A connection is ready."
Write-Host "Redirect URI registered: $redirectUrl"
