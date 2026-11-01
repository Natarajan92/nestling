# Nestling · Week 4 deliverables

**Track 3: original agent evaluation with LangSmith.** Start with the [canonical Week 4 report](week4_report.md), then inspect the [detailed v3 results](v3_evaluation_report.md) and a linked case trace. The canonical report preserves the Loom field and excludes incomplete rounds from final results.

| Handout deliverable | Evidence | Current status |
| --- | --- | --- |
| Use case, framework, five primary metrics and pass bars | [Week 4 report](week4_report.md) | Defined; baseline measured |
| Reviewed 30–50-case presentation | [40 questions](../evals/results/golden_v3/submission40_questions.csv), [selector/timing](../evals/golden_v3.submission40.json) | 20 happy / 12 edge / 6 known-fail / 2 adversarial |
| Frozen full regression set and provenance | [62-case v3](../evals/golden_v3.csv), [hash/review record](../evals/golden_v3.freeze.json) | Sole active dataset; all 62 remain primary gates |
| Case outputs, scores and trace evidence | [Baseline cases](../evals/results/golden_v3/baseline/cases.csv), [presentation40 results](../evals/results/golden_v3/baseline/submission40_results.csv), [round folders](../evals/results/golden_v3/) | Baseline and all three improvement rounds complete and verified |
| Three leading failure modes and observed costs | [Canonical report](week4_report.md#failure-analysis) | Available; qualitative parent impact, no invented loss estimates |
| Three targeted changes and measured deltas | Pre-call `plan.json`, completed round artifacts, post-review `decision.json`; [detailed report](v3_evaluation_report.md) | R1 kept; R2 and R3 rejected; all results preserved |
| Executed offline notebook | [Notebook 09](../notebooks/09_v3_evaluation.ipynb) | Saved metrics, decisions, paired comparisons and H07 trace evidence; no API calls |
| Prompts, rubrics and supporting implementation | [Code evaluators](../evals/evaluators.py), [judge schema/prompt and runner](../evals/v3_run.py), [specialists](../nestling/agents/), [Verifier](../nestling/verifier.py) | Included; round `judge.json` holds actual judgments |
| Human-versus-judge comparison | [Human review CSV](../evals/results/golden_v3/human_review.csv); command below | Pending actual human output labels |
| Short Loom | Canonical report's **Loom** field | Pending owner recording/link |

All 62 questions are **owner-attested human-authored and owner-reviewed**, following the latest clarification; authorship is not independently verified. The 40-case view was selected lexicographically by stratum after baseline and before the first improvement measurement, without scores; it is retrospective and does not replace full-set failures or establish unseen-case generalization.

**Retained result:** R1, with paired faithfulness improving by 9.09 percentage points against baseline; its 12.11-second p95 latency still misses the 8-second target. Final accounted evaluation spend is **₹183.9041 / ₹350**. Human calibration and the owner's Loom recording remain pending.

Rebuild reports and inspect progress offline:

```powershell
uv run python -m nestling.golden
uv run python -m evals.v3_run --status
uv run python -m evals.v3_compare
uv run python -m evals.label_calibration --report
```

The owner labels saved answers using the exact source evidence and reviewed expectations, then records Y/N judgments, reasons and reviewer/date in `human_review.csv`. Golden-label review is separate from actual-output calibration; no agreement percentage is fabricated. The upload ZIP excludes full source passages; private checkpoints and local review tools retain the evidence.

Local upload artifacts are `output/pdf/Nestling_Week4_Submission.pdf` and `output/submission/Nestling_Week4_Submission.zip`; they are rebuildable and are not stored in Git. Rebuild the ZIP with `uv run python scripts/package_submission.py` after human labels and the Loom link are updated. [GitHub cleanup record](github_cleanup.md).

Live evaluations use the separate `evals.v3_run` commands and one owner-approved ₹350 shared cap; they are not part of report regeneration. Application startup, tests and deployment instructions remain in the [README](../README.md); no deployment is claimed by this submission.
