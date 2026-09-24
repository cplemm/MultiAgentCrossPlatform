Set-StrictMode -Version Latest

function Get-AzdValue {
    param([Parameter(Mandatory)][string]$Name)
    $value = azd env get-value $Name 2>$null
    if ($LASTEXITCODE -ne 0) {
        return $null
    }
    return $value.Trim('"').Trim()
}

function Set-AzdValue {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string]$Value
    )
    azd env set $Name $Value | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to set azd environment value $Name"
    }
}

function Get-FoundryProjectEndpoint {
    $endpoint = Get-AzdValue "FOUNDRY_PROJECT_ENDPOINT"
    if ($endpoint) {
        return $endpoint
    }
    throw "FOUNDRY_PROJECT_ENDPOINT is missing from the azd environment."
}

function Get-GraphToken {
    $token = az account get-access-token `
        --resource https://graph.microsoft.com `
        --query accessToken `
        --output tsv
    if ($LASTEXITCODE -ne 0 -or -not $token) {
        throw "Unable to acquire a Microsoft Graph token."
    }
    return $token
}

function Invoke-GraphPatch {
    param(
        [Parameter(Mandatory)][string]$ObjectId,
        [Parameter(Mandatory)][hashtable]$Body
    )
    $token = [string](Get-GraphToken)
    $headers = @{
        Authorization = [string]::Concat(
            "Bearer",
            [char]32,
            $token.Trim()
        )
    }
    Invoke-RestMethod `
        -Method Patch `
        -Uri "https://graph.microsoft.com/v1.0/applications/$ObjectId" `
        -Headers $headers `
        -ContentType "application/json" `
        -Body ($Body | ConvertTo-Json -Depth 12)
}

function Ensure-ServicePrincipal {
    param([Parameter(Mandatory)][string]$AppId)
    $existing = az ad sp list `
        --filter "appId eq '$AppId'" `
        --query "[0].id" `
        --output tsv
    if (-not $existing) {
        az ad sp create --id $AppId --output none
        if ($LASTEXITCODE -ne 0) {
            throw "Unable to create service principal for $AppId"
        }
    }
}

function Reset-AppSecret {
    param(
        [Parameter(Mandatory)][string]$AppId,
        [Parameter(Mandatory)][string]$DisplayName
    )
    $credential = az ad app credential reset `
        --id $AppId `
        --append `
        --display-name $DisplayName `
        --years 1 `
        --output json | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0 -or -not $credential.password) {
        throw "Unable to create a client secret for $AppId"
    }
    return $credential.password
}
