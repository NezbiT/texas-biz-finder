# TX BizFinder - produccion local + Cloudflare Tunnel (HTTPS + PWA)
# Requisito: ejecutar primero .\scripts\setup-cloudflare-tunnel.ps1
# Uso: .\start-cloudflare.ps1
#      .\start-cloudflare.ps1 -Rebuild

param(
    [switch]$Rebuild
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$ConfigPath = Join-Path $Root "deploy\cloudflare\config.yml"
$Port = 8000

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
Write-Host "TX BizFinder - Cloudflare Tunnel" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $Python)) {
    Write-Host "Python venv no encontrado. Crea .venv e instala dependencias." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $ConfigPath)) {
    Write-Host "Falta deploy/cloudflare/config.yml" -ForegroundColor Red
    Write-Host "Ejecuta primero: .\scripts\setup-cloudflare-tunnel.ps1" -ForegroundColor Yellow
    exit 1
}

$cf = Find-Cloudflared
if (-not $cf) {
    Write-Host "cloudflared no instalado. winget install Cloudflare.cloudflared" -ForegroundColor Red
    exit 1
}

$distIndex = Join-Path $Root "frontend\dist\index.html"
if ($Rebuild -or -not (Test-Path $distIndex)) {
    Write-Host "Building frontend (npm run build)..." -ForegroundColor Cyan
    $npm = "npm.cmd"
    $frontend = Join-Path $Root "frontend"
    Set-Location $frontend
    if (-not (Test-Path "node_modules")) {
        & $npm install
    }
    & $npm run build
    Set-Location $Root
    if (-not (Test-Path $distIndex)) {
        Write-Host "Build fallo: falta frontend/dist/index.html" -ForegroundColor Red
        exit 1
    }
    Write-Host "Build OK." -ForegroundColor Green
}

$onPort = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($onPort) {
    Write-Host "Puerto $Port en uso - deteniendo proceso anterior..." -ForegroundColor Yellow
    $onPort | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 1
}

Write-Host "Iniciando API + PWA (prod, puerto $Port)..." -ForegroundColor Cyan
$apiJob = Start-Process -FilePath $Python -ArgumentList @(
    "run.py", "--prod", "--no-seed", "--host", "127.0.0.1", "--port", "$Port"
) -WorkingDirectory $Root -PassThru -WindowStyle Minimized

Start-Sleep -Seconds 3

try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 10
    Write-Host "API: $($health.status) - $($health.app)" -ForegroundColor Green
} catch {
    Write-Host "API no respondio en /health. Revisa logs del proceso $($apiJob.Id)." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Iniciando Cloudflare Tunnel..." -ForegroundColor Cyan
Write-Host "  Publico:  https://www.txbizfinder.com" -ForegroundColor Green
Write-Host "  Publico:  https://txbizfinder.com" -ForegroundColor Green
Write-Host "  Local:    http://127.0.0.1:$Port" -ForegroundColor DarkGray
Write-Host ""
Write-Host "Manten esta ventana abierta. Ctrl+C detiene el tunnel (la API sigue en segundo plano)." -ForegroundColor DarkGray
Write-Host "Para detener la API: Stop-Process -Id $($apiJob.Id)" -ForegroundColor DarkGray
Write-Host ""

& $cf tunnel --config $ConfigPath run