$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

if (!(Test-Path ".env.local")) {
    throw "Missing .env.local. Run .\scripts\local-init.ps1 first, then edit the DB password."
}

$env:DOCSHIELD_ENV_FILE = ".env.local"

Write-Host "Using DOCSHIELD_ENV_FILE=.env.local"
Write-Host "Checking local ports..."
Test-NetConnection 127.0.0.1 -Port 5432 | Select-Object ComputerName,RemoteAddress,RemotePort,TcpTestSucceeded
Test-NetConnection 127.0.0.1 -Port 6379 | Select-Object ComputerName,RemoteAddress,RemotePort,TcpTestSucceeded

Write-Host "Checking Python settings and DB login..."
$pythonCheck = @"
from sqlalchemy import text
from core.config import settings
from core.database import engine
print("env database target:", settings.database_url.split("@")[-1])
print("env redis target:", settings.redis_url)
try:
    with engine.connect() as conn:
        print("db select 1:", conn.execute(text("select 1")).scalar())
except Exception as exc:
    print("db failed:", type(exc).__name__)
    print(str(exc).splitlines()[0])
"@
$pythonCheck | python -

Write-Host "Checking Ollama models..."
try {
    Invoke-RestMethod http://localhost:11434/api/tags | ConvertTo-Json -Depth 3
} catch {
    Write-Host $_.Exception.Message
}
