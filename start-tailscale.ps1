# TexasBizFinder — local + Tailscale (sin costo cloud)
# Uso: .\start-tailscale.ps1
# Abre en otro dispositivo: http://<tu-ip-tailscale>:5173

$Root = $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Node = "C:\Program Files\nodejs\node.exe"
$Vite = Join-Path $Root "frontend\node_modules\vite\bin\vite.js"
$Tailscale = "C:\Program Files\Tailscale\tailscale.exe"

Write-Host "TexasBizFinder — modo Tailscale" -ForegroundColor Cyan
Write-Host ""

if (Test-Path $Tailscale) {
    $tsIp = & $Tailscale ip -4 2>$null
    if ($tsIp) {
        Write-Host "Tailscale IP:  $tsIp" -ForegroundColor Green
        Write-Host "URL remota:    http://${tsIp}:5173" -ForegroundColor Green
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
    Write-Host "Red local:     http://${lanIp}:5173" -ForegroundColor DarkGray
}
Write-Host "Local:         http://127.0.0.1:5173" -ForegroundColor DarkGray
Write-Host ""
Write-Host "Iniciando API (0.0.0.0:8000) y frontend (0.0.0.0:5173)..." -ForegroundColor Cyan
Write-Host "Cierra esta ventana o Ctrl+C en cada proceso para detener." -ForegroundColor DarkGray
Write-Host ""

Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "Set-Location '$Root'; & '$Python' run.py --no-seed --host 0.0.0.0 --port 8000"
) -WindowStyle Normal

Start-Sleep -Seconds 2

Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "Set-Location (Join-Path '$Root' 'frontend'); & '$Node' '$Vite' --host 0.0.0.0 --port 5173"
) -WindowStyle Normal