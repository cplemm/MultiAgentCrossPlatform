[CmdletBinding()]
param(
    [string]$SubscriptionId = "39b4a175-7439-4dc8-b6a3-450d620159d2",
    [string]$Location = "swedencentral",
    [string]$ResourceGroup = "rg-foundry-external-a2a-agent",
    [string]$ContainerAppName = "external-graph-profile-agent"
)

$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:NO_COLOR = "1"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
. "$PSScriptRoot\common.ps1"

$tenantId = Get-AzdValue "AZURE_TENANT_ID"
$apiClientId = Get-AzdValue "EXTERNAL_API_CLIENT_ID"
$apiSecret = Get-AzdValue "EXTERNAL_API_CLIENT_SECRET"
if (-not $tenantId -or -not $apiClientId -or -not $apiSecret) {
    throw "Run create-entra-apps.ps1 before deploying the Container App."
}

az account set --subscription $SubscriptionId
az group create `
    --name $ResourceGroup `
    --location $Location `
    --output none

$source = Join-Path $PSScriptRoot "..\src\external-agent"
$environmentName = "$ContainerAppName-env"
$environmentId = az containerapp env show `
    --subscription $SubscriptionId `
    --resource-group $ResourceGroup `
    --name $environmentName `
    --query id `
    --output tsv 2>$null
if (-not $environmentId) {
    az containerapp env create `
        --subscription $SubscriptionId `
        --resource-group $ResourceGroup `
        --name $environmentName `
        --location $Location `
        --output none
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to create the Container Apps environment."
    }
}

$registryName = az acr list `
    --subscription $SubscriptionId `
    --resource-group $ResourceGroup `
    --query "[0].name" `
    --output tsv
if (-not $registryName) {
    $suffix = (
        [Convert]::ToHexString(
            [Security.Cryptography.SHA256]::HashData(
                [Text.Encoding]::UTF8.GetBytes($ResourceGroup)
            )
        ).Substring(0, 10).ToLowerInvariant()
    )
    $registryName = "a2aobo$suffix"
    az acr create `
        --subscription $SubscriptionId `
        --resource-group $ResourceGroup `
        --name $registryName `
        --location $Location `
        --sku Basic `
        --output none
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to create Azure Container Registry."
    }
}

$imageTag = Get-Date -Format "yyyyMMddHHmmss"
$repository = "external-graph-profile-agent"
$image = "$registryName.azurecr.io/${repository}:$imageTag"
Write-Host "Queueing ACR build for $image..."
Write-Host "Build logs are intentionally suppressed to avoid a Windows CLI encoding bug."
$build = az acr build `
    --subscription $SubscriptionId `
    --registry $registryName `
    --image "${repository}:$imageTag" `
    --platform linux/amd64 `
    --file (Join-Path $source "Dockerfile") `
    --no-logs `
    $source `
    --output json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) {
    throw "Unable to queue the ACR build."
}
if ($build.status -and $build.status -ne "Succeeded") {
    throw "ACR build failed with status $($build.status)."
}
Write-Host "ACR build completed."

$existingApp = az containerapp show `
    --subscription $SubscriptionId `
    --resource-group $ResourceGroup `
    --name $ContainerAppName `
    --query id `
    --output tsv 2>$null

if (-not $existingApp) {
    az containerapp create `
        --subscription $SubscriptionId `
        --resource-group $ResourceGroup `
        --name $ContainerAppName `
        --environment $environmentName `
        --image $image `
        --ingress external `
        --target-port 8000 `
        --system-assigned `
        --registry-server "$registryName.azurecr.io" `
        --registry-identity system `
        --secrets "api-client-secret=$apiSecret" `
        --env-vars `
            "AZURE_TENANT_ID=$tenantId" `
            "API_CLIENT_ID=$apiClientId" `
            "API_CLIENT_SECRET=secretref:api-client-secret" `
            "API_AUDIENCE=api://$apiClientId" `
            "API_REQUIRED_SCOPE=access_as_user" `
            "PUBLIC_BASE_URL=https://placeholder.invalid" `
            "PORT=8000" `
        --min-replicas 1 `
        --max-replicas 1 `
        --output none
} else {
    az containerapp secret set `
        --subscription $SubscriptionId `
        --resource-group $ResourceGroup `
        --name $ContainerAppName `
        --secrets "api-client-secret=$apiSecret" `
        --output none
    az containerapp update `
        --subscription $SubscriptionId `
        --resource-group $ResourceGroup `
        --name $ContainerAppName `
        --image $image `
        --set-env-vars `
            "AZURE_TENANT_ID=$tenantId" `
            "API_CLIENT_ID=$apiClientId" `
            "API_CLIENT_SECRET=secretref:api-client-secret" `
            "API_AUDIENCE=api://$apiClientId" `
            "API_REQUIRED_SCOPE=access_as_user" `
            "PORT=8000" `
        --min-replicas 1 `
        --max-replicas 1 `
        --output none
}
if ($LASTEXITCODE -ne 0) {
    throw "Unable to create or update the Container App."
}

$fqdn = az containerapp show `
    --subscription $SubscriptionId `
    --resource-group $ResourceGroup `
    --name $ContainerAppName `
    --query properties.configuration.ingress.fqdn `
    --output tsv
if (-not $fqdn) {
    throw "Unable to resolve the Container App FQDN."
}
$baseUrl = "https://$fqdn"
az containerapp update `
    --subscription $SubscriptionId `
    --resource-group $ResourceGroup `
    --name $ContainerAppName `
    --set-env-vars "PUBLIC_BASE_URL=$baseUrl" `
    --output none
if ($LASTEXITCODE -ne 0) {
    throw "Unable to configure the public A2A base URL."
}

Set-AzdValue "EXTERNAL_A2A_BASE_URL" $baseUrl
Set-AzdValue "AZURE_SUBSCRIPTION_ID" $SubscriptionId
Set-AzdValue "AZURE_LOCATION" $Location
Set-AzdValue "EXTERNAL_RESOURCE_GROUP" $ResourceGroup
Set-AzdValue "EXTERNAL_CONTAINER_APP_NAME" $ContainerAppName

$apiSecret = $null
Write-Host "External A2A agent deployed: $baseUrl"
