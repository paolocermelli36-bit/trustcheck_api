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


# ========= FILTRO NOME + COGNOME (con word boundary) =========

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


def _contains_word(text: str, word: str) -> bool:
    """
    Match su parola intera: 'oretta' NON matcha 'loretta'.
    """
    if not word:
        return False
    pattern = r"\b" + re.escape(word) + r"\b"
    return re.search(pattern, text) is not None


def _word_index(text: str, word: str) -> int:
    pattern = r"\b" + re.escape(word) + r"\b"
    m = re.search(pattern, text)
    return m.start() if m else -1


def _matches_name(query: str, text: str) -> bool:
    """
    Tiene il risultato SOLO se:
    - contiene il nome completo "nome cognome", oppure
    - contiene sia nome che cognome entro distanza ragionevole.
    """
    first, last, full = _normalize_name(query)
    if not full:
        return True  # query vuota/strana → non filtriamo

    text = text.lower()

    # match diretto "nome cognome"
    if _contains_word(text, full):
        return True

    # match "first" + "last" come parole intere
    if first and last and _contains_word(text, first) and _contains_word(text, last):
        idx_first = _word_index(text, first)
        idx_last = _word_index(text, last)

        if idx_first != -1 and idx_last != -1:
            words_before_first = text[:idx_first].count(" ")
            words_before_last = text[:idx_last].count(" ")
            word_distance = abs(words_before_last - words_before_first)

            # entro 8 parole → consideriamo rilevante
            if word_distance <= 8:
                return True

    return False


def _filter_by_name(query: str, items: List[Dict[str, str]]) -> List[Dict[str, str]]:
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