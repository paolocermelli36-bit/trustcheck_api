from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import log_google_config
from reputation_engine import analyze_basic, analyze_pro, SearchEngineError


class AnalyzeRequest(BaseModel):
    query: str


class AnalyzeProRequest(BaseModel):
    query: str


app = FastAPI(
    title="TrustCheck API",
    version="0.1.0",
)

# Domini autorizzati (CORS)
origins = [
    # locale
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    # dominio principale
    "https://trustcheckscan.com",
    "https://www.trustcheckscan.com",
    "https://app.trustcheckscan.com",
    # netlify diretto
    "https://stately-creponne-626be4.netlify.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    # Log di servizio per verificare le chiavi Google
    log_google_config()


@app.get("/")
async def root():
    return {"message": "TrustCheck API is running"}


@app.post("/analyze")
async def analyze_endpoint(payload: AnalyzeRequest):
    try:
        result = await analyze_basic(payload.query)
        return result
    except SearchEngineError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ✅ Alias per compatibilità con la webapp: /analyze2 fa la stessa cosa di /analyze
@app.post("/analyze2")
async def analyze2_endpoint(payload: AnalyzeRequest):
    try:
        result = await analyze_basic(payload.query)
        return result
    except SearchEngineError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze-pro")
async def analyze_pro_endpoint(payload: AnalyzeProRequest):
    try:
        result = await analyze_pro(payload.query)
        return result
    except SearchEngineError as e:
        raise HTTPException(status_code=500, detail=str(e))