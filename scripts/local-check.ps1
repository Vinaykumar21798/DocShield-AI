$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

if (!(Test-Path ".env.local")) {
    throw "Missing .env.local. Run .\scripts\local-init.ps1 first, then edit the DB password."
}

$env:DOCSHIELD_ENV_FILE = ".env.local"
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (!(Test-Path $VenvPython)) {
    throw "Missing .venv Python. Run .\scripts\local-init.ps1 first."
}

Write-Host "Using DOCSHIELD_ENV_FILE=.env.local"
Write-Host "Checking local ports..."
Test-NetConnection 127.0.0.1 -Port 5432 | Select-Object ComputerName,RemoteAddress,RemotePort,TcpTestSucceeded
Test-NetConnection 127.0.0.1 -Port 6379 | Select-Object ComputerName,RemoteAddress,RemotePort,TcpTestSucceeded

Write-Host "Checking Python settings and DB login..."
$pythonCheck = @"
import spacy
from sqlalchemy import text
from core.config import settings
from core.database import engine
models = spacy.util.get_installed_models()
if "en_core_web_sm" not in models and "en_core_web_lg" not in models:
    raise RuntimeError("Missing spaCy English model; run .\\.venv\\Scripts\\python.exe -m spacy download en_core_web_sm")
print("presidio spaCy model:", "en_core_web_sm" if "en_core_web_sm" in models else "en_core_web_lg")
print("env database target:", settings.database_url.split("@")[-1])
print("env redis target:", settings.redis_url)
try:
    with engine.connect() as conn:
        print("db select 1:", conn.execute(text("select 1")).scalar())
except Exception as exc:
    print("db failed:", type(exc).__name__)
    print(str(exc).splitlines()[0])
"@
$pythonCheck | & $VenvPython -

Write-Host "Checking Ollama models..."
try {
    Invoke-RestMethod http://localhost:11434/api/tags | ConvertTo-Json -Depth 3
} catch {
    Write-Host $_.Exception.Message
}
