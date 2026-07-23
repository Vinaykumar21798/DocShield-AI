from fastapi import FastAPI

app = FastAPI(
    title="PII-PHI Document Intelligence PoC",
    description="AI-powered Document Intelligence Platform",
    version="1.0.0"
)


@app.get("/")
async def root():
    return {
        "status": "running",
        "message": "PII-PHI Document Intelligence PoC",
        "version": "1.0.0"
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy"
    }