$ErrorActionPreference = "Stop"
. "$PSScriptRoot\common.ps1"

$python = Join-Path (Split-Path -Parent $PSScriptRoot) `
    ".venv\Scripts\python.exe"
$env:EXTERNAL_A2A_BASE_URL = Get-AzdValue "EXTERNAL_A2A_BASE_URL"
$apiClientId = Get-AzdValue "EXTERNAL_API_CLIENT_ID"
$env:A2A_ACCESS_TOKEN = az account get-access-token `
    --scope "api://$apiClientId/access_as_user" `
    --query accessToken `
    --output tsv
if ($LASTEXITCODE -ne 0 -or -not $env:A2A_ACCESS_TOKEN) {
    throw "Unable to acquire the delegated external A2A access token."
}
& $python "$PSScriptRoot\smoke-test-external.py"
$env:A2A_ACCESS_TOKEN = $null
if ($LASTEXITCODE -ne 0) {
    throw "Direct delegated A2A smoke test failed."
}
