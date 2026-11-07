"""
Thin wrapper around OpenAI chat, with and without streaming, recording token usage.
Lesson B2: never send `temperature` (reasoning models reject it); send
`reasoning_effort` only to reasoning models (gpt-5*, o*), which reject it otherwise.
"""

from collections.abc import Iterator

from config import REASONING_EFFORT
from src.openai_client import get_client


def _params(model: str, messages: list[dict]) -> dict:
    params = {"model": model, "messages": messages}
    if REASONING_EFFORT and model.startswith(("gpt-5", "o")):
        params["reasoning_effort"] = REASONING_EFFORT
    return params


def chat(model: str, messages: list[dict]) -> dict:
    response = get_client().chat.completions.create(**_params(model, messages))
    usage = response.usage
    return {
        "text": (response.choices[0].message.content or "").strip(),
        "input_tokens": usage.prompt_tokens if usage else 0,
        "output_tokens": usage.completion_tokens if usage else 0,
    }


def chat_stream(model: str, messages: list[dict], usage_out: dict) -> Iterator[str]:
    """Yield the answer piece by piece (lesson B3: the user sees text right away).
    Token usage arrives in the last event and is written into `usage_out`."""
    stream = get_client().chat.completions.create(
        **_params(model, messages), stream=True, stream_options={"include_usage": True})
    for event in stream:
        if event.usage:
            usage_out["input_tokens"] = event.usage.prompt_tokens
            usage_out["output_tokens"] = event.usage.completion_tokens
        if event.choices and event.choices[0].delta.content:
            yield event.choices[0].delta.content
