"""Money, part 2: questions about the parent's own insurance policy, answered with exact clauses.

The uploaded PDF goes to Claude as a document with citations enabled, so every statement
comes back with the exact quoted text and its page number (constitution II: clause-level
sources). The PDF is processed in memory and never stored or indexed; the trace hides it.
"""

import base64

from langsmith import traceable

from nestling.agents import SONNET, client, usage_of
from nestling.tracing import cost_inr

SYSTEM = """You help a parent in India understand their own health insurance policy for pregnancy, delivery and the newborn.
Answer only from the policy document. Quote the exact clause for every point and keep the policy's own numbers and waiting periods.
If the policy does not say, reply: "I couldn't find this in your policy. Please ask your insurer or TPA." Never guess cover.
Do not give medical advice. Keep it short and kind."""


@traceable(name="policy_ask", run_type="chain")
def ask_policy(question: str, pdf: bytes) -> dict:
    """{"answer", "quotes": [{"text", "page_start", "page_end"}], "cost_inr"}"""
    response = client().beta.messages.create(
        model=SONNET,
        max_tokens=4000,
        system=SYSTEM,
        messages=[{"role": "user", "content": [
            {"type": "document", "title": "Your policy", "citations": {"enabled": True},
             "source": {"type": "base64", "media_type": "application/pdf", "data": base64.standard_b64encode(pdf).decode()}},
            {"type": "text", "text": question},
        ]}],
        output_config={"effort": "low"},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    if response.stop_reason == "refusal":
        return {"answer": "I couldn't read this policy. Please ask your insurer or TPA.", "quotes": [], "cost_inr": None}
    parts, quotes = [], []
    for block in response.content:
        if block.type != "text":
            continue
        parts.append(block.text)
        for c in getattr(block, "citations", None) or []:
            if getattr(c, "type", None) == "page_location":
                quotes.append({"text": c.cited_text.strip(), "page_start": c.start_page_number, "page_end": c.end_page_number - 1})
    u = usage_of(response)
    unique = list({(q["text"], q["page_start"]): q for q in quotes}.values())
    return {"answer": "".join(parts).strip(), "quotes": unique,
            "cost_inr": cost_inr(u["model"], u["tokens_in"], u["tokens_out"], u["cache_write"], u["cache_read"])}
