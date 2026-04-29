param(
    [Parameter(Mandatory = $true)]
    [string]$ApiBaseUrl,

    [string]$MerchantId = "1"
)

$ErrorActionPreference = "Stop"

$api = $ApiBaseUrl.TrimEnd("/")
if (-not $api.EndsWith("/api/v1")) {
    throw "ApiBaseUrl must include /api/v1, for example: https://backend.example.com/api/v1"
}

$headers = @{
    "X-Merchant-Id" = $MerchantId
}

function Invoke-JsonCheck {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,

        [Parameter(Mandatory = $true)]
        [string]$Url
    )

    Write-Host "Checking $Name -> $Url"
    try {
        $response = Invoke-RestMethod -Method Get -Uri $Url -Headers $headers -TimeoutSec 20
        $response | ConvertTo-Json -Depth 5
        return $response
    }
    catch {
        throw "$Name failed. URL=$Url Error=$($_.Exception.Message)"
    }
}

$balance = Invoke-JsonCheck -Name "balance" -Url "$api/balance"
Invoke-JsonCheck -Name "payouts" -Url "$api/payouts" | Out-Null
Invoke-JsonCheck -Name "ledger" -Url "$api/ledger?limit=5" | Out-Null

if ($null -eq $balance.available_balance_paise -or $null -eq $balance.held_balance_paise) {
    throw "Balance response is missing expected fields. Check backend route and serializer compatibility."
}

Write-Host ""
Write-Host "Deployment smoke test passed for merchant $MerchantId."
Write-Host "Use this exact frontend env var before building:"
Write-Host "VITE_API_URL=$api"
