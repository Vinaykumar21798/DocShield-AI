$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

if (!(Test-Path ".env.local")) {
    throw "Missing .env.local. Run .\scripts\local-init.ps1 first, then edit the DB password."
}

$env:DOCSHIELD_ENV_FILE = ".env.local"
python -m alembic upgrade head
