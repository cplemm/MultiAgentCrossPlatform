[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$ProjectEndpoint,

    [string]$AgentName = "market-research-agent"
)

$ErrorActionPreference = "Stop"
$ProjectEndpoint = $ProjectEndpoint.TrimEnd("/")

$token = az account get-access-token `
    --resource https://ai.azure.com `
    --query accessToken `
    --output tsv

if ($LASTEXITCODE -ne 0 -or -not $token) {
    throw "Unable to acquire a token for https://ai.azure.com."
}

$body = @{
    agent_card = @{
        version = "1.0"
        description = "Researches current financial-market information."
        skills = @(
            @{
                id = "market-research"
                name = "Market research"
                description = "Finds current prices, news, catalysts, and risks."
            }
        )
    }
    agent_endpoint = @{
        protocol_configuration = @{
            responses = @{}
            a2a = @{}
        }
    }
} | ConvertTo-Json -Depth 8

Invoke-RestMethod `
    -Method Patch `
    -Uri "$ProjectEndpoint/agents/$AgentName`?api-version=v1" `
    -Headers @{ Authorization = "Bearer $token" } `
    -ContentType "application/json" `
    -Body $body | Out-Null

$a2aEndpoint = "$ProjectEndpoint/agents/$AgentName/endpoint/protocols/a2a"
$cpsA2aEndpoint = $a2aEndpoint
$cardUrl = "$a2aEndpoint/agentCard/v1.0"

$card = Invoke-RestMethod `
    -Method Get `
    -Uri $cardUrl `
    -Headers @{ Authorization = "Bearer $token" }

$cpsInterface = @(
    $card.supportedInterfaces |
        Where-Object {
            $_.protocolVersion -eq "1.0" -and
            $_.protocolBinding -eq "JSONRPC"
        }
)

if ($cpsInterface.Count -eq 0) {
    throw "A2A card validation failed. CPS requires a JSONRPC interface with protocolVersion 1.0."
}

Write-Host "Incoming A2A is enabled."
Write-Host "A2A base endpoint: $a2aEndpoint"
Write-Host "CPS A2A URL:      $cpsA2aEndpoint"
Write-Host "A2A v1 card:      $cardUrl"
