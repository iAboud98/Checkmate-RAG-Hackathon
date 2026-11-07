"""All settings ("knobs") in one place. Values come from .env when present, else these defaults."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

# --- Paths -------------------------------------------------------------------
DOCS_DIR = ROOT / os.getenv("DOCS_DIR", "data/raw")     # the documents we answer from
INDEX_DIR = ROOT / "data" / "index"                     # built by: python -m src.ingest.build_index
DB_PATH = ROOT / "data" / "app.db"                      # chat history + analytics (SQLite)
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".md", ".txt"}

# --- OpenAI ------------------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-5.4-mini")       # writes answers (3.7 s vs 5.2 s for gpt-5-mini, same answer)
REWRITE_MODEL = os.getenv("OPENAI_REWRITE_MODEL", "gpt-5-nano")   # rewrites queries
JUDGE_MODEL = os.getenv("OPENAI_JUDGE_MODEL", CHAT_MODEL)         # grades the eval
VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", CHAT_MODEL)       # OCR_ENGINE=vision
EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")
REASONING_EFFORT = os.getenv("OPENAI_REASONING_EFFORT", "low")    # only sent to gpt-5*/o* models

# Optional prices (USD per 1M tokens) for the analytics cost estimate. Leave empty to show tokens only.
PRICE_INPUT_PER_1M = float(os.getenv("PRICE_INPUT_PER_1M") or 0)
PRICE_OUTPUT_PER_1M = float(os.getenv("PRICE_OUTPUT_PER_1M") or 0)

# --- Ingestion -----------------------------------------------------------------
OCR_ENGINE = os.getenv("OCR_ENGINE", "tesseract")   # "tesseract" (offline) or "vision" (LLM reads the page image; keeps tables)
OCR_LANG = os.getenv("OCR_LANG", "ara+eng")         # tesseract: "ara+eng" keeps Latin codes, "ara" reads Arabic words better
MIN_TEXT_CHARS = 20                                 # fewer chars on a PDF page = scanned image -> OCR

# Section-based chunking: one chunk per section. This is ONLY a safety net for very long
# sections: they get split at their numbered clauses / paragraphs, keeping the section title.
MAX_SECTION_CHARS = int(os.getenv("MAX_SECTION_CHARS", "2500"))

# --- Retrieval ---------------------------------------------------------------
TOP_K = int(os.getenv("TOP_K", "4"))
CANDIDATES = int(os.getenv("CANDIDATES", "15"))
RRF_K = int(os.getenv("RRF_K", "60"))
REFUSAL_THRESHOLD = float(os.getenv("REFUSAL_THRESHOLD", "0.30"))  # calibrate: python eval/run_eval.py --calibrate

# --- Auth ----------------------------------------------------------------------
# Users as "username:role:hash", comma separated. Make a hash with: python scripts/hash_password.py
AUTH_USERS = os.getenv("AUTH_USERS", "")
AUTH_ENABLED = os.getenv("AUTH_ENABLED", "true").lower() == "true"
