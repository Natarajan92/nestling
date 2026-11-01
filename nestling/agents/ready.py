"""Ready: labour bag, hospital and documents checklists from YAML, explained by Sonnet.

The checklist (playbooks/labour_bag.yaml) is code-owned; Sonnet only explains and
personalises it. Partner questions ("what can I do this week?") use the same agent with
passages from the antenatal sources.
"""

from functools import cache
from pathlib import Path

import yaml

from nestling import retrieval
from nestling.agents import answer_from_sources, retrieval_query

PLAYBOOK = Path(__file__).resolve().parents[2] / "playbooks" / "labour_bag.yaml"

INSTRUCTIONS = """- For packing and documents, use Nestling's checklist; each item shows its source ID or says it is common practice. Cite the item's source ID when you use it.
- For partners and fathers, give practical, kind things they can do, based on the passages.
- Do not add medical claims that are not in the passages."""


@cache
def checklist() -> dict:
    return yaml.safe_load(PLAYBOOK.read_text(encoding="utf-8"))


def checklist_text() -> str:
    data = checklist()
    lines = [data["title"], data["when"]]
    for section in data["sections"]:
        lines.append(f"{section['name']}:")
        for i in section["items"]:
            page = f", p. {i['page']}" if i.get("page") else ""
            lines.append(f"- {i['item']} [{i['source']}{page}]")
    lines.append("After birth:")
    lines += [f"- {i['item']} [{i['source']}]" for i in data["after_birth"]]
    return "\n".join(lines)


def answer(question: str, context: dict, mode: str = "reranked") -> dict:
    if mode == "plain":
        hits = retrieval.search(question, top_k=6)
    else:
        sources = retrieval.sources_for("ready") + retrieval.sources_for("care")
        hits = retrieval.search_reranked(retrieval_query(question, context), source_ids=sources)
    out = answer_from_sources("Ready", question, context, hits, INSTRUCTIONS, extra=checklist_text())
    return {**out, "hits": hits, "agent": "ready"}
