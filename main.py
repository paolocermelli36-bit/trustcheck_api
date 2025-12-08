from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import log_google_config
from reputation_engine import analyze_basic, SearchEngineError


class AnalyzeRequest(BaseModel):
    query: str


app = FastAPI(
    title="TrustCheck API",
    version="0.1.0",
)

# CORS aperto per TUTTI i domini
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
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
