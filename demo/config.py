"""
Every setting ("knob") of the system in one place.

Values come from the .env file when present, otherwise the defaults below.
Change a knob, rebuild the index (for chunking/embedding knobs) and rerun the
eval to see what it does. That loop is how you tune a RAG system.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

# --- Paths ---------------------------------------------------------------
RAW_DIR = ROOT / "data" / "raw"        # the PDFs we search over
INDEX_DIR = ROOT / "data" / "index"    # built by src/ingest/build_index.py

# --- OpenAI ----------------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-5-mini")        # writes the final answer
REWRITE_MODEL = os.getenv("OPENAI_REWRITE_MODEL", "gpt-5-nano")  # cheap model: rewrites questions, judges eval
EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")

# --- OCR for scanned pages (see ocr_page() in src/ingest/loaders.py) ---------
OCR_LANG = os.getenv("OCR_LANG", "ara+eng")   # "ara+eng" keeps Latin codes; "ara" reads Arabic words better

# --- Chunking (rebuild the index after changing these) -----------------------
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "600"))        # max characters per chunk
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))  # characters repeated between neighbouring chunks

# --- Retrieval ---------------------------------------------------------------
TOP_K = int(os.getenv("TOP_K", "4"))                    # chunks handed to the LLM
CANDIDATES = int(os.getenv("CANDIDATES", "15"))         # how many each search method returns before fusion
RRF_K = int(os.getenv("RRF_K", "60"))                   # smoothing constant in Reciprocal Rank Fusion

# If the best semantic match is below this cosine similarity, we refuse
# WITHOUT calling the LLM. Calibrated with the eval set (see README, milestone 7).
REFUSAL_THRESHOLD = float(os.getenv("REFUSAL_THRESHOLD", "0.30"))

# The exact sentence the system says when the answer isn't in the documents.
REFUSAL_MESSAGE = "عذراً، لم أجد هذه المعلومة في المستندات المتاحة لدي."
