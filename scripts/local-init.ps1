$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

if (!(Test-Path ".env.local")) {
    Copy-Item ".env.example" ".env.local"
    Write-Host "Created .env.local from .env.example"
    Write-Host "Edit POSTGRES_PASSWORD and DATABASE_URL in .env.local, then run .\scripts\local-migrate.ps1"
}

New-Item -ItemType Directory -Force `
    "storage/runs", `
    "storage/uploads", `
    "storage/temp" | Out-Null

if (!(Test-Path ".venv")) {
    python -m venv .venv
    Write-Host "Created .venv"
}

Write-Host "Local profile initialized."
Write-Host "Next commands:"
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host "  python -m pip install -r requirements.txt"
Write-Host "  .\scripts\local-check.ps1"
Write-Host "  .\scripts\local-migrate.ps1"
Write-Host "  .\scripts\local-api.ps1"
Write-Host "  .\scripts\local-worker.ps1"
