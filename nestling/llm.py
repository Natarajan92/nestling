"""One shared client for every runtime LLM call: Nebius open models through the OpenAI-compatible API.

MAIN answers (specialists, verifier, policy Q&A); FAST classifies and extracts (Guardian classifier,
Concierge, Capture). `chat_json` asks for a JSON schema and falls back to JSON mode plus validation
when a model does not support `json_schema`. (Anthropic stays only in baseline.py, the Phase 2 record.)
"""

import json
import os
from functools import cache

from jsonschema import ValidationError, validate
from langsmith.wrappers import wrap_openai

MAIN = os.environ.get("NESTLING_MAIN_MODEL") or "deepseek-ai/DeepSeek-V4-Pro"  # env override: Task 13 bake-off only
FAST = "deepseek-ai/DeepSeek-V4.1-Flash"
BASE_URL = "https://api.tokenfactory.nebius.com/v1/"


@cache
def client():
    from openai import OpenAI

    return wrap_openai(OpenAI(base_url=BASE_URL, api_key=os.environ["NEBIUS_API_KEY"], timeout=120, max_retries=3))


def usage_of(response) -> dict:
    u = response.usage
    return {"model": response.model or "", "tokens_in": u.prompt_tokens or 0, "tokens_out": u.completion_tokens or 0}


def _parse(text: str, schema: dict) -> dict | None:
    try:
        data = json.loads(text)
        validate(data, schema)
        return data
    except (ValueError, ValidationError):
        return None


def chat_json(model: str, system: str, user: str, schema: dict, max_tokens: int = 3000,
              *, reasoning_effort: str | None = None) -> tuple[dict | None, dict, str]:
    """(parsed or None, usage, raw text). Schema path first, JSON mode if rejected.

    Reasoning effort is caller-scoped; omission preserves the provider's default.
    """
    if reasoning_effort not in (None, "none", "low"):
        raise ValueError("reasoning_effort must be None, 'none' or 'low'")
    reasoning = {"reasoning_effort": reasoning_effort} if reasoning_effort is not None else {}
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    try:
        response = client().chat.completions.create(
            model=model, messages=messages, max_tokens=max_tokens, temperature=0,
            response_format={"type": "json_schema", "json_schema": {"name": "reply", "schema": schema, "strict": True}},
            **reasoning)
    except Exception as exc:  # BadRequest etc.: this model does not take json_schema
        message = str(exc).lower()
        # A reasoning-parameter rejection cannot be repaired by switching JSON formats.
        schema_rejection = "reasoning_effort" not in message and any(
            marker in message for marker in ("json_schema", "json schema", "response_format"))
        if getattr(exc, "status_code", None) not in (400, 422) or not schema_rejection:
            raise
        messages[0]["content"] += "\n\nReply with one JSON object only, matching this JSON schema:\n" + json.dumps(schema)
        response = client().chat.completions.create(
            model=model, messages=messages, max_tokens=max_tokens, temperature=0, response_format={"type": "json_object"},
            **reasoning)
    text = response.choices[0].message.content or ""
    return _parse(text, schema), usage_of(response), text
