import os
from dotenv import load_dotenv

# Carica il file .env in locale; su Render le variabili sono già nell'ambiente.
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CX_ID = os.getenv("GOOGLE_CX_ID")


def log_google_config() -> None:
    """Solo log di servizio, niente panico se manca."""
    if GOOGLE_API_KEY and GOOGLE_CX_ID:
        print("Google Custom Search configurato correttamente.")
    else:
        print("Google Custom Search NON configurato (manca GOOGLE_API_KEY o GOOGLE_CX_ID).")