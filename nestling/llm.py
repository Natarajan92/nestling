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

MAIN = "deepseek-ai/DeepSeek-V4-Pro"
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


def chat_json(model: str, system: str, user: str, schema: dict, max_tokens: int = 3000) -> tuple[dict | None, dict, str]:
    """(parsed or None, usage, raw text). Schema path first; JSON mode with the schema in the prompt if rejected."""
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    try:
        response = client().chat.completions.create(
            model=model, messages=messages, max_tokens=max_tokens, temperature=0,
            response_format={"type": "json_schema", "json_schema": {"name": "reply", "schema": schema, "strict": True}})
    except Exception as exc:  # BadRequest etc.: this model does not take json_schema
        if getattr(exc, "status_code", 400) not in (400, 422):
            raise
        messages[0]["content"] += "\n\nReply with one JSON object only, matching this JSON schema:\n" + json.dumps(schema)
        response = client().chat.completions.create(
            model=model, messages=messages, max_tokens=max_tokens, temperature=0, response_format={"type": "json_object"})
    text = response.choices[0].message.content or ""
    return _parse(text, schema), usage_of(response), text
