from __future__ import annotations

import time
from typing import List, Dict

import httpx

from config import settings


class SearchEngineError(Exception):
    """Errore generico del motore di ricerca."""
    pass


def _ensure_config_ok() -> None:
    if not settings.google_api_key or not settings.google_cx_id:
        raise SearchEngineError(
            "GOOGLE_API_KEY o GOOGLE_CX_ID non configurati sul server."
        )


def _google_single_query(query: str, start: int, num: int) -> List[Dict]:
    """
    Esegue UNA chiamata a Google Custom Search per una singola query.
    """
    _ensure_config_ok()

    params = {
        "key": settings.google_api_key,
        "cx": settings.google_cx_id,
        "q": query,
        "start": start,
        "num": num,
    }

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get("https://www.googleapis.com/customsearch/v1", params=params)
    except httpx.RequestError as exc:
        raise SearchEngineError(f"Errore di rete verso Google: {exc}") from exc

    if resp.status_code != 200:
        raise SearchEngineError(
            f"Google API ha risposto con status {resp.status_code}: {resp.text}"
        )

    data = resp.json()
    return data.get("items", []) or []


def google_custom_search(queries: List[str], total_limit: int) -> List[Dict]:
    """
    FASE 5 SAFE:
    - accetta una lista di query (multi-lingua, negative, ecc.)
    - distribuisce il budget totale tra le query
    - unisce e restituisce TUTTI i risultati (senza dedup: ci pensa il motore reputazionale)
    """
    if not queries:
        return []

    # Budget massimo totale
    total_limit = max(1, min(total_limit, settings.max_results_pro_safe))

    # Risultati per query, limitati dal per_query_limit_safe
    per_query = max(1, min(settings.per_query_limit_safe, total_limit // len(queries)))
    if per_query < 1:
        per_query = 1

    all_items: List[Dict] = []

    for q in queries:
        # Sempre partire da 1 (prima pagina)
        try:
            items = _google_single_query(q, start=1, num=per_query)
            all_items.extend(items)
        except SearchEngineError as exc:
            # Se una query fallisce, continuiamo con le altre
            print(f"[google_custom_search] Query fallita '{q}': {exc}")
        # Throttle minimo per sicurezza (rate-limit friendly)
        time.sleep(0.2)

    return all_items