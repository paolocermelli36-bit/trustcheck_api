from typing import List, Dict, Any
import httpx

from config import GOOGLE_API_KEY, GOOGLE_CX_ID


class SearchEngineError(Exception):
    """Errore generico motore di ricerca."""
    pass


async def google_custom_search(query: str, max_results: int = 30) -> List[Dict[str, Any]]:
    """
    Chiama l'API Google Custom Search.
    Ritorna una lista di item (title, link, snippet, ecc.).
    """
    if not GOOGLE_API_KEY or not GOOGLE_CX_ID:
        raise SearchEngineError(
            "Google Custom Search non configurato (GOOGLE_API_KEY o GOOGLE_CX_ID mancanti)."
        )

    all_items: List[Dict[str, Any]] = []
    start = 1  # Google usa start=1, 11, 21, ...

    async with httpx.AsyncClient(timeout=20.0) as client:
        while len(all_items) < max_results and start <= 91:
            params = {
                "key": GOOGLE_API_KEY,
                "cx": GOOGLE_CX_ID,
                "q": query,
                "start": start,
                "num": min(10, max_results - len(all_items)),
            }
            resp = await client.get("https://www.googleapis.com/customsearch/v1", params=params)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("items", [])
            if not items:
                break

            all_items.extend(items)
            start += 10

    return all_items