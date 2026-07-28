# TX BizFinder — local + Tailscale (sin costo cloud)
# Uso: .\start-tailscale.ps1
# Abre en otro dispositivo: http://<tu-ip-tailscale>:3000

$Root = $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Frontend = Join-Path $Root "frontend-v2"
$Tailscale = "C:\Program Files\Tailscale\tailscale.exe"

Write-Host "TX BizFinder — modo Tailscale" -ForegroundColor Cyan
Write-Host ""

if (Test-Path $Tailscale) {
    $tsIp = & $Tailscale ip -4 2>$null
    if ($tsIp) {
        Write-Host "Tailscale IP:  $tsIp" -ForegroundColor Green
        Write-Host "URL remota:    http://${tsIp}:3000" -ForegroundColor Green
    } else {
        Write-Host "Tailscale aun no tiene IP. Abre Tailscale y espera 'Connected'." -ForegroundColor Yellow
    }
} else {
    Write-Host "Tailscale no encontrado; solo acceso local." -ForegroundColor Yellow
}

$lanIp = (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.IPAddress -notlike "127.*" -and $_.PrefixOrigin -ne "WellKnown" } |
    Select-Object -First 1 -ExpandProperty IPAddress)

if ($lanIp) {
    Write-Host "Red local:     http://${lanIp}:3000" -ForegroundColor DarkGray
}
Write-Host "Local:         http://127.0.0.1:3000" -ForegroundColor DarkGray
Write-Host ""
Write-Host "Iniciando API (0.0.0.0:8000) y Nuxt dev (0.0.0.0:3000)..." -ForegroundColor Cyan
Write-Host "Cierra esta ventana o Ctrl+C en cada proceso para detener." -ForegroundColor DarkGray
Write-Host ""

Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "Set-Location '$Root'; & '$Python' run.py --no-seed --host 0.0.0.0 --port 8000"
) -WindowStyle Normal

Start-Sleep -Seconds 2

# Nuxt dev: su devProxy reenvia /api al FastAPI de :8000, asi que el navegador
# habla siempre con el mismo origen (sin CORS).
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "Set-Location '$Frontend'; npm.cmd run dev -- --host 0.0.0.0 --port 3000"
) -WindowStyle Normal