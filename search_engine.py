from typing import List, Dict, Any
import requests

from config import GOOGLE_API_KEY, GOOGLE_SEARCH_ENGINE_ID


def _normalize_item(item: Dict[str, Any]) -> Dict[str, str]:
    """Normalizza un singolo risultato di Google CSE in un formato semplice."""
    return {
        "title": item.get("title", "") or "",
        "snippet": item.get("snippet", "") or "",
        "url": item.get("link", "") or "",
    }


def search_web(query: str, max_results: int = 10) -> Dict[str, Any]:
    """
    Ricerca base su Google Programmable Search Engine.
    Ritorna al massimo max_results risultati normalizzati.
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
        resp = requests.get("https://www.googleapis.com/customsearch/v1", params=params, timeout=10)
        if resp.status_code != 200:
            break

        data = resp.json()
        items = data.get("items") or []
        if not items:
            break

        for raw in items:
            results.append(_normalize_item(raw))
            if len(results) >= max_results:
                break

        # Google CSE usa start come indice (1-based); aumentiamo di per_page
        start += per_page

    return {
        "query": query,
        "results": results,
        "results_count": len(results),
        "provider": "google_cse",
    }


def pro_multi_search(query: str, max_total: int = 150) -> List[Dict[str, Any]]:
    """
    Modalita PRO:
    - esegue piu query mirate su Google CSE
    - deduplica per URL
    - filtra per presenza del nome/cognome nel titolo/snippet
    - restituisce al massimo max_total risultati normalizzati
      con un campo extra 'source_query' che indica da quale sotto-query provengono.
    """
    # token del nome (es. "paolo", "cermelli")
    name_tokens = [t for t in query.lower().split() if len(t) > 2]

    # definizione delle sotto-query PRO
    base = query.strip()
    sub_queries: List[Dict[str, str]] = [
        {"label": "base", "q": base},
        {
            "label": "fraud",
            "q": f"{base} truffa frode scam fraud",
        },
        {
            "label": "investigation",
            "q": f"{base} indagine investigation sanzione fine penalty enforcement",
        },
        {
            "label": "crime",
            "q": f"{base} arrestato arrest charged indicted criminal",
        },
        {
            "label": "insolvency",
            "q": f"{base} fallimento insolvency insolvenza default liquidation",
        },
    ]

    all_results: List[Dict[str, Any]] = []
    seen_urls: set[str] = set()

    # limitiamo un po per query secondaria
    per_secondary = 25

    for idx, sq in enumerate(sub_queries):
        if len(all_results) >= max_total:
            break

        # base: permettiamo fino a max_total (ci pensa search_web a fermarsi)
        if sq["label"] == "base":
            want = max_total
        else:
            want = min(per_secondary, max_total - len(all_results))

        data = search_web(sq["q"], max_results=want)
        items = data.get("results", [])

        for item in items:
            url = item.get("url") or ""
            if not url:
                continue
            if url in seen_urls:
                continue

            title = item.get("title", "") or ""
            snippet = item.get("snippet", "") or ""
            text = (title + " " + snippet).lower()

            # filtro: il nome deve comparire nel testo per considerarlo rilevante
            if name_tokens and not any(t in text for t in name_tokens):
                continue

            seen_urls.add(url)
            enriched = dict(item)
            enriched["source_query"] = sq["label"]
            all_results.append(enriched)

            if len(all_results) >= max_total:
                break

    return all_results