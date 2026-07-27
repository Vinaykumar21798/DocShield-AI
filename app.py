from fastapi import FastAPI

app = FastAPI(
    title="PII-PHI Document Intelligence PoC",
    description="AI-powered Document Intelligence Platform",
    version="1.0.0"
)


@app.on_event("startup")
def startup_validation():
    from database.session import run_startup_validation
    run_startup_validation()


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