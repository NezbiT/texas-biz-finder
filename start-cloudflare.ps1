# RETIRED — Cloudflare Tunnel to this PC is no longer part of the deploy model.
#
# Suite URLs are path-based on a single domain:
#   https://www.txbizfinder.com/app | /radar | /channel | /api | ...
#
# API runs on Oracle Free Tier; edge routing is a Cloudflare Worker
# (deploy/cloudflare/path-router.worker.js). See deploy/cloudflare/README.md
#
# Local API only:
#   python run.py
#   # or: docker compose up

Write-Host ""
Write-Host "start-cloudflare.ps1 is RETIRED." -ForegroundColor Yellow
Write-Host "No tunnel to this computer." -ForegroundColor Yellow
Write-Host ""
Write-Host "Use:" -ForegroundColor Cyan
Write-Host "  Local API:     python run.py"
Write-Host "  Oracle API:    deploy/oracle/README.md"
Write-Host "  Path router:   deploy/cloudflare/README.md  (wrangler deploy)"
Write-Host "  Paths:         www.txbizfinder.com/{app,radar,channel,sentinel,flood,power,map,api}"
Write-Host ""
exit 1
