"""One shared OpenAI client for the whole app. The key comes from .env, never from code."""

from functools import lru_cache

from openai import OpenAI

from config import OPENAI_API_KEY


@lru_cache(maxsize=1)
def get_client() -> OpenAI:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is missing. Copy .env.example to .env and put your key in it.")
    return OpenAI(api_key=OPENAI_API_KEY)
