from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import settings
from reputation_engine import analyze_basic, analyze_pro
from search_engine import SearchEngineError

app = FastAPI(
    title="TrustCheck API",
    version="0.1.0",
)

# CORS per Flutter (web + app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # in futuro puoi restringere
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    query: str


class AnalyzeProRequest(BaseModel):
    query: str


@app.on_event("startup")
def startup_event():
    if not settings.google_api_key or not settings.google_cx_id:
        print("⚠️  Attenzione: GOOGLE_API_KEY o GOOGLE_CX_ID non sono impostate nel file .env.")
    else:
        print("✅ Google Custom Search configurato correttamente.")


@app.get("/")
def root():
    return {"status": "ok", "message": "TrustCheck API — DeepScan engine"}


# =========================
#   ENDPOINTS PRINCIPALI
# =========================

@app.post("/analyze")
def analyze(request: AnalyzeRequest):
    """
    Endpoint principale usato dalla APP.
    Ora punta direttamente alla MODALITÀ PRO (FASE 5 SAFE).
    """
    try:
        return analyze_pro(request.query)
    except SearchEngineError as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/analyze-pro")
def analyze_pro_endpoint(request: AnalyzeProRequest):
    """
    Alias esplicito PRO (stesso motore di /analyze).
    """
    try:
        return analyze_pro(request.query)
    except SearchEngineError as exc:
        raise HTTPException(status_code=500, detail=str(exc))