[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$ClientId,

    [Parameter(Mandatory)]
    [ValidatePattern("^https://")]
    [string]$RedirectUri
)

$ErrorActionPreference = "Stop"

$existing = @(
    az ad app show `
        --id $ClientId `
        --query web.redirectUris `
        --output tsv
)

if ($LASTEXITCODE -ne 0) {
    throw "Unable to read the Entra application."
}

$redirects = @(
    $existing + $RedirectUri |
        Where-Object { $_ } |
        Sort-Object -Unique
)

az ad app update `
    --id $ClientId `
    --web-redirect-uris $redirects `
    --output none

if ($LASTEXITCODE -ne 0) {
    throw "Unable to register the CPS redirect URI."
}

Write-Host "Registered redirect URI: $RedirectUri"

