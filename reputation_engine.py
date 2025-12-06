from typing import List, Dict, Any
import re
import requests

from config import GOOGLE_API_KEY, GOOGLE_SEARCH_ENGINE_ID


# ========= PAROLE E DOMINI NEGATIVI =========

NEGATIVE_KEYWORDS = [
    "scam", "fraud", "ponzi", "scheme", "arrest", "indicted", "charged",
    "money laundering", "laundering", "fine", "sanction", "lawsuit",
    "complaint", "investigation", "bribery", "corruption", "crime",
    "criminal", "regulator", "class action", "bankruptcy", "liquidation",
    "suspension", "revocation", "ban", "banned", "warning", "blacklist",
    "watchlist", "default", "debt collection", "foreclosure",
]

NEGATIVE_DOMAINS_WEIGHTS: Dict[str, int] = {
    # Autorità e regolatori (peso alto)
    "sec.gov": 3,
    "justice.gov": 3,
    "ftc.gov": 3,
    "consob.it": 3,
    "agcm.it": 3,
    "ivass.it": 3,
    "bancaditalia.it": 3,
    "banque-france.fr": 3,
    "amf-france.org": 3,
    "fca.org.uk": 3,
    "finma.ch": 3,
    "bafin.de": 3,

    # Stampa autorevole (peso medio)
    "reuters.com": 2,
    "bloomberg.com": 2,
    "ft.com": 2,
    "wsj.com": 2,
    "nytimes.com": 2,
    "theguardian.com": 2,
}


# ========= RICERCA SU GOOGLE CSE =========

def _google_search(query: str, max_results: int = 100) -> List[Dict[str, str]]:
    """
    Ricerca su Google Programmable Search Engine.
    Ritorna una lista di dict {title, snippet, url}.
    """
    results: List[Dict[str, str]] = []
    start = 1
    per_page = 10

    while len(results) < max_results:
        num = min(per_page, max_results - len(results))

        params = {
            "key": GOOGLE_API_KEY,
            "cx": GOOGLE_SEARCH_ENGINE_ID,
            "q": query,
            "start": start,
            "num": num,
        }

        resp = requests.get(
            "https://www.googleapis.com/customsearch/v1",
            params=params,
            timeout=10,
        )

        if resp.status_code != 200:
            break

        data = resp.json()
        items = data.get("items", [])

        for item in items:
            results.append(
                {
                    "title": item.get("title", "") or "",
                    "snippet": item.get("snippet", "") or "",
                    "url": item.get("link", "") or "",
                }
            )

        if not items:
            break

        start += len(items)

        if start > 100:
            break

    return results


# ========= NORMALIZZAZIONE NOME =========

def _normalize_name(query: str):
    tokens = [t.strip().lower() for t in query.split() if t.strip()]
    if len(tokens) >= 2:
        first = tokens[0]
        last = tokens[-1]
        full = f"{first} {last}"
        return first, last, full
    elif len(tokens) == 1:
        return tokens[0], "", tokens[0]
    else:
        return "", "", ""


def _clean_for_match(text: str) -> str:
    """
    Porta a lower case e sostituisce - e _ con spazio (per le URL).
    """
    text = text.lower()
    text = text.replace("-", " ").replace("_", " ")
    return text


def _matches_name(query: str, title: str, snippet: str, url: str) -> bool:
    """
    FILTRO SUPER STRETTO:
    - per query con nome + cognome, accettiamo SOLO se
      il pattern appare esattamente (contiguo) nel testo o nell'URL.
    """
    first, last, full = _normalize_name(query)

    # Query strana/vuota → non filtriamo
    if not full:
        return True

    # Costruiamo le varianti accettate
    patterns = [
        full,                      # "oretta croce"
        f"{last} {first}",         # "croce oretta"
        f"{last}, {first}",        # "croce, oretta"
    ]

    text_blob = _clean_for_match(f"{title} {snippet}")
    url_blob = _clean_for_match(url)

    for p in patterns:
        if p in text_blob or p in url_blob:
            return True

    # Se non troviamo la sequenza esatta, SCARTIAMO
    return False


def _filter_by_name(query: str, items: List[Dict[str, str]]) -> List[Dict[str, str]]:
    filtered: List[Dict[str, str]] = []

    for it in items:
        title = it.get("title", "")
        snippet = it.get("snippet", "")
        url = it.get("url", "")
        if _matches_name(query, title, snippet, url):
            filtered.append(it)

    return filtered


# ========= CALCOLO SEVERITÀ =========

def _domain_from_url(url: str) -> str:
    try:
        without_proto = url.split("://", 1)[-1]
        host = without_proto.split("/", 1)[0]
        return host.lower()
    except Exception:
        return ""


def _score_item(item: Dict[str, str]) -> int:
    """
    Ritorna la severity (0–3) e la scrive in item["severity"].
    """
    text = f"{item.get('title', '')} {item.get('snippet', '')}".lower()
    url = item.get("url", "")
    score = 0

    for kw in NEGATIVE_KEYWORDS:
        if kw in text:
            score += 1

    domain = _domain_from_url(url)
    for dom, weight in NEGATIVE_DOMAINS_WEIGHTS.items():
        if dom in domain:
            score += weight

    if score >= 6:
        severity = 3
    elif score >= 3:
        severity = 2
    elif score >= 1:
        severity = 1
    else:
        severity = 0

    item["severity"] = severity
    return severity


# ========= FUNZIONE PRINCIPALE =========

def analyze_reputation(query: str, max_results: int = 100) -> Dict[str, Any]:
    """
    Funzione usata da /analyze e /analyze-pro.
    """
    raw_results = _google_search(query, max_results=max_results)
    filtered_results = _filter_by_name(query, raw_results)

    total_results = len(filtered_results)

    negative_count = 0
    severity_sum = 0
    for item in filtered_results:
        sev = _score_item(item)
        if sev > 0:
            negative_count += 1
            severity_sum += sev

    if negative_count == 0:
        level = "LOW"
        score = 0
    else:
        raw_score = negative_count * 3 + severity_sum * 5
        score = min(100, raw_score)

        if score >= 70:
            level = "HIGH"
        elif score >= 35:
            level = "MEDIUM"
            # sotto 35 → LOW

        else:
            level = "LOW"

    return {
        "query": query,
        "score": score,
        "level": level,
        "total_results": total_results,
        "negative_results": negative_count,
        "results": filtered_results,
    }