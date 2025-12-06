import os
import math
from typing import List

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ------------------------------------------------------------
# FastAPI app
# ------------------------------------------------------------

app = FastAPI(title="TrustCheck API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # app Flutter + web
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------
# Modelli Pydantic
# ------------------------------------------------------------


class AnalyzeRequest(BaseModel):
    query: str
    max_results: int = 100  # massimo risultati "buoni" dopo il filtro


class ResultItem(BaseModel):
    title: str
    url: str
    snippet: str
    severity: int


class AnalyzeResponse(BaseModel):
    query: str
    score: int
    level: str
    total_results: int
    results: List[ResultItem]


# ------------------------------------------------------------
# Config: Google Custom Search
# ------------------------------------------------------------

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CX = os.getenv("GOOGLE_CX")

if not GOOGLE_API_KEY or not GOOGLE_CX:
    print("⚠️  WARNING: GOOGLE_API_KEY or GOOGLE_CX not set in environment.")


GOOGLE_SEARCH_URL = "https://www.googleapis.com/customsearch/v1"

# ------------------------------------------------------------
# Liste molto semplici per severità (da raffinare in futuro)
# ------------------------------------------------------------

NEGATIVE_KEYWORDS = [
    "arrest",
    "indicted",
    "scandal",
    "fraud",
    "scam",
    "lawsuit",
    "fine",
    "penalty",
    "sanction",
    "investigation",
    "money laundering",
    "bribery",
    "corruption",
    "revocation",
    "bankruptcy",
    "liquidation",
    "criminal",
    "terror",
    "sex offender",
    "pedophile",
    "child abuse",
    "hacker",
    "breach",
    "data leak",
    # italiano
    "arresto",
    "indagato",
    "inchiesta",
    "indagine",
    "truffa",
    "frode",
    "truffatore",
    "denuncia",
    "condanna",
    "sanzione",
    "multa",
    "revoca",
    "fallimento",
    "liquidazione",
    "pignoramento",
    "estorsione",
    "corruzione",
    "riciclaggio",
    "usura",
    "revocata",
]

NEGATIVE_DOMAINS = [
    "sec.gov",
    "justice.gov",
    "ftc.gov",
    "ofac",
    "europa.eu",
    "eprs.europa.eu",
    "bancaditalia.it",
    "consob.it",
    "ivass.it",
    "agcm.it",
    "gdf.it",
    "poliziadistato.it",
    "carabinieri.it",
    "reuters.com",
    "bloomberg.com",
    "ft.com",
    "forbes.com",
]


# ------------------------------------------------------------
# Funzioni di utilità
# ------------------------------------------------------------


def normalize_text(value: str) -> str:
    return (value or "").strip().lower()


def extract_significant_parts(query: str) -> List[str]:
    """
    Togliamo parole troppo corte o inutili (“di”, “spa”, “srl”, ecc.)
    e teniamo solo i pezzi "seri" (nome+ cognome, nome azienda).
    """
    q = normalize_text(query)
    raw = q.split()

    STOP_WORDS = {
        "spa",
        "srl",
        "ag",
        "sa",
        "llc",
        "inc",
        "plc",
        "the",
        "and",
        "di",
        "de",
        "la",
        "le",
        "il",
        "lo",
        "of",
        "group",
        "holding",
        "ltd",
        "limited",
    }

    parts: List[str] = []
    for p in raw:
        if len(p) <= 2:
            continue
        if p in STOP_WORDS:
            continue
        parts.append(p)

    return parts


def is_relevant_result(query: str, title: str, snippet: str) -> bool:
    """
    Tiene SOLO i risultati dove c'è almeno "nome + cognome" (o comunque
    tutte le parole significative della query) nel titolo o nello snippet.

    Esempio:
    - query: "Oretta Croce"
    - passa: risultati con "Oretta Croce" o comunque con "oretta" E "croce"
    - bocciati: cose con solo "Croce" o solo "Oretta"
    """
    q = normalize_text(query)
    if not q:
        return False

    text = normalize_text(f"{title} {snippet}")

    # 1) se c'è la frase completa, è ok
    if q in text:
        return True

    # 2) altrimenti richiediamo che tutte le parole significative siano presenti
    parts = extract_significant_parts(q)
    if not parts:
        return False

    return all(p in text for p in parts)


def compute_severity(title: str, snippet: str, url: str) -> int:
    """
    Piccolo score per ogni risultato. Non è il sistema definitivo,
    ma ci dà un'idea di "quanto è brutto" il link.
    """
    text = normalize_text(f"{title} {snippet}")
    link = normalize_text(url)

    score = 0

    # parole negative nel testo
    for kw in NEGATIVE_KEYWORDS:
        if kw in text:
            score += 2

    # domini "pesanti"
    for dom in NEGATIVE_DOMAINS:
        if dom in link:
            score += 3

    # se non abbiamo trovato niente, ma il risultato è passato il filtro
    # gli diamo comunque 1 punto per dire "esiste, ma non sembra gravissimo"
    if score == 0:
        score = 1

    # limitiamo un po' lo score per singolo link
    return min(score, 10)


def level_from_score(score: int) -> str:
    """
    Converte lo score totale in livello.
    Tuning grezzo ma chiaro.
    """
    if score <= 0:
        return "NONE"
    if score < 20:
        return "LOW"
    if score < 60:
        return "MEDIUM"
    return "HIGH"


# ------------------------------------------------------------
# Endpoint principale /analyze
# ------------------------------------------------------------


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    query = (request.query or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    if not GOOGLE_API_KEY or not GOOGLE_CX:
        raise HTTPException(
            status_code=500,
            detail="GOOGLE_API_KEY or GOOGLE_CX not configured on server.",
        )

    # Quanti risultati MASSIMI vogliamo dopo il filtro
    target_results = max(1, min(request.max_results, 200))

    per_page = 10  # limite API Google
    max_pages = math.ceil(target_results / per_page)

    collected: List[ResultItem] = []
    seen_links: set[str] = set()

    for page in range(max_pages):
        start = page * per_page + 1

        params = {
            "key": GOOGLE_API_KEY,
            "cx": GOOGLE_CX,
            "q": query,
            "num": per_page,
            "start": start,
            "hl": "en",  # lingua di interfaccia, non blocca l'italiano
        }

        try:
            resp = requests.get(GOOGLE_SEARCH_URL, params=params, timeout=10)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=502,
                detail=f"Error contacting Google Search API: {exc}",
            ) from exc

        if resp.status_code != 200:
            # se Google risponde male, ci fermiamo
            break

        data = resp.json()
        items = data.get("items", [])
        if not items:
            break

        for item in items:
            title = item.get("title", "")
            link = item.get("link", "")
            snippet = item.get("snippet", "")

            if not link:
                continue

            # dedup per URL
            if link in seen_links:
                continue

            # filtro "nome + cognome" / parole significative
            if not is_relevant_result(query, title, snippet):
                continue

            seen_links.add(link)
            severity = compute_severity(title, snippet, link)

            collected.append(
                ResultItem(
                    title=title,
                    url=link,
                    snippet=snippet,
                    severity=severity,
                )
            )

            if len(collected) >= target_results:
                break

        if len(collected) >= target_results:
            break

    total_score = sum(item.severity for item in collected)
    level = level_from_score(total_score)

    return AnalyzeResponse(
        query=query,
        score=total_score,
        level=level,
        total_results=len(collected),
        results=collected,
    )


@app.get("/")
def root():
    return {"status": "ok", "message": "TrustCheck API"}