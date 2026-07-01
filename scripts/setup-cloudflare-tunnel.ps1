# TX BizFinder - one-time Cloudflare Tunnel setup for www.txbizfinder.com
# Requires: domain txbizfinder.com on your Cloudflare account (orange-cloud proxy ON).
# Usage: .\scripts\setup-cloudflare-tunnel.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
$TunnelName = "txbizfinder"
$ConfigDir = Join-Path $Root "deploy\cloudflare"
$ConfigPath = Join-Path $ConfigDir "config.yml"
$TemplatePath = Join-Path $ConfigDir "config.yml.template"
$CloudflaredDir = Join-Path $env:USERPROFILE ".cloudflared"

function Find-Cloudflared {
    $candidates = @(
        "C:\Program Files (x86)\cloudflared\cloudflared.exe",
        "C:\Program Files\cloudflared\cloudflared.exe"
    )
    foreach ($path in $candidates) {
        if (Test-Path $path) { return $path }
    }
    $cmd = Get-Command cloudflared -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $null
}

Write-Host ""
Write-Host "TX BizFinder - Cloudflare Tunnel setup" -ForegroundColor Cyan
Write-Host "Dominio: www.txbizfinder.com" -ForegroundColor DarkGray
Write-Host ""

$cf = Find-Cloudflared
if (-not $cf) {
    Write-Host "cloudflared no encontrado. Instala con:" -ForegroundColor Red
    Write-Host "  winget install Cloudflare.cloudflared" -ForegroundColor Yellow
    exit 1
}
Write-Host "cloudflared: $cf" -ForegroundColor Green

$cert = Join-Path $CloudflaredDir "cert.pem"
if (-not (Test-Path $cert)) {
    Write-Host ""
    Write-Host "Paso 1/4 - Inicia sesion en Cloudflare (se abre el navegador)..." -ForegroundColor Cyan
    Write-Host "Elige la cuenta donde esta txbizfinder.com" -ForegroundColor DarkGray
    & $cf tunnel login
    if (-not (Test-Path $cert)) {
        Write-Host "Login cancelado o fallido. Vuelve a ejecutar el script." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "Cloudflare login: OK (cert.pem existe)" -ForegroundColor Green
}

Write-Host ""
Write-Host "Paso 2/4 - Crear tunnel '$TunnelName'..." -ForegroundColor Cyan
$existing = & $cf tunnel list 2>&1 | Out-String
if ($existing -match [regex]::Escape($TunnelName)) {
    Write-Host "Tunnel '$TunnelName' ya existe - se reutiliza." -ForegroundColor Yellow
} else {
    & $cf tunnel create $TunnelName
}

$tunnelId = $null
$listOut = & $cf tunnel list 2>&1 | Out-String
$idPattern = [regex]::Escape($TunnelName) + '\s+([0-9a-f-]{36})'
if ($listOut -match $idPattern) {
    $tunnelId = $Matches[1]
}
if (-not $tunnelId) {
    $credFiles = Get-ChildItem -Path $CloudflaredDir -Filter "*.json" -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -ne "config.json" } |
        Sort-Object LastWriteTime -Descending
    if ($credFiles) {
        $tunnelId = $credFiles[0].BaseName
    }
}
if (-not $tunnelId) {
    Write-Host "No se pudo obtener el ID del tunnel. Revisa: cloudflared tunnel list" -ForegroundColor Red
    exit 1
}
Write-Host "Tunnel ID: $tunnelId" -ForegroundColor Green

$credFile = Join-Path $CloudflaredDir "$tunnelId.json"
if (-not (Test-Path $credFile)) {
    Write-Host "No se encontro credenciales: $credFile" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Paso 3/4 - DNS en Cloudflare (CNAME automatico)..." -ForegroundColor Cyan
foreach ($dnsName in @("www.txbizfinder.com", "txbizfinder.com")) {
    $routeOut = & $cf tunnel route dns $TunnelName $dnsName 2>&1 | Out-String
    if ($routeOut -match "already exists|Added CNAME") {
        Write-Host "  $dnsName - OK" -ForegroundColor Green
    } else {
        Write-Host "  $dnsName - $routeOut" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Paso 4/4 - Escribir $ConfigPath ..." -ForegroundColor Cyan
if (-not (Test-Path $TemplatePath)) {
    Write-Host "Falta plantilla: $TemplatePath" -ForegroundColor Red
    exit 1
}
$template = Get-Content $TemplatePath -Raw
$config = $template `
    -replace '\{\{TUNNEL_NAME\}\}', $TunnelName `
    -replace '\{\{CREDENTIALS_FILE\}\}', ($credFile -replace '\\', '/')
Set-Content -Path $ConfigPath -Value $config -Encoding UTF8
Write-Host "Config escrito." -ForegroundColor Green

Write-Host ""
Write-Host "Listo. Siguiente paso:" -ForegroundColor Cyan
Write-Host "  .\start-cloudflare.ps1" -ForegroundColor Yellow
Write-Host ""
Write-Host "Cloudflare Dashboard (recomendado):" -ForegroundColor DarkGray
Write-Host "  SSL/TLS -> Full (strict)" -ForegroundColor DarkGray
Write-Host "  Rules -> Redirect txbizfinder.com -> https://www.txbizfinder.com (opcional)" -ForegroundColor DarkGray
Write-Host ""