$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

docker compose `
    -p docshield-ai-live `
    -f docker-compose.yml `
    -f docker-compose.local-gui.yml `
    down
