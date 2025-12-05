from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from search_engine import search_web
from reputation_engine import analyze_reputation, analyze_reputation_pro


app = FastAPI(title="MicroboLabs TrustCheck API")


# CORS: permettiamo richieste dal frontend Flutter web (localhost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "http://localhost", "http://127.0.0.1"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    query: str
    max_results: int | None = 10


class AnalyzeRequest(BaseModel):
    query: str


class AnalyzeProRequest(BaseModel):
    query: str
    max_total: int | None = 150


@app.post("/search")
def search(req: SearchRequest):
    max_results = req.max_results or 10
    return search_web(req.query, max_results=max_results)


@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    return analyze_reputation(req.query)


@app.post("/analyze-pro")
def analyze_pro(req: AnalyzeProRequest):
    max_total = req.max_total or 150
    return analyze_reputation_pro(req.query, max_total=max_total)