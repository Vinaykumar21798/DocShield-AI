$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

if (!(Test-Path ".env.local")) {
    throw "Missing .env.local. Run .\scripts\local-init.ps1 first, then edit the DB password."
}

$env:DOCSHIELD_ENV_FILE = ".env.local"
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
