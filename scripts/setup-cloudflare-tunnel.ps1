# RETIRED — do not create a tunnel to this PC.
# Use the Cloudflare Worker path router instead:
#   deploy/cloudflare/README.md
#   npx wrangler deploy  (from deploy/cloudflare)

Write-Host ""
Write-Host "setup-cloudflare-tunnel.ps1 is RETIRED." -ForegroundColor Yellow
Write-Host "Paths: www.txbizfinder.com/{app,radar,channel,api,...}" -ForegroundColor Cyan
Write-Host "See: deploy\cloudflare\README.md" -ForegroundColor Cyan
Write-Host ""
exit 1
