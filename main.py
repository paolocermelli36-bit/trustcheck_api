from typing import Any, Dict
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from reputation_engine import analyze_reputation


class AnalyzeRequest(BaseModel):
    query: str


app = FastAPI(
    title="TrustCheck API",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # per ora tutto aperto
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> Dict[str, Any]:
    return {"status": "ok", "service": "trustcheck_api"}


@app.post("/analyze")
def analyze(req: AnalyzeRequest) -> Dict[str, Any]:
    """
    Endpoint principale: usa il motore unico.
    """
    return analyze_reputation(req.query)


@app.post("/analyze-pro")
def analyze_pro(req: AnalyzeRequest) -> Dict[str, Any]:
    """
    Per ora PRO usa lo stesso motore di /analyze,
    così l'app non va in 404.
    """
    return analyze_reputation(req.query)