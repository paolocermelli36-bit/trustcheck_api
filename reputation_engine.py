from typing import List, Dict, Any, Tuple
import re

from search_engine import google_custom_search, SearchEngineError


# Parole chiave molto rozze per capire se un risultato è negativo
NEGATIVE_KEYWORDS = [
    "scandal", "fraud", "lawsuit", "fine", "penalty", "indicted", "charged",
    "guilty", "money laundering", "investigation", "probe", "sanction",
    "misconduct", "complaint", "class action", "crime", "illegal", "controversy",
    "ban", "warning", "cease and desist", "settlement",
    "sanzione", "indagine", "procedimento", "condanna", "arresto",
    "truffa", "frode", "riciclaggio", "revoca", "radiazione",
]


def _is_negative(text: str) -> Tuple[bool, int]:
    """
    Ritorna (is_negative, severity) con severity 1=low,2=medium,3=high.
    Logica spartana ma sufficiente per test.
    """
    t = text.lower()
    score = 0

    for kw in NEGATIVE_KEYWORDS:
        if kw in t:
            # parole più forti => +2
            if any(w in kw for w in ["fraud", "truffa", "money laundering", "riciclaggio",
                                     "indicted", "charged", "condanna", "arresto",
                                     "class action", "crime", "illegal"]):
                score += 2
            else:
                score += 1

    if score == 0:
        return False, 0
    if score >= 4:
        return True, 3
    if score >= 2:
        return True, 2
    return True, 1


def _build_response(query: str, items: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(items)
    negatives: List[Dict[str, Any]] = []

    critical = high = medium = low = 0

    for item in items:
        title = item.get("title", "")
        snippet = item.get("snippet", "")
        link = item.get("link", "")

        is_neg, sev = _is_negative(f"{title} {snippet}")
        if not is_neg:
            continue

        if sev == 3:
            high += 1  # usiamo solo high/medium/low, critical=0 in questa versione
        elif sev == 2:
            medium += 1
        else:
            low += 1

        negatives.append(
            {
                "title": title,
                "link": link,
                "snippet": snippet,
                "severity": sev,
            }
        )

    negative_count = len(negatives)

    # Calcolo score grezzo
    score = min(100, negative_count * 5 + high * 10 + medium * 5)

    if score >= 70:
        level = "HIGH"
    elif score >= 40:
        level = "MEDIUM"
    elif score > 0:
        level = "LOW"
    else:
        level = "LOW"

    return {
        "total_results": total,
        "negative_results": negative_count,
        "score": score,
        "level": level,
        "critical": 0,
        "high": high,
        "medium": medium,
        "low": low,
        "results": negatives,
    }


async def analyze_basic(query: str) -> Dict[str, Any]:
    """
    Modalità standard: una query secca.
    """
    items = await google_custom_search(query, max_results=30)
    return _build_response(query, items)


async def analyze_pro(query: str) -> Dict[str, Any]:
    """
    Modalità PRO: stessa logica ma con multi-query (nome + nome "scandal" ecc.).
    """
    # Query varianti base
    variants = [
        query,
        f"{query} scandal",
        f"{query} investigation",
        f"{query} fraud",
        f"{query} lawsuit",
        f"{query} sanzione",
        f"{query} indagine",
    ]

    all_items: List[Dict[str, Any]] = []
    seen_links = set()

    for q in variants:
        try:
            items = await google_custom_search(q, max_results=20)
        except SearchEngineError:
            # Se qualcosa va storto, ci fermiamo e ritorniamo quello che abbiamo
            break

        for it in items:
            link = it.get("link")
            if not link or link in seen_links:
                continue
            seen_links.add(link)
            all_items.append(it)

    return _build_response(query, all_items)