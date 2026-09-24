[CmdletBinding()]
param(
    [string]$ResourceGroup = "rg-shipment-recovery-demo",
    [string]$Location = "swedencentral",
    [string]$PolicyBridgeName = "shipment-policy-bridge",
    [string]$SupplierAgentName = "shipment-supplier-agent"
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\common.ps1"
$root = Split-Path -Parent $PSScriptRoot

$tenantId = Get-AzdValue "AZURE_TENANT_ID"
$clientId = Get-AzdValue "POLICY_BRIDGE_CLIENT_ID"
$clientSecret = Get-AzdValue "POLICY_BRIDGE_CLIENT_SECRET"
$cpsEnvironment = Get-AzdValue "COPILOT_STUDIO_ENVIRONMENT_ID"
$cpsSchema = Get-AzdValue "COPILOT_STUDIO_SCHEMA_NAME"
if (
    -not $tenantId -or
    -not $clientId -or
    -not $clientSecret -or
    -not $cpsEnvironment -or
    -not $cpsSchema
) {
    throw (
        "Policy bridge or Copilot Studio values are missing. Run " +
        "create-policy-app.ps1 and set COPILOT_STUDIO_ENVIRONMENT_ID and " +
        "COPILOT_STUDIO_SCHEMA_NAME."
    )
}

az group create `
    --name $ResourceGroup `
    --location $Location `
    --output none

az containerapp up `
    --name $SupplierAgentName `
    --resource-group $ResourceGroup `
    --location $Location `
    --source (Join-Path $root "src\supplier-agent") `
    --ingress external `
    --target-port 8000 `
    --env-vars `
        "PUBLIC_BASE_URL=https://placeholder.invalid" `
        "INVENTORY_PATH=data/inventory.json" `
        "PORT=8000"
if ($LASTEXITCODE -ne 0) {
    throw "Supplier agent deployment failed."
}
$supplierFqdn = az containerapp show `
    --name $SupplierAgentName `
    --resource-group $ResourceGroup `
    --query properties.configuration.ingress.fqdn `
    --output tsv
$supplierUrl = "https://$supplierFqdn"
az containerapp update `
    --name $SupplierAgentName `
    --resource-group $ResourceGroup `
    --set-env-vars `
        "PUBLIC_BASE_URL=$supplierUrl" `
        "INVENTORY_PATH=data/inventory.json" `
        "PORT=8000" `
    --min-replicas 1 `
    --max-replicas 1 `
    --output none

az containerapp up `
    --name $PolicyBridgeName `
    --resource-group $ResourceGroup `
    --location $Location `
    --source (Join-Path $root "src\policy-bridge") `
    --ingress external `
    --target-port 8000 `
    --env-vars `
        "AZURE_TENANT_ID=$tenantId" `
        "POLICY_BRIDGE_CLIENT_ID=$clientId" `
        "POLICY_BRIDGE_CLIENT_SECRET=not-configured-yet" `
        "POLICY_BRIDGE_AUDIENCE=api://$clientId" `
        "POLICY_BRIDGE_REQUIRED_SCOPE=access_as_user" `
        "POLICY_BRIDGE_URL=https://placeholder.invalid/mcp" `
        "COPILOT_STUDIO_ENVIRONMENT_ID=$cpsEnvironment" `
        "COPILOT_STUDIO_SCHEMA_NAME=$cpsSchema" `
        "HOST=0.0.0.0" `
        "PORT=8000"
if ($LASTEXITCODE -ne 0) {
    throw "Policy bridge deployment failed."
}
$bridgeFqdn = az containerapp show `
    --name $PolicyBridgeName `
    --resource-group $ResourceGroup `
    --query properties.configuration.ingress.fqdn `
    --output tsv
$bridgeUrl = "https://$bridgeFqdn/mcp"
az containerapp secret set `
    --name $PolicyBridgeName `
    --resource-group $ResourceGroup `
    --secrets "policy-client-secret=$clientSecret" `
    --output none
az containerapp update `
    --name $PolicyBridgeName `
    --resource-group $ResourceGroup `
    --set-env-vars `
        "AZURE_TENANT_ID=$tenantId" `
        "POLICY_BRIDGE_CLIENT_ID=$clientId" `
        "POLICY_BRIDGE_CLIENT_SECRET=secretref:policy-client-secret" `
        "POLICY_BRIDGE_AUDIENCE=api://$clientId" `
        "POLICY_BRIDGE_REQUIRED_SCOPE=access_as_user" `
        "POLICY_BRIDGE_URL=$bridgeUrl" `
        "COPILOT_STUDIO_ENVIRONMENT_ID=$cpsEnvironment" `
        "COPILOT_STUDIO_SCHEMA_NAME=$cpsSchema" `
        "HOST=0.0.0.0" `
        "PORT=8000" `
    --min-replicas 1 `
    --max-replicas 1 `
    --output none

Set-AzdValue "AZURE_RESOURCE_GROUP" $ResourceGroup
Set-AzdValue "AZURE_LOCATION" $Location
Set-AzdValue "SUPPLIER_A2A_BASE_URL" $supplierUrl
Set-AzdValue "SUPPLIER_CONTAINER_APP_NAME" $SupplierAgentName
Set-AzdValue "POLICY_BRIDGE_URL" $bridgeUrl
Set-AzdValue "POLICY_BRIDGE_CONTAINER_APP_NAME" $PolicyBridgeName

Write-Host "Supplier A2A endpoint: $supplierUrl"
Write-Host "Policy MCP endpoint:   $bridgeUrl"
