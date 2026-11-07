"""Lesson B1: list the models your OpenAI key can use, before choosing them in .env."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.openai_client import get_client  # noqa: E402

ids = sorted(m.id for m in get_client().models.list())
for prefix in ("gpt-", "o", "text-embedding"):
    print(f"\n{prefix}*:", ", ".join(i for i in ids if i.startswith(prefix) and "-20" not in i))
