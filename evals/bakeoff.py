"""Task 13 lever B: run a fixed case subset through one pipeline version on one MAIN model, score and judge it.

    NESTLING_MAIN_MODEL=moonshotai/Kimi-K3 uv run python -m evals.bakeoff v7 moonshotai/Kimi-K3
Writes evals/results/phase3_v7_bakeoff_<model>.json (judge = Qwen on Nebius; never a pipeline model).
"""

import json
import sys
from concurrent.futures import ThreadPoolExecutor

from evals import evaluators, judge
from nestling import golden, graph, llm


def run(version: str, case_ids: list[str]) -> dict:
    by_id = {c["case_id"]: c for c in golden.load()}
    counts_as = graph._counts_as()

    def one(cid):
        inputs = golden.to_example(by_id[cid])
        out = graph.ask(inputs["inputs"]["question"], inputs["inputs"], version=version)
        s = evaluators.score_case(out, inputs["outputs"], counts_as)
        verdict = None
        if out["agent"] in judge.JUDGED_AGENTS and not out["escalate"] and not out["refused"] and out["answer"]:
            passages = list(out.get("passages") or [])
            if out["agent"] == "ready":
                from nestling.agents.ready import checklist_text
                passages.append({"source_id": "NESTLING-CHECKLIST", "page_label": None, "text": checklist_text()})
            verdict = judge.judge(inputs["inputs"]["question"], out["answer"], passages)
        return {"case_id": cid, "agent": out["agent"], "citation_match": s["citation_match"], "route_match": s["route_match"],
                "faithful": None if verdict is None else verdict.get("faithful"), "cost_inr": out["cost_inr"],
                "latency_ms": out["latency_ms"], "error": out["error"], "sources_cited": out["sources_cited"]}

    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(one, case_ids))
    judged = [r for r in rows if r["faithful"] is not None]
    cites = [r for r in rows if r["citation_match"] is not None]
    return {"model": llm.MAIN, "version": version, "n": len(rows), "errors": sum(bool(r["error"]) for r in rows),
            "faithfulness": round(sum(r["faithful"] for r in judged) / len(judged), 3) if judged else None, "n_judged": len(judged),
            "citation_match": round(sum(bool(r["citation_match"]) for r in cites) / len(cites), 3) if cites else None,
            "routing": round(sum(r["route_match"] for r in rows) / len(rows), 3),
            "cost_inr": round(sum(r["cost_inr"] or 0 for r in rows), 2), "mean_latency_ms": round(sum(r["latency_ms"] for r in rows) / len(rows)),
            "cases": rows}


if __name__ == "__main__":
    from dotenv import find_dotenv, load_dotenv

    load_dotenv(find_dotenv(usecwd=True))
    version = sys.argv[1]
    subset = json.loads(open(evaluators.RESULTS_DIR / "phase3_v7_diagnosis.json", encoding="utf-8").read())["bakeoff_subset"]["all"]
    result = run(version, subset)
    path = evaluators.RESULTS_DIR / f"phase3_v7_bakeoff_{llm.MAIN.split('/')[-1]}.json"
    path.write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "cases"}, indent=1))
