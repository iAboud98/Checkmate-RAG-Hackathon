"""Thin wrapper around the OpenAI chat API that also records token usage (for cost per answer)."""

import os

from src.openai_client import get_client

# Reasoning models (gpt-5*, o*) "think" before answering. "low" keeps them fast
# enough for a chat demo. Other models don't accept this parameter, so we only
# send it to reasoning models.
REASONING_EFFORT = os.getenv("OPENAI_REASONING_EFFORT", "low")


def chat(model: str, messages: list[dict]) -> dict:
    params = {"model": model, "messages": messages}
    if REASONING_EFFORT and model.startswith(("gpt-5", "o")):
        params["reasoning_effort"] = REASONING_EFFORT

    response = get_client().chat.completions.create(**params)
    usage = response.usage
    return {
        "text": (response.choices[0].message.content or "").strip(),
        "input_tokens": usage.prompt_tokens if usage else 0,
        "output_tokens": usage.completion_tokens if usage else 0,
    }
