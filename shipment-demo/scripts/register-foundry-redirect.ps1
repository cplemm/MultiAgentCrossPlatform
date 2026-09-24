$ErrorActionPreference = "Stop"
. "$PSScriptRoot\common.ps1"

$projectId = Get-AzdValue "AZURE_AI_PROJECT_ID"
$clientId = Get-AzdValue "POLICY_BRIDGE_CLIENT_ID"
if (-not $projectId -or -not $clientId) {
    throw "Foundry project or policy bridge client ID is missing."
}
$redirect = az rest `
    --method get `
    --url (
        "https://management.azure.com$projectId/connections/" +
        "policy-bridge-connection?api-version=2025-06-01"
    ) `
    --query properties.redirectUrl `
    --output tsv
if (-not $redirect) {
    throw "The Foundry connection returned no redirect URI."
}
$existing = @(
    az ad app show `
        --id $clientId `
        --query web.redirectUris `
        --output tsv
)
$redirects = @(
    $existing + $redirect |
        Where-Object { $_ } |
        Sort-Object -Unique
)
az ad app update `
    --id $clientId `
    --web-redirect-uris $redirects `
    --output none
Set-AzdValue "POLICY_BRIDGE_REDIRECT_URL" $redirect
Write-Host "Registered Foundry OAuth redirect URI: $redirect"
