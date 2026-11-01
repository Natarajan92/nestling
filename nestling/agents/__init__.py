"""Specialist agents: care, nourish, ready, money, celebrate, journal.

Each specialist answers from passages of its own sources (registry `used_by`) with one
Sonnet call, through `answer_from_sources`. Deterministic content (checklists, playbooks)
is passed in by the agent as extra context; the LLM explains it and never invents it.
Every call reports its token usage so the pipeline can total the cost.
"""

import json
from functools import cache

from langsmith import traceable

from nestling import retrieval

SONNET = "claude-sonnet-5-5"
NO_SOURCE_LINE = "I don't have a trusted source for that. Please ask your doctor."

ANSWER_SCHEMA = {
    "type": "object",
    "properties": {"answer": {"type": "string"}, "sources_cited": {"type": "array", "items": {"type": "string"}}},
    "required": ["answer", "sources_cited"],
    "additionalProperties": False,
}

BASE_PROMPT = """You are Nestling's {agent} specialist: a calm, warm companion for first-time parents in India (mothers, fathers, partners, every family shape), in pregnancy and after birth.

Rules:
- Base every medical, diet, insurance and legal statement only on the passages given, and mention the source ID in the text, e.g. "(WHO-ANC, p. 34)". If the passages do not cover the question, say: "{no_source}"
- sources_cited lists the source IDs you actually used, taken only from the passage labels.
- Never give medicine doses and never diagnose.
- You cannot see uploaded documents, scans, policies or records, and you cannot save anything; if the question needs one, say so and ask for it.
- Be kind and brief: at most about 180 words. Speak to the person who wrote (a father asking about his wife gets advice for both of them).
{instructions}"""


@cache
def client():
    import anthropic
    from langsmith.wrappers import wrap_anthropic

    return wrap_anthropic(anthropic.Anthropic())


def usage_of(response) -> dict:
    u = response.usage
    return {"model": response.model, "tokens_in": u.input_tokens, "tokens_out": u.output_tokens,
            "cache_write": u.cache_creation_input_tokens or 0, "cache_read": u.cache_read_input_tokens or 0}


def final_text(response) -> str:
    """Text written by the model that finally answered (after any refusal-fallback switch)."""
    blocks = list(response.content)
    last_switch = max((i for i, b in enumerate(blocks) if b.type == "fallback"), default=-1)
    return "".join(b.text for b in blocks[last_switch + 1:] if b.type == "text")


def sonnet_json(system: str, user: str, schema: dict, max_tokens: int = 3000) -> tuple[dict | None, dict, str]:
    """One structured Sonnet call with server-side refusal fallback. Returns (data, usage, stop_reason)."""
    response = client().beta.messages.create(
        model=SONNET,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": schema}},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    data = json.loads(final_text(response)) if response.stop_reason not in ("refusal", "max_tokens") else None
    return data, usage_of(response), response.stop_reason


def profile_line(context: dict) -> str:
    keys = ("week", "diet", "tradition", "parent_role", "life_stage")
    return "Parent context: " + ", ".join(f"{k}={context[k]}" for k in keys if context.get(k) not in (None, ""))


def retrieval_query(question: str, context: dict) -> str:
    """The question with the parent's life stage in front, so postnatal questions find postnatal sources."""
    stage = context.get("life_stage")
    if stage == "postpartum":
        return f"After birth (postnatal mother and newborn): {question}"
    if stage == "pregnancy" and context.get("week"):
        return f"Pregnancy, week {context['week']}: {question}"
    return question


def retrieve(question: str, context: dict, agent: str, mode: str) -> list[dict]:
    """mode 'plain' = baseline dense search; 'reranked' = agent sources + life stage + rerank (lever 3)."""
    if mode == "plain":
        return retrieval.search(question, top_k=6)
    return retrieval.search_reranked(retrieval_query(question, context), source_ids=retrieval.sources_for(agent))


def passages_text(hits: list[dict]) -> str:
    return "\n".join(f"\n[{n}] {retrieval.format_citation(h)}\n{h['chunk_text']}" for n, h in enumerate(hits, 1))


@traceable(name="specialist_answer", run_type="chain")
def answer_from_sources(agent: str, question: str, context: dict, hits: list[dict], instructions: str = "",
                        extra: str = "") -> dict:
    """{"answer", "sources_cited", "usage": [..], "stop_reason"} from one Sonnet call over the passages."""
    system = BASE_PROMPT.format(agent=agent, no_source=NO_SOURCE_LINE, instructions=instructions)
    user = f"{profile_line(context)}\n\nParent's message: {question}\n"
    if extra:
        user += f"\nNestling's own checklist/playbook (code-owned; explain it, do not add to it):\n{extra}\n"
    user += f"\nPassages:{passages_text(hits) or ' (none found)'}"
    data, usage, stop = sonnet_json(system, user, ANSWER_SCHEMA)
    if data is None:
        data = {"answer": NO_SOURCE_LINE, "sources_cited": []}
    return {**data, "usage": [usage], "stop_reason": stop}
