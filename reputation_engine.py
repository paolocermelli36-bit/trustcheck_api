from __future__ import annotations

from typing import Dict, List, Tuple

from config import settings
from search_engine import google_custom_search, SearchEngineError


def _clean_query(raw: str) -> str:
    q = (raw or "").strip()
    # Togliamo doppi spazi e virgolette strane
    q = q.replace("\n", " ").replace("\r", " ")
    while "  " in q:
        q = q.replace("  ", " ")
    q = q.replace('"', " ")
    return q


# =========================
#   COSTRUZIONE DELLE QUERY
# =========================

def build_queries_base(raw_query: str) -> List[str]:
    """
    Filtro 1–2: pulizia nome/brand + query base.
    """
    cleaned = _clean_query(raw_query)
    if not cleaned:
        raise ValueError("Query vuota.")

    base = f'"{cleaned}"'
    return [base]


def build_queries_pro(raw_query: str) -> List[str]:
    """
    FASE 5 SAFE — multi-lingua + query estese.

    Strategia:
    - Query base (neutra) = DeepScan "panoramica"
    - Query IT con negative
    - Query EN con negative
    - Query ES con negative

    Totale massimo: 4 query (SAFE).
    """
    cleaned = _clean_query(raw_query)
    if not cleaned:
        raise ValueError("Query vuota.")

    base = f'"{cleaned}"'

    neg_it = " OR ".join(settings.negative_keywords_it)
    neg_en = " OR ".join(settings.negative_keywords_en)
    neg_es = " OR ".join(settings.negative_keywords_es)

    q_base = base
    q_it = f'{base} ({neg_it})'
    q_en = f'{base} ({neg_en})'
    q_es = f'{base} ({neg_es})'

    return [q_base, q_it, q_en, q_es]


# =========================
#   RANKING & CLASSIFICA
# =========================

def _is_recent(text: str) -> bool:
    t = text.lower()
    return any(year in t for year in settings.recent_years)


def _has_negative_kw(text: str) -> bool:
    t = text.lower()
    for kw in (
        *settings.negative_keywords_it,
        *settings.negative_keywords_en,
        *settings.negative_keywords_es,
    ):
        if kw.lower() in t:
            return True
    return False


def _domain_score(url: str) -> int:
    url_l = url.lower()
    for dom in settings.high_auth_domains:
        if dom in url_l:
            return 2  # autorità/media forte
    if ".gov" in url_l or ".gouv" in url_l:
        return 2
    if ".int" in url_l or ".eu" in url_l:
        return 1
    return 0


def _classify_item(item: Dict) -> Tuple[str, int]:
    """
    Restituisce (severity, score numerico 0-4).
    """
    url = item.get("link", "") or ""
    title = item.get("title", "") or ""
    snippet = item.get("snippet", "") or ""

    text = f"{title} {snippet}"

    score = 0

    if _has_negative_kw(text):
        score += 1

    if _is_recent(text):
        score += 1

    score += _domain_score(url)

    # Mappa score -> severity
    if score >= 4:
        return "critical", score
    if score == 3:
        return "high", score
    if score == 2:
        return "medium", score
    return "low", score


def _deduplicate(items: List[Dict]) -> List[Dict]:
    """
    Deduplica i risultati per URL.
    """
    seen = set()
    deduped = []
    for it in items:
        url = it.get("link")
        if not url:
            continue
        if url in seen:
            continue
        seen.add(url)
        deduped.append(it)
    return deduped


def _aggregate(items: List[Dict]) -> Dict:
    """
    Calcola contatori, score e livello finale.
    """
    total = len(items)
    if total == 0:
        return {
            "total_results": 0,
            "negative_results": 0,
            "score": 0,
            "level": "LOW",
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "results": [],
        }

    critical = high = medium = low = 0
    negative_results = 0
    total_risk_score = 0

    enriched_results = []

    for it in items:
        severity, s = _classify_item(it)
        it_with_sev = dict(it)
        it_with_sev["severity"] = severity
        it_with_sev["risk_score"] = s
        enriched_results.append(it_with_sev)

        total_risk_score += s

        if severity == "critical":
            critical += 1
            negative_results += 1
        elif severity == "high":
            high += 1
            negative_results += 1
        elif severity == "medium":
            medium += 1
            negative_results += 1
        else:
            low += 1

    # Score 0–100, normalizzato
    max_possible = total * 4
    if max_possible == 0:
        final_score = 0
    else:
        final_score = int((total_risk_score / max_possible) * 100)

    if final_score >= 70:
        level = "HIGH"
    elif final_score >= 40:
        level = "MEDIUM"
    else:
        level = "LOW"

    return {
        "total_results": total,
        "negative_results": negative_results,
        "score": final_score,
        "level": level,
        "critical": critical,
        "high": high,
        "medium": medium,
        "low": low,
        "results": enriched_results,
    }


# =========================
#   ENTRY POINT PUBBLICI
# =========================

def analyze_basic(query: str) -> Dict:
    """
    Modalità "base" (usiamo comunque DeepScan ma con meno risultati).
    """
    queries = build_queries_base(query)
    raw_items = google_custom_search(queries, total_limit=settings.max_results_basic)
    deduped = _deduplicate(raw_items)
    return _aggregate(deduped)


def analyze_pro(query: str) -> Dict:
    """
    Modalità PRO — FASE 5 SAFE:
    - multi-query
    - multi-lingua (IT/EN/ES)
    - ranking negativo
    """
    queries = build_queries_pro(query)
    raw_items = google_custom_search(queries, total_limit=settings.max_results_pro_safe)
    deduped = _deduplicate(raw_items)
    return _aggregate(deduped)