"""LangSmith metadata helpers: every trace carries the plan §9.4 metadata.

Metadata holds IDs, labels, versions and numbers only. Never put personal data
(names, due dates, symptoms tied to a person, policy details) in it.
"""

import time
import uuid

from langsmith import get_current_run_tree, traceable
from langsmith.utils import LangSmithNotFoundError

# Plan §9.4, in order. Every trace gets all of these keys; unknown ones are None.
METADATA_KEYS = (
    "case_id",
    "dataset_version",
    "scenario_type",
    "pipeline_version",
    "prompt_version",
    "model",
    "expected_escalate",
    "predicted_escalate",
    "expected_route",
    "predicted_route",
    "refused",
    "sources_cited",
    "correct",
    "latency_ms",
    "tokens_in",
    "tokens_out",
    "cost_inr",
    "error",
)

# USD per million tokens (input, output). Runtime models are Nebius open models; prices from the Nebius
# Token Factory model list (GET https://api.tokenfactory.nebius.com/v1/models?verbose=true, "pricing"),
# read 2026-11-01. Claude prices are kept for the Phase 2 baseline and v1-v5 records (Anthropic first-party).
PRICE_USD_PER_MTOK = {
    "deepseek-ai/DeepSeek-V4-Pro": (1.75, 3.50),
    "deepseek-ai/DeepSeek-V4.1-Flash": (0.30, 1.20),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-opus-5-5": (4.00, 20.00),
    "claude-opus-5": (5.00, 25.00),
    "claude-opus-4-8": (5.00, 25.00),
    "claude-sonnet-5": (2.00, 10.00),
}
USD_TO_INR = 94.91  # Rate as of 2026-11-01; update before reporting Week 4 costs.


def trace_metadata(**fields) -> dict:
    """Return the full §9.4 metadata dict. Missing keys are None; unknown keys raise."""
    unknown = set(fields) - set(METADATA_KEYS)
    if unknown:
        raise KeyError(f"Not in the §9.4 metadata schema: {sorted(unknown)}")
    return {key: fields.get(key) for key in METADATA_KEYS}


def cost_inr(model: str, tokens_in: int, tokens_out: int, cache_write: int = 0, cache_read: int = 0) -> float | None:
    """Cost of one call in INR, or None if the model has no price on file.

    Cache writes cost 1.25x and cache reads 0.1x the input price.
    """
    if model not in PRICE_USD_PER_MTOK:
        return None
    price_in, price_out = PRICE_USD_PER_MTOK[model]
    usd = ((tokens_in + 1.25 * cache_write + 0.1 * cache_read) * price_in + tokens_out * price_out) / 1_000_000
    return round(usd * USD_TO_INR, 4)


def traced_claude_call(client, *, run_name: str, project_name: str, metadata: dict, **create_kwargs):
    """Make one Claude call inside a LangSmith parent run carrying the §9.4 metadata.

    `client` must be wrapped with `langsmith.wrappers.wrap_anthropic`, so the LLM
    call appears as a child run with token usage. The measured fields (model,
    latency_ms, tokens_in, tokens_out, cost_inr, error) are filled in after the
    call; `model` is the model that actually served the response.

    Returns (response, run_id).
    """
    run_id = uuid.uuid4()

    @traceable(name=run_name, run_type="chain")
    def _run(**kwargs):
        run = get_current_run_tree()
        started = time.perf_counter()
        try:
            response = client.beta.messages.create(**kwargs)
        except Exception as exc:
            run.add_metadata({
                "latency_ms": round((time.perf_counter() - started) * 1000),
                "error": type(exc).__name__,
            })
            raise
        usage = response.usage
        run.add_metadata({
            "model": response.model,
            "latency_ms": round((time.perf_counter() - started) * 1000),
            "tokens_in": usage.input_tokens,
            "tokens_out": usage.output_tokens,
            "cost_inr": cost_inr(response.model, usage.input_tokens, usage.output_tokens),
        })
        return response

    response = _run(
        **create_kwargs,
        langsmith_extra={
            "run_id": run_id,
            "project_name": project_name,
            "metadata": trace_metadata(**metadata),
        },
    )
    return response, run_id


def fetch_run(ls_client, run_id, timeout_s: float = 60.0):
    """Flush pending traces and read the run back from LangSmith once it is ingested."""
    ls_client.flush()
    deadline = time.monotonic() + timeout_s
    while True:
        try:
            run = ls_client.read_run(run_id)
        except LangSmithNotFoundError:  # not ingested yet
            run = None
        if run is not None and run.end_time is not None:
            return run
        if time.monotonic() > deadline:
            if run is None:
                raise TimeoutError(f"Run {run_id} not found in LangSmith after {timeout_s}s")
            return run
        time.sleep(2)
