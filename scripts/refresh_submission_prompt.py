"""Refresh the finishing prompt from completed saved v3 evidence; offline only."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def build():
    from evals.v3_compare import ROUND_ORDER, compare_rounds, load_round
    from nestling import golden
    results = ROOT / "evals/results/golden_v3"
    runs = []
    for name in ROUND_ORDER:
        folder = results / name
        summary = folder / "summary.json"
        if summary.exists() and json.loads(summary.read_text(encoding="utf-8"))["progress"]["complete"]:
            runs.append(load_round(folder))
    kept = [r for r in runs if (r["directory"] / "decision.json").exists() and
            json.loads((r["directory"] / "decision.json").read_text(encoding="utf-8")).get("decision")=="keep"]
    selected = kept[-1] if kept else runs[0]
    lines = ["# Nestling submission finishing prompt — saved v3 evidence", "",
        "Finish Nestling's Week 4 submission. Make the README understandable in under two minutes. "
        "Read docs/HANDOFF.md, docs/NESTLING_PLAN.md, docs/week4_report.md and docs/v3_evaluation_report.md first. "
        "The owner's target is 2 November 2026, 10:00 AM IST; the owner-confirmed cutoff is noon IST.", "",
        f"Retained measured configuration: **{selected['directory'].name}**. "
        "Completed rejected experiments stay visible and must not be promoted because they are newer.", "",
        "| Run | Escalation | Refusal | Routing | Faithful / valid | Task fulfilled | p95 s | Mean INR |",
        "|---|---|---|---|---|---|---|---|"]
    for run in runs:
        rows, summary = run["rows"], run["summary"]
        esc = [r for r in rows if r["expected_escalate"]]
        faith = [r for r in rows if r["faithfulness_eligible"] and type(r["faithful"]) is bool and not r["judge_error"]]
        task = [r for r in rows if type(r["task_fulfilled"]) is bool and not r["judge_error"]]
        values = [run["directory"].name,
                  f"{sum(r['predicted_escalate'] and not r['error'] for r in esc)}/{len(esc)}",
                  f"{sum(r['refusal_match'] for r in rows)}/{len(rows)}",
                  f"{sum(r['route_match'] for r in rows)}/{len(rows)}",
                  f"{sum(r['faithful'] for r in faith)}/{len(faith)}",
                  f"{sum(r['task_fulfilled'] for r in task)}/{len(task)}",
                  str(summary["metrics"]["p95_latency_s"]["value"]),
                  str(summary["metrics"]["mean_cost_inr"]["value"])]
        lines.append("| " + " | ".join(values) + " |")
    paired = compare_rounds(results / "baseline", selected["directory"])["faithfulness"]
    lines += ["", f"Primary paired comparison: baseline → retained {selected['directory'].name}; "
        f"{paired['baseline']:.2%} → {paired['candidate']:.2%}, n={paired['paired_valid_n']}, "
        f"delta {paired['delta_pp']:+.2f} percentage points. Headline fractions can have different eligible cohorts; "
        "retain paired comparisons, zero-claim answers, abstentions and errors.", ""]
    old = json.loads((results / "spend.json").read_text(encoding="utf-8"))
    new_path = results / "latency_budget/spend.json"
    new = json.loads(new_path.read_text(encoding="utf-8")) if new_path.exists() else {"accounted_inr":0}
    lines += [f"Budget accounting: original v3 ledger INR {old['accounted_inr']:.4f}; "
        f"latency campaign INR {new['accounted_inr']:.4f} / 160; combined "
        f"INR {old['accounted_inr']+new['accounted_inr']:.4f}. The approved combined maximum is INR343.9041. "
        "Unknown-outcome reservations remain accounted. Do not reset or merge ledgers.", "",
        "## Rules", "",
        f"- Sole active Ask dataset: golden_v3, 62 unchanged cases, normalized SHA256 `{golden.SHA256}`. "
        "Owner-attested human authorship/review is not independent verification or clinical validation.",
        "- Submission40 is a retrospective stratified view defined after baseline and before R1, without scores. "
        "Full 62-case results remain primary; this exposed regression set does not establish unseen-case accuracy.",
        "- Preserve all raw results, source/label limitations, pre-call plans, decisions and trace evidence. "
        "Never fill human labels, manufacture a Loom URL or claim an unmet latency target passed.",
        "- The owner approved INR160 for compatibility checks and up to three full latency rounds with the same Qwen judge "
        "and deidentified LangSmith traces. Read the ledger/remaining scope before any further paid action; "
        "new spending beyond the approval needs explicit approval.",
        "- No deployment, Pinecone writes, lesson-version changes, secret publication or personal-data caching. "
        "Existing exact-version lesson approvals remain unchanged.", "",
        "## Finish and verify", "",
        "1. Keep README concise: product, three differentiators, real synthetic-profile screenshot, actual retained scorecard, "
        "measured paired improvement and limitations, architecture, quickstart and evidence links.",
        "2. Regenerate reports and plots offline: `uv run python -m evals.v3_compare`; "
        "`uv run --with matplotlib python -m evals.plot_tradeoff`. Keep the canonical report under250 lines in handout order.",
        "3. Preserve three leading failure clusters, observed pipeline costs, parent impact, each hypothesis, actual metric "
        "deltas/regressions and keep/reject decisions. Explain FAST reasoning and startup observations only from saved evidence.",
        "4. Re-execute notebooks/09_v3_evaluation.ipynb offline. Regenerate PDF before ZIP: "
        "`uv run python scripts/build_submission_pdf.py`; `uv run python scripts/package_submission.py`. "
        "Inspect every page; verify provenance and ZIP integrity. Exclude source passages, secrets and private backups.",
        "5. Owner records the five-minute Loom using docs/loom_script.md, then supplies the real link. "
        "Owner labels actual saved outputs using `uv run python -m evals.label_calibration`; "
        "`--report` reports agreement only for entered labels. Expected-answer review does not label actual-output quality.",
        "6. Run appropriate Python/web checks after changes. Preserve the documented development dependency advisory "
        "and physical-device/microphone/native-sharing limitations. Do not infer security certification from unit tests.",
        "7. Publish only verified code/results under the owner's GitHub authorization. "
        "Normal-ref old Ask history cleanup is complete; GitHub closed-PR caches may retain old objects. "
        "Do not repush old private branches/backups. Public deployment requires separate approval.", ""]
    target = ROOT / "docs/submission_finish_prompt.md"
    target.write_text("\n".join(lines), encoding="utf-8")
    print(f"Finishing prompt refreshed from {len(runs)} completed runs; retained {selected['directory'].name}")


if __name__=="__main__":
    build()
