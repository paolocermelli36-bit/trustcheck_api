from typing import List, Dict, Any
import requests

from config import GOOGLE_API_KEY, GOOGLE_SEARCH_ENGINE_ID


def _normalize_item(item: Dict[str, Any]) -> Dict[str, str]:
    """Normalizza un singolo risultato CSE in formato pulito."""
    return {
        "title": item.get("title", "") or "",
        "snippet": item.get("snippet", "") or "",
        "url": item.get("link", "") or ""
    }


def search_web(query: str, max_results: int = 100) -> Dict[str, Any]:
    """
    Ricerca completa con Google Programmable Search Engine (CSE).
    Recupera fino a max_results risultati reali.
    """
    results: List[Dict[str, str]] = []

    start = 1  # Google parte da 1
    per_page = 10  # Google CSE restituisce max 10 risultati alla volta

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
            timeout=10
        )

        if resp.status_code != 200:
            return {
                "query": query,
                "error": f"Google error {resp.status_code}: {resp.text}",
                "results": []
            }

        data = resp.json()
        items = data.get("items", [])

        if not items:
            break

        for item in items:
            results.append(_normalize_item(item))

        # passa al successivo blocco di 10
        start += 10

    return {
        "query": query,
        "total_results": len(results),
        "results": results
    }