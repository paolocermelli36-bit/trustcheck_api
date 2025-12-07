import os
from dotenv import load_dotenv

# In locale carica il .env; su Render le variabili sono già nell’ambiente
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
# legge GOOGLE_CX (Render) oppure GOOGLE_CX_ID (tuo .env locale)
GOOGLE_CX = os.getenv("GOOGLE_CX") or os.getenv("GOOGLE_CX_ID")
# alias per non rompere eventuali import vecchi
GOOGLE_CX_ID = GOOGLE_CX


def log_google_config() -> None:
    """Solo log di servizio, niente panico se manca."""
    if GOOGLE_API_KEY and GOOGLE_CX:
        print("Google Custom Search configurato correttamente.")
    else:
        print("Google Custom Search NON configurato (manca GOOGLE_API_KEY o GOOGLE_CX).")