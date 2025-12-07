import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Carica variabili da .env (stessa cartella del backend)
load_dotenv()


@dataclass
class Settings:
    # === Chiavi di Google Custom Search ===
    google_api_key: str | None = os.getenv("GOOGLE_API_KEY")
    google_cx_id: str | None = os.getenv("GOOGLE_CX_ID")

    # Limiti "SAFE" (budget controllato)
    max_results_basic: int = 30        # /analyze "semplice"
    max_results_pro_safe: int = 100    # /analyze (motore DeepScan safe)
    per_query_limit_safe: int = 25     # max risultati per singola query

    # Parole chiave negative (multilingua) — FASE 5
    negative_keywords_it: tuple[str, ...] = (
        "truffa",
        "frode",
        "indagine",
        "arresto",
        "sanzione",
        "indagato",
        "inchiesta",
        "condanna",
        "riciclaggio",
    )

    negative_keywords_en: tuple[str, ...] = (
        "fraud",
        "scandal",
        "lawsuit",
        "investigation",
        "fine",
        "charged",
        "indicted",
        "money laundering",
        "class action",
    )

    negative_keywords_es: tuple[str, ...] = (
        "estafa",
        "fraude",
        "investigación",
        "demanda",
        "sanción",
        "acusado",
        "blanqueo",
    )

    # Domini "pesanti" per il ranking
    high_auth_domains: tuple[str, ...] = (
        "sec.gov",
        "justice.gov",
        "ft.com",
        "bloomberg.com",
        "reuters.com",
        "nytimes.com",
        "wsj.com",
        "apnews.com",
        "ansa.it",
        "repubblica.it",
        "corriere.it",
        "sole24ore.com",
        "consob.it",
        "bancaditalia.it",
        "ivass.it",
        "agcm.it",
        "ivass.it",
        "baFin.de",
        "amf-france.org",
        "fca.org.uk",
    )

    # Anni recenti che alzano il punteggio di rischio
    recent_years: tuple[str, ...] = ("2025", "2024", "2023", "2022")


settings = Settings()