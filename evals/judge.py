"""Faithfulness judge: an open model on Nebius (a different family from Claude) checks answers.

The prompt lives in evals/judge_prompt.md. Nebius serves an OpenAI-compatible API, called with
plain HTTP (no extra SDK). Scores are attached to the experiment's runs as `faithfulness`
feedback, so the LangSmith comparison view shows them next to the code evaluators.

    uv run python -m evals.judge nestling-ask-baseline-c7951af1
"""

import csv
import json
import os
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

from evals.evaluators import RESULTS_DIR, StoredExperiment

JUDGE_MODEL = "Qwen/Qwen3-235B-A22B-Instruct-2507"
JUDGE_VERSION = "judge-v1"
ENDPOINT = "https://api.tokenfactory.nebius.com/v1/chat/completions"
PROMPT_FILE = Path(__file__).resolve().parent / "judge_prompt.md"
JUDGED_AGENTS = {"care", "nourish", "money", "ready", "baseline"}


def _prompt() -> tuple[str, str]:
    text = PROMPT_FILE.read_text(encoding="utf-8")
    system = text.split("## System", 1)[1].split("## User template", 1)[0].strip()
    template = re.search(r"```\n(.*?)```", text.split("## User template", 1)[1], re.S).group(1)
    return system, template


def judge(question: str, answer: str, passages: list[dict], retries: int = 3) -> dict:
    """{"claims": [...], "faithful": bool, "score": share of claims supported (1.0 if none)}."""
    system, template = _prompt()
    passage_text = "\n\n".join(f"[{p['source_id']}, p. {p.get('page_label')}] {p['text']}" for p in passages) or "(none)"
    body = {
        "model": JUDGE_MODEL, "temperature": 0, "max_tokens": 2000, "response_format": {"type": "json_object"},
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": template.replace("{question}", question).replace("{passages}", passage_text).replace("{answer}", answer)}],
    }
    request = urllib.request.Request(ENDPOINT, data=json.dumps(body).encode(), method="POST", headers={
        "Authorization": f"Bearer {os.environ['NEBIUS_API_KEY']}", "Content-Type": "application/json"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                data = json.load(response)
            result = json.loads(data["choices"][0]["message"]["content"])
            claims = result.get("claims", [])
            supported = sum(c.get("verdict") == "supported" for c in claims)
            result["score"] = round(supported / len(claims), 3) if claims else 1.0
            result["faithful"] = bool(result.get("faithful")) and supported == len(claims)
            return result
        except Exception as exc:  # rate limit, timeout or malformed JSON: back off and retry
            error = f"{type(exc).__name__}: {exc}"
            time.sleep(2 ** attempt)
    return {"claims": [], "faithful": None, "score": None, "error": error}


def _baseline_passages(question: str) -> list[dict]:
    """The baseline's passages: plain dense search is deterministic, so this re-creates them."""
    from nestling import retrieval

    return [{"source_id": h["source_id"], "page_label": h["page_label"], "text": h["chunk_text"]}
            for h in retrieval.search(question, top_k=6)]


def judge_experiment(experiment_name: str, max_workers: int = 6, upload: bool = True) -> list[dict]:
    """Judge every passage-based answer in a finished experiment; returns one row per judged case."""
    stored = StoredExperiment(experiment_name)
    items = [(i["run"], i["example"]) for i in stored if i["run"] and i["run"].outputs]

    def work(pair):
        run, example = pair
        out = run.outputs
        agent = out.get("agent", "baseline")
        if agent not in JUDGED_AGENTS or out.get("escalate") or out.get("refused") or not out.get("answer"):
            return None
        passages = list(out.get("passages") or [])
        if not passages and agent == "baseline":  # baseline answers (also v1) keep no passages; re-create them
            passages = _baseline_passages(example.inputs["question"])
        if agent == "ready":  # Ready answers from Nestling's code-owned, sourced checklist too
            from nestling.agents.ready import checklist_text

            passages.append({"source_id": "NESTLING-CHECKLIST", "page_label": None, "text": checklist_text()})
        verdict = judge(example.inputs["question"], out["answer"], passages)
        if upload and verdict.get("score") is not None:
            for old in stored.client.list_feedback(run_ids=[run.id], feedback_key=["faithfulness"]):
                stored.client.delete_feedback(old.id)  # one judge verdict per run
            stored.client.create_feedback(run.id, key="faithfulness", score=int(verdict["faithful"]),
                                          value=verdict["score"], comment=json.dumps(verdict["claims"])[:4000],
                                          source_info={"judge": JUDGE_MODEL, "version": JUDGE_VERSION})
        return {"case_id": example.metadata["case_id"], "scenario_type": example.metadata["scenario_type"], "agent": agent,
                "faithful": verdict.get("faithful"), "claim_support": verdict.get("score"),
                "unsupported": " | ".join(c["claim"] for c in verdict.get("claims", []) if c.get("verdict") != "supported"),
                "question": example.inputs["question"], "answer": out["answer"], "error": verdict.get("error")}

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        rows = [r for r in pool.map(work, items) if r]
    return sorted(rows, key=lambda r: r["case_id"])


def summary(rows: list[dict]) -> dict:
    judged = [r for r in rows if r["faithful"] is not None]
    return {
        "faithfulness": round(sum(r["faithful"] for r in judged) / len(judged), 4) if judged else None,
        "mean_claim_support": round(sum(r["claim_support"] for r in judged) / len(judged), 4) if judged else None,
        "n_judged": len(judged), "n_judge_errors": len(rows) - len(judged), "pass_bar": ">= 0.9",
        "judge": JUDGE_MODEL, "judge_version": JUDGE_VERSION,
    }


def export(rows: list[dict], prefix: str) -> Path:
    RESULTS_DIR.mkdir(exist_ok=True)
    path = RESULTS_DIR / f"{prefix}_{date.today().isoformat()}_judge.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def calibration_sheet(rows: list[dict], n: int = 20) -> Path:
    """A sheet for the owner to label (plan §9.2: calibrate the judge on at least 15 cases).

    Takes every judged-unfaithful case plus faithful ones spread across agents, up to n.
    Fill `human_faithful` (Y/N) and run `agreement()` on the file.
    """
    unfaithful = [r for r in rows if r["faithful"] is False]
    faithful = [r for r in rows if r["faithful"]]
    picked = (unfaithful + faithful[:: max(1, len(faithful) // max(1, n - len(unfaithful)))])[:n]
    path = RESULTS_DIR / f"judge_calibration_{date.today().isoformat()}.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["case_id", "agent", "question", "answer", "judge_faithful", "judge_unsupported", "human_faithful", "human_note"])
        writer.writeheader()
        for r in sorted(picked, key=lambda r: r["case_id"]):
            writer.writerow({"case_id": r["case_id"], "agent": r["agent"], "question": r["question"], "answer": r["answer"],
                             "judge_faithful": "Y" if r["faithful"] else "N", "judge_unsupported": r["unsupported"],
                             "human_faithful": "", "human_note": ""})
    return path


def agreement(path: str | Path) -> dict:
    """Judge-vs-human agreement on a filled calibration sheet."""
    rows = [r for r in csv.DictReader(open(path, encoding="utf-8")) if r["human_faithful"].strip().upper() in ("Y", "N")]
    agree = sum(r["judge_faithful"] == r["human_faithful"].strip().upper() for r in rows)
    return {"n_labelled": len(rows), "agreement": round(agree / len(rows), 3) if rows else None}


if __name__ == "__main__":
    from dotenv import find_dotenv, load_dotenv

    load_dotenv(find_dotenv(usecwd=True))
    name = sys.argv[1]
    rows = judge_experiment(name)
    print(json.dumps(summary(rows), indent=2))
    print("wrote", export(rows, prefix=name))
