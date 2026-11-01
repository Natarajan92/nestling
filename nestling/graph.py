"""LangGraph wiring: Guardian -> Concierge -> specialist(s) -> Verifier.

The improvement levers of plan §9.5 are switched on cumulatively, so each one can be
measured on the frozen golden set with the same evaluators as the baseline:

    v1  Guardian (code rules + verified Haiku proposals) in front of the baseline answerer
    v2  + Concierge router and specialists
    v3  + retrieval upgrade: agent source filters, life-stage query, rerank
    v4  + Verifier
    v5  all levers after round-1 failure analysis (code-only unsafe kinds, Concierge v2,
        source-diversity cap, single-rewrite Verifier); v1-v4 were measured with round-1 code
    v6  v5 + stricter Verifier (verifier-v3: also checks practical advice and the parent's week;
        the rewrite only deletes), to win back the v5 faithfulness drop, on Nebius open models
        (DeepSeek-V4-Pro / V4.1-Flash, nestling/llm.py). v1-v5 results were recorded on Claude
        (Sonnet 5.5 / Haiku 5.5) and stay as published; the code now runs every version on the open models.

    uv run python -m nestling.graph v4 K01   # one case, traced into nestling-ask-improved
    uv run python -m nestling.graph v4 all   # full experiment
"""

import operator
import sys
import time
import uuid
from functools import cache
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from langsmith import get_current_run_tree, traceable
from langsmith.utils import ContextThreadPoolExecutor

from nestling import baseline, concierge, golden, guardian, llm, retrieval, verifier
from nestling.agents import care, celebrate, journal, money, nourish, ready
from nestling.lessons import LESSONS, library
from nestling.tracing import cost_inr, trace_metadata

PROJECT = "nestling-ask-improved"
PROMPT_VERSIONS = {"v1": "improved-v1", "v2": "improved-v1", "v3": "improved-v1", "v4": "improved-v1",
                   "v5": "improved-v2", "v6": "improved-v3", "v7": "improved-v4"}  # v2 = guardian code-only unsafe + concierge-v2 + verifier-v2
PROMPT_VERSION = PROMPT_VERSIONS["v6"]
VERSIONS = {
    "v1": {"concierge": False, "retrieval": "plain", "verifier": False},
    "v2": {"concierge": True, "retrieval": "plain", "verifier": False},
    "v3": {"concierge": True, "retrieval": "reranked", "verifier": False},
    "v4": {"concierge": True, "retrieval": "reranked", "verifier": True},
    "v5": {"concierge": True, "retrieval": "reranked", "verifier": True},
    "v6": {"concierge": True, "retrieval": "reranked", "verifier": True, "strict_verifier": True},
    "v7": {"concierge": True, "retrieval": "staged", "verifier": True, "strict_verifier": True},
}
for _flags in VERSIONS.values():
    _flags["lessons"] = False
# App-only variants; measured versions and their prompts remain unchanged.
VERSIONS["v6+lessons"] = {**VERSIONS["v6"], "lessons": True}
VERSIONS["v7+lessons"] = {**VERSIONS["v7"], "lessons": True}
VERSIONS["v7_vector"] = {**VERSIONS["v7"], "retrieval": "staged_vector"}
VERSIONS["app_v7_vector"] = {**VERSIONS["v7_vector"], "lessons": True}
PROMPT_VERSIONS.update({"v6+lessons": "app-v6-lessons-v1", "v7+lessons": "app-v7-lessons-v1",
                        "v7_vector": "improved-v4-vector", "app_v7_vector": "app-v7-vector-lessons-v1"})
APP_VERSION = "v6+lessons"  # promote only after the full v7 quality gate is reviewed
SPECIALISTS = {"care": care, "nourish": nourish, "money": money, "ready": ready, "celebrate": celebrate, "journal": journal}
VERIFIED = {"care", "nourish", "money"}  # medical, diet and insurance answers
REDIRECT_KINDS = {"dose", "medicine", "scan_interpretation", "diagnosis"}

OUT_OF_SCOPE_REPLY = ("That's outside what I can help with. I'm here for pregnancy, birth and your baby's first months: "
                      "health, food, getting ready, money matters and celebrations. Is there something there I can help with?")
CLARIFY_REPLY = ("I'd like to help. Could you tell me a little more: what you're noticing or wondering about, "
                 "and how many weeks along you are (or how old your baby is)?")


class AskState(TypedDict, total=False):
    question: str
    context: dict
    flags: dict
    can_save: bool
    screening: dict
    proposed_route: dict | None
    route: str
    result: dict
    verification: dict
    lesson_gap_topic: str
    steps: Annotated[list, operator.add]  # "How I answered", in order
    usage: Annotated[list, operator.add]  # one entry per LLM call


def guardian_node(state: AskState) -> dict:
    """Guardian screening. When the Concierge is on and the rules do not escalate, the Concierge
    runs at the same time (it only proposes a route; the Guardian's decision still comes first)."""
    question = state["question"]
    proposed = None
    if state["flags"]["concierge"] and not guardian.decide(question).escalate:
        with ContextThreadPoolExecutor(max_workers=2) as pool:
            screening = pool.submit(guardian.screen, question)
            routing = pool.submit(concierge.route, question, **({"lessons": True} if state["flags"].get("lessons") else {}))
            (decision, usage), proposed = screening.result(), routing.result()
    else:
        decision, usage = guardian.screen(question)
    steps = ["Guardian checked the message"]
    if decision.red_flags:
        steps.append("Red-flag rules fired: " + ", ".join(decision.red_flags))
    if decision.unsafe:
        steps.append("Unsafe request: " + ", ".join(decision.unsafe))
    usages = [u for u in (usage, (proposed or {}).get("usage")) if u]
    return {"screening": decision.as_dict(), "proposed_route": proposed, "steps": steps, "usage": usages}


def after_guardian(state: AskState) -> str:
    s = state["screening"]
    if s["escalate"] or s["refuse"]:
        return "guardian_reply"
    if not state["flags"]["concierge"]:
        return "baseline"
    if REDIRECT_KINDS & set(s["unsafe"]):
        return "redirect"
    return "concierge"


def guardian_reply_node(state: AskState) -> dict:
    s = state["screening"]
    route = "out_of_scope" if s["refuse"] and not s["escalate"] and s["unsafe"] == ["surveillance"] else "guardian"
    step = "Escalated to your doctor; specialists skipped" if s["escalate"] else "Declined the request; specialists skipped"
    result = {"answer": s["reply"], "sources_cited": [x["source_id"] for x in s["sources"]], "hits": [], "agent": "guardian"}
    return {"route": route, "result": result, "steps": [step]}


def baseline_node(state: AskState) -> dict:
    out = baseline.ask(state["question"], state["context"])
    s = state["screening"]
    route = "guardian" if REDIRECT_KINDS & set(s["unsafe"]) else out["route"]
    usage = {"model": out["model"], "tokens_in": out["tokens_in"] or 0, "tokens_out": out["tokens_out"] or 0}
    result = {"answer": out["answer"], "sources_cited": out["sources_cited"], "hits": [],
              "retrieved_source_ids": out["retrieved_source_ids"], "agent": "baseline", "error": out["error"]}
    return {"route": route, "result": result, "steps": ["Baseline answerer (single Sonnet call)"], "usage": [usage]}


def redirect_node(state: AskState) -> dict:
    kinds = [k for k in state["screening"]["unsafe"] if k in REDIRECT_KINDS]
    out = care.answer(state["question"], state["context"], state["flags"]["retrieval"], redirect=kinds)
    return {"route": "guardian", "result": out, "usage": out["usage"],
            "steps": ["Guardian: safe redirect (no medicine names, doses or diagnosis)", "Care answered from its sources"]}


def concierge_node(state: AskState) -> dict:
    out = state.get("proposed_route")
    usage = []
    if out is None:  # not pre-computed alongside the Guardian
        out = concierge.route(state["question"], **({"lessons": True} if state["flags"].get("lessons") else {}))
        usage = [out["usage"]] if out.get("usage") else []
    return {"route": out["route"], "usage": usage, "steps": [f"Concierge routed to {out['route']}"]}


def after_concierge(state: AskState) -> str:
    return "lessons" if state["flags"].get("lessons") and state["route"] == "lessons" else "specialist"


def lessons_node(state: AskState) -> dict:
    usage = []
    matched = library.match(state["question"], usage=usage)
    lesson_id = matched["lesson_id"]
    lesson = library.payload(lesson_id) if lesson_id else None
    if lesson:
        board = library.get(lesson_id)["storyboard"]
        answer = "\n\n".join(f"{s['step_no']}. {s['narration_line']} [{s['source_id']}, p. {s['page_label']}]" for s in board["scenes"])
        return {"route": "lessons", "result": {"answer": answer, "sources_cited": [s["id"] for s in lesson["sources"]],
                "retrieved_source_ids": [s["id"] for s in lesson["sources"]], "hits": [], "agent": "lessons", "lesson": lesson},
                "usage": usage, "steps": ["Approved Little Lesson: reviewed steps and video"]}
    out = specialist_node({**state, "route": "care"})
    topic = matched.get("topic")
    return {**out, "route": "care", "usage": usage + out.get("usage", []),
            "lesson_gap_topic": topic if topic in LESSONS else "newborn_care",
            "steps": ["No approved lesson available; Care answered from its sources", *out.get("steps", [])]}


def specialist_node(state: AskState) -> dict:
    route = state["route"]
    if route == "out_of_scope":
        return {"result": {"answer": OUT_OF_SCOPE_REPLY, "sources_cited": [], "hits": [], "agent": "concierge"}}
    if route == "clarify":
        return {"result": {"answer": CLARIFY_REPLY, "sources_cited": [], "hits": [], "agent": "concierge"}}
    agent = SPECIALISTS[route]
    if route == "journal":
        out = agent.answer(state["question"], state["context"], can_save=state.get("can_save", False))
    else:
        out = agent.answer(state["question"], state["context"], state["flags"]["retrieval"])
    sources = ", ".join(sorted(set(out["sources_cited"]))) or "none"
    return {"result": out, "usage": out.get("usage", []), "steps": [f"{route.title()} answered (sources: {sources})"]}


def after_specialist(state: AskState) -> str:
    agent = state["result"].get("agent")
    if state["flags"]["verifier"] and agent in VERIFIED and state["result"].get("hits"):
        return "verifier"
    return END


def verifier_node(state: AskState) -> dict:
    r = state["result"]
    v = verifier.verify(r["answer"], r["sources_cited"], r["hits"], strict=state["flags"].get("strict_verifier", False))
    step = {"passed": "Verifier: every claim matches its source",
            "rewritten": f"Verifier: removed {len(v['unsupported'])} unsupported claim(s)",
            "replaced": "Verifier: claims not supported; answered that there is no trusted source"}[v["verdict"]]
    return {"result": {**r, "answer": v["answer"], "sources_cited": v["sources_cited"]},
            "verification": {k: v[k] for k in ("verdict", "unsupported")}, "usage": v["usage"], "steps": [step]}


@cache
def compiled():
    g = StateGraph(AskState)
    g.add_node("guardian", guardian_node)
    g.add_node("guardian_reply", guardian_reply_node)
    g.add_node("baseline", baseline_node)
    g.add_node("redirect", redirect_node)
    g.add_node("concierge", concierge_node)
    g.add_node("specialist", specialist_node)
    g.add_node("lessons", lessons_node)
    g.add_node("verifier", verifier_node)
    g.add_edge(START, "guardian")
    g.add_conditional_edges("guardian", after_guardian, ["guardian_reply", "baseline", "redirect", "concierge"])
    g.add_edge("guardian_reply", END)
    g.add_edge("baseline", END)
    g.add_conditional_edges("redirect", after_specialist, ["verifier", END])
    g.add_conditional_edges("concierge", after_concierge, ["lessons", "specialist"])
    g.add_conditional_edges("lessons", after_specialist, ["verifier", END])
    g.add_conditional_edges("specialist", after_specialist, ["verifier", END])
    g.add_edge("verifier", END)
    return g.compile()


def _total_cost(usage: list[dict]) -> float | None:
    costs = [cost_inr(u["model"], u.get("tokens_in", 0), u.get("tokens_out", 0), u.get("cache_write", 0), u.get("cache_read", 0))
             for u in usage if u]
    return round(sum(c for c in costs if c is not None), 4) if costs else 0.0


@traceable(name="nestling_pipeline", run_type="chain")
def ask(question: str, context: dict | None = None, version: str = "v6", can_save: bool = False) -> dict:
    """Answer one message. Never raises: failures come back in `error`, and the Guardian's
    decision (code) is kept even if a later step fails."""
    context = context or {}
    started = time.perf_counter()
    out = {"answer": "", "escalate": False, "route": None, "refused": False, "sources_cited": [], "retrieved_source_ids": [],
           "rules_fired": [], "unsafe": [], "classifier_flags": [], "agent": None, "verification": None, "steps": [],
           "model": None, "latency_ms": None, "tokens_in": None, "tokens_out": None, "cost_inr": None, "error": None,
           "lesson": None, "lesson_gap_topic": None, "retrieval_fallback": None,
           "retrieval_mode": VERSIONS.get(version, {}).get("retrieval")}
    try:
        with retrieval.app_rerank_fallback(enabled=version in {"v6+lessons", "v7+lessons", "app_v7_vector"}):
            state = compiled().invoke({"question": question, "context": context, "flags": VERSIONS[version], "can_save": can_save})
        s, r = state["screening"], state["result"]
        usage = [u for u in state.get("usage", []) if u]
        retrieved = set(r.get("retrieved_source_ids") or [h["source_id"] for h in r.get("hits", [])])
        retrieved |= {x["source_id"] for x in s["sources"]}  # rule sources are checked pages, not model picks
        out.update(
            answer=r["answer"], escalate=s["escalate"], refused=s["refuse"], route=state["route"],
            sources_cited=list(dict.fromkeys(r["sources_cited"])), retrieved_source_ids=sorted(retrieved),
            rules_fired=s["red_flags"], unsafe=s["unsafe"], classifier_flags=s["classifier_flags"], agent=r.get("agent"),
            verification=state.get("verification"), steps=state.get("steps", []), error=r.get("error"),
            lesson=r.get("lesson"), lesson_gap_topic=state.get("lesson_gap_topic"),
            passages=[{"source_id": h["source_id"], "page_label": h.get("page_label"), "text": h["chunk_text"]} for h in r.get("hits", [])],
            model=next((u["model"] for u in reversed(usage) if u["model"] in (llm.MAIN, "claude-sonnet-5-5")), usage[-1]["model"] if usage else "rules"),
            tokens_in=sum(u.get("tokens_in", 0) + u.get("cache_write", 0) + u.get("cache_read", 0) for u in usage),
            tokens_out=sum(u.get("tokens_out", 0) for u in usage), cost_inr=_total_cost(usage),
        )
        if any(h.get("retrieval_fallback") == "vector_order" for h in r.get("hits", [])):
            out["retrieval_fallback"] = "vector_order"
            out["steps"] = [*out["steps"], "Rerank unavailable; source passages kept in vector order"]
    except Exception as exc:
        out["error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
        try:  # safety still decided in code even when the rest failed
            d = guardian.decide(question)
            out.update(escalate=d.escalate, refused=d.refuse, rules_fired=d.red_flags, unsafe=d.unsafe,
                       answer=d.reply or "", route="guardian" if d.escalate or d.refuse else None)
        except Exception:
            pass
    out["latency_ms"] = round((time.perf_counter() - started) * 1000)
    return out


@cache
def _golden_by_id() -> dict[str, dict]:
    return {c["case_id"]: c for c in golden.load()}


@cache
def _counts_as() -> dict[str, set[str]]:
    return retrieval.counts_as(retrieval.load_registry())


def make_target(version: str):
    @traceable(name="nestling_ask", run_type="chain")
    def target(inputs: dict, metadata: dict) -> dict:
        """LangSmith target: one golden example through pipeline `version`, with the full §9.4 metadata."""
        from evals.evaluators import score_case

        case = _golden_by_id()[metadata["case_id"]]
        expected = golden.to_example(case)["outputs"]
        out = ask(inputs["question"], inputs, version=version)
        scores = score_case(out, expected, _counts_as())
        out.update(invalid_citations=scores["invalid_citations"], unretrieved_citations=scores["unretrieved_citations"])
        run = get_current_run_tree()
        if run is not None:
            run.add_metadata(trace_metadata(
                case_id=case["case_id"], dataset_version=golden.DATASET_VERSION, scenario_type=case["scenario_type"],
                pipeline_version=version, prompt_version=PROMPT_VERSIONS[version], model=out["model"],
                expected_escalate=expected["expected_escalate"], predicted_escalate=out["escalate"],
                expected_route="|".join(expected["expected_route"]), predicted_route=out["route"],
                refused=out["refused"], sources_cited=out["sources_cited"], correct=scores["correct"],
                latency_ms=out["latency_ms"], tokens_in=out["tokens_in"], tokens_out=out["tokens_out"],
                cost_inr=out["cost_inr"], error=out["error"],
                lesson_gap_topic=out.get("lesson_gap_topic"), retrieval_mode=out.get("retrieval_mode"),
                retrieval_fallback=out.get("retrieval_fallback"),
            ))
        return out

    return target


RECORDED_NOTE = ("v1-v5 published results were measured on claude-sonnet-5-5 + claude-haiku-5-5; the code now runs every "
                 "version on the Nebius open models (v1 still uses the Claude baseline answerer), so a re-run is not comparable")


def run_info(version: str) -> dict:
    return {"dataset": golden.LANGSMITH_DATASET, "dataset_version": golden.DATASET_VERSION, "pipeline_version": version,
            "prompt_version": PROMPT_VERSIONS[version], "model": f"{llm.MAIN} + {llm.FAST}", "levers": VERSIONS[version],
            "retrieval_mode": VERSIONS[version]["retrieval"],
            **({"note": RECORDED_NOTE} if version in {"v1", "v2", "v3", "v4", "v5"} else {})}


def run_experiment(version: str, max_concurrency: int = 4):
    """Run every frozen case through `version` as one experiment (prefix nestling-ask-improved-<version>)."""
    from langsmith import evaluate

    from evals.evaluators import EVALUATORS

    _golden_by_id()  # fail fast if the golden file changed
    return evaluate(
        make_target(version), data=golden.LANGSMITH_DATASET, evaluators=EVALUATORS,
        experiment_prefix=f"{PROJECT}-{version}", metadata=run_info(version), max_concurrency=max_concurrency,
        description=f"Phase 3 {version}: " + ", ".join(k for k, v in VERSIONS[version].items() if v and v != "plain"),
    )


def run_one(case_id: str, version: str = "v6") -> tuple[dict, uuid.UUID]:
    case = _golden_by_id()[case_id]
    run_id = uuid.uuid4()
    out = make_target(version)(golden.to_example(case)["inputs"], {"case_id": case_id},
                               langsmith_extra={"run_id": run_id, "project_name": PROJECT})
    return out, run_id


if __name__ == "__main__":
    import json

    from dotenv import find_dotenv, load_dotenv

    load_dotenv(find_dotenv(usecwd=True))
    version, arg = (sys.argv[1:] + ["v4", "help"])[:2] if len(sys.argv) > 2 else ("v4", (sys.argv[1:] or ["help"])[0])
    if arg == "all":
        from evals.evaluators import export

        results = run_experiment(version)
        print("experiment:", results.experiment_name)
        for path in export(results, run_info(version), prefix=f"improved_{version}"):
            print("wrote", path)
    elif arg in _golden_by_id():
        from langsmith import Client

        from nestling.tracing import METADATA_KEYS, fetch_run

        out, run_id = run_one(arg, version)
        print(json.dumps({k: v for k, v in out.items()}, indent=2, ensure_ascii=False))
        ls = Client()
        run = fetch_run(ls, run_id)
        print("trace:", ls.get_run_url(run=run, project_name=PROJECT))
        print("missing §9.4 keys:", [k for k in METADATA_KEYS if k not in run.extra.get("metadata", {})] or "none")
    else:
        print(__doc__)
