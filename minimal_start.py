"""Minimal VERA Start - nur FastAPI ohne Lifespan"""
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="VERA Minimal")

@app.get("/health")
def health():
    return {"status": "ok", "mode": "minimal"}

@app.get("/")
def root():
    return {"service": "VERA Office", "version": "minimal", "status": "running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
