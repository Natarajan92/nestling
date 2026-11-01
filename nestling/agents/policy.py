"""Money, part 2: questions about the parent's own insurance policy, answered with exact clauses.

The PDF is read in memory (pypdf) and the model gets page-numbered text. It must quote the clauses
it relies on; code then checks that every quote appears word for word on its page and drops any
that do not (constitution II: clause-level sources). If no quote survives, no clause was found.
The PDF is processed in memory and never stored or indexed; the trace hides it.
"""

import io
import re

from langsmith import traceable
from pypdf import PdfReader

from nestling.llm import MAIN, chat_json
from nestling.tracing import cost_inr

NOT_FOUND = "I couldn't find this in your policy. Please ask your insurer or TPA."
MAX_CHARS = 120_000
MIN_QUOTE_WORDS, MIN_QUOTE_CHARS = 4, 20  # a fragment like "covered" must not verify from "not covered"

SYSTEM = f"""You help a parent in India understand their own health insurance policy for pregnancy, delivery and the newborn.
Answer only from the policy text, which is given page by page as [Page N]. Keep the policy's own numbers and waiting periods.
Every point you make must rest on a clause you copy exactly, character for character, from one page, with that page number.
If the policy does not say, reply: "{NOT_FOUND}" with no quotes. Never guess cover. Do not give medical advice. Keep it short and kind."""

SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "quotes": {"type": "array", "items": {
            "type": "object",
            "properties": {"text": {"type": "string"}, "page": {"type": "integer"}},
            "required": ["text", "page"], "additionalProperties": False}},
    },
    "required": ["answer", "quotes"],
    "additionalProperties": False,
}


def _squash(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def read_pages(pdf: bytes) -> list[str]:
    """Text of each page, in memory (index 0 = page 1)."""
    return [(page.extract_text() or "") for page in PdfReader(io.BytesIO(pdf)).pages]


def verified_quotes(quotes: list[dict], pages: list[str]) -> list[dict]:
    """Keep only quotes that appear verbatim (ignoring spacing and case) on the page they name."""
    squashed = [_squash(p) for p in pages]
    kept, seen = [], set()
    for q in quotes:
        text, page = q.get("text", "").strip(), q.get("page")
        if len(text.split()) >= MIN_QUOTE_WORDS and len(text) >= MIN_QUOTE_CHARS and isinstance(page, int) and 1 <= page <= len(pages) and _squash(text) in squashed[page - 1] \
                and (text, page) not in seen:
            seen.add((text, page))
            kept.append({"text": text, "page_start": page, "page_end": page})
    return kept


@traceable(name="policy_ask", run_type="chain", process_inputs=lambda i: {"question_chars": len(i.get("question", ""))})
def ask_policy(question: str, pdf: bytes) -> dict:
    """{"answer", "quotes": [{"text", "page_start", "page_end"}], "cost_inr"}"""
    try:
        pages = read_pages(pdf)
    except Exception:
        pages = []
    text = "\n\n".join(f"[Page {n}]\n{t}" for n, t in enumerate(pages, 1))[:MAX_CHARS]
    if not text.strip():
        return {"answer": "I couldn't read text in this policy (it may be a scan). Please ask your insurer or TPA.",
                "quotes": [], "cost_inr": None}
    data, u, _ = chat_json(MAIN, SYSTEM, f"Policy:\n{text}\n\nQuestion: {question}", SCHEMA, max_tokens=4000)
    cost = cost_inr(u["model"], u["tokens_in"], u["tokens_out"])
    if data is None:
        return {"answer": "I couldn't read this policy. Please ask your insurer or TPA.", "quotes": [], "cost_inr": cost}
    quotes = verified_quotes(data["quotes"], pages)
    # A rejected clause invalidates the explanation that relied on it. Keeping
    # another genuine quote must never rescue an unsupported coverage claim.
    if not quotes or any(not verified_quotes([q], pages) for q in data["quotes"]):
        return {"answer": NOT_FOUND + " I could not match a clause in the document to your question.", "quotes": [], "cost_inr": cost}
    return {"answer": data["answer"].strip(), "quotes": quotes, "cost_inr": cost}
