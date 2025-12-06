from typing import List, Dict, Any
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

    # Altra stampa autorevole (peso medio)
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
    Esegue la ricerca su Google Programmable Search Engine
    e restituisce una lista di dict {title, snippet, url}.
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

        # limite di Google: oltre 100 risulta inutile
        if start > 100:
            break

    return results


# ========= FILTRO NOME + COGNOME =========

def _normalize_name(query: str):
    """
    Ritorna (first, last, full) in minuscolo.
    """
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


def _matches_name(query: str, text: str) -> bool:
    """
    Tiene il risultato SOLO se:
    - contiene il nome completo "nome cognome", oppure
    - contiene sia nome che cognome entro una distanza ragionevole.
    """
    first, last, full = _normalize_name(query)
    if not full:
        # query vuota / strana -> tieni tutto
        return True

    text = text.lower()

    # match diretto "nome cognome"
    if full in text:
        return True

    # match "first" + "last" sparsi ma vicini
    if first and last and (first in text and last in text):
        first_idx = text.find(first)
        last_idx = text.find(last)

        if first_idx != -1 and last_idx != -1:
            # stima grezza della distanza in parole
            words_before_first = text[:first_idx].count(" ")
            words_before_last = text[:last_idx].count(" ")
            word_distance = abs(words_before_last - words_before_first)

            # se sono entro ~8 parole consideriamo rilevante
            if word_distance <= 8:
                return True

    return False


def _filter_by_name(query: str, items: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Applica il filtro nome+cognome su titolo + snippet + URL.
    """
    filtered: List[Dict[str, str]] = []

    for it in items:
        blob = f"{it.get('title', '')} {it.get('snippet', '')} {it.get('url', '')}"
        if _matches_name(query, blob):
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
    Ritorna la severity (0–3) e la scrive su item["severity"].
    """
    text = f"{item.get('title', '')} {item.get('snippet', '')}".lower()
    url = item.get("url", "")
    score = 0

    # parole chiave negative
    for kw in NEGATIVE_KEYWORDS:
        if kw in text:
            score += 1

    # domini “pesanti”
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


# ========= FUNZIONE PRINCIPALE USATA DA FASTAPI =========

def analyze_reputation(query: str, max_results: int = 100) -> Dict[str, Any]:
    """
    Funzione chiamata da /analyze.

    1) chiama Google CSE
    2) filtra i risultati per nome+cognome
    3) calcola severity e score
    4) ritorna il JSON consumato dalla tua app Flutter.
    """
    # 1) ricerca base
    raw_results = _google_search(query, max_results=max_results)

    # 2) filtro nome+cognome
    filtered_results = _filter_by_name(query, raw_results)

    total_results = len(filtered_results)

    # 3) calcolo negativi
    negative_count = 0
    severity_sum = 0

    for item in filtered_results:
        severity = _score_item(item)
        if severity > 0:
            negative_count += 1
            severity_sum += severity

    # 4) score e livello complessivo
    if negative_count == 0:
        level = "LOW"
        score = 0
    else:
        # base: numero di link * 3 + severità pesata * 5, clampato a 100
        raw_score = negative_count * 3 + severity_sum * 5
        score = min(100, raw_score)

        if score >= 70:
            level = "HIGH"
        elif score >= 35:
            level = "MEDIUM"
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