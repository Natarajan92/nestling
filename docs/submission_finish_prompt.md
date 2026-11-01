# Nestling submission finishing prompt - current v3 evidence

You are finishing Nestling for the 2 November submission: target 10:00 AM IST, official cutoff 12:00 PM IST. Make the README understandable in under two minutes and prepare every handout artifact except the owner-recorded Loom. Read README.md, docs/week4_report.md, docs/v3_evaluation_report.md, docs/NESTLING_PLAN.md, evals/golden_v3.freeze.json and completed summaries under evals/results/golden_v3/ first.

Selected retained configuration: round1. Latest measured is round3; rejected rounds stay visible and are not promoted.
## Verified measurements - completed full 62-case runs only

| Run | Escalation | Refusal | Routing | Faithful / valid judge | Task fulfilled | p95 seconds | Mean INR | p95 INR |
|---|---|---|---|---|---|---|---|---|
| baseline | 18/18 | 62/62 | 59/62 | 29/35 (82.86%) | 47/62 | 22.55 | 0.681 | 1.428 |
| round1 | 18/18 | 62/62 | 58/62 | 32/35 (91.43%) | 52/62 | 12.11 | 0.719 | 1.534 |
| round2 | 18/18 | 62/62 | 59/62 | 30/33 (90.91%) | 48/62 | 9.23 | 0.59 | 1.343 |
| round3 | 18/18 | 62/62 | 58/62 | 28/31 (90.32%) | 47/62 | 11.89 | 0.753 | 1.574 |

Primary comparison is baseline → retained round1. Paired faithfulness: 81.82% → 90.91% on 33 common valid cases; delta +9.09 percentage points. Overall faithfulness rows use different eligible cohorts; keep both denominators visible. All three approved improvement rounds are complete; no further paid calls are needed. Shared ledger: INR 183.9041 / 350, no pending reservations.

## Rules and current authorization

- Every number comes from saved results. Never invent, relabel, suppress regressions or use partial results as final. Preserve completed measurements. Display ordinary rounding with exact case fractions alongside it.
- Sole active Ask dataset: frozen golden_v3.csv, 62 questions/labels. The owner clarified all 62 shortlisted questions are their own: record owner-attested human authorship, without independent-verification claims. Do not alter rows or hash. The deterministic20/12/6/2 Submission40 view was defined after baseline and before R1; disclose timing and publish full 62 stress results/failures too.
- Only Anand enters human_faithful and human_task_fulfilled. Expected-label review is separate from actual-output calibration. Current review packet: evals/results/golden_v3/human_review.csv; local exact evidence: .superpowers/sdd/plan/v3-human-review.html.
- A fresh INR 350 shared cap is already approved for v3 baseline, judging and up to 3 improvement rounds, with deidentified evaluation traces. Continue authorized work within that cap using evals.v3_run; do not reuse old budgets. Read the live ledger/status before calls; new spending beyond scope/cap needs explicit approval.
- Deployment requires separate approval. Owner already requested old Ask artifact cleanup and removal from GitHub history. Use verified ignored backups, a separate rewrite clone, explicit path filters and captured remote SHA leases. Explain GitHub-managed closed-PR cache limits; never claim those inaccessible refs were erased.
- No new frameworks, secrets, Pinecone writes or lesson-approval changes. Current12 lesson versions retain their exact human approvals.

## Finish in this order

1. README: title/tagline, one-sentence problem, three differentiators, actual local UI image, baseline→accepted-candidate scorecard, honest three-sentence tradeoff story, architecture, quickstart, next priorities and three evidence links. Keep it crisp; operational details go in docs/engineering_notes.md. Do not restore retired v1/v2 benchmark numbers or source files.
2. Regenerate docs/media/tradeoff.png and metrics_by_version.png with uv run --with matplotlib python -m evals.plot_tradeoff. Use completed v3 full 62 summaries only, exact judge denominators, cost-based marker sizes and 90% / 8s target lines. Pairwise tables remain primary for improvement claims.
3. Regenerate canonical docs/week4_report.md in handout order, under 250 lines: one-liner,agent,outcome,metrics/judges,dataset/hash/review,passbars,instrumentation,baseline,failureclusters,costs/parentimpact,hypotheses,incremental+overalldeltas/regressions,humanagreement,nextmonitoring. Include both plots; use actual pipeline spend rather than invented parent-harm currency.
4. Include Submission40 questions/scored outputs and full 62 evidence. Never compare v3 against retired datasets as an improvement delta. Explain known B11 missing-policy citation-label limitation and previously exposed regression-set scope.
5. Update docs/loom_script.md using actual current runs: Today/Guardian zero-LLM emergency/approved lesson/H07 trace proving citation-parser evidence loss/current scorecard/limitations. Owner captures the demo in the morning; keep its link pending until provided.
6. Human calibration: uv run python -m evals.label_calibration; Y/N/skip, exact source evidence before judge verdict, save entered labels only. Then uv run python -m evals.label_calibration --report and regenerate reports. Pending is never 0% or 100% agreement.
7. Screenshot utility: scripts/capture_screenshots.py targets web port 3000 / API port 8010, 390x844,isolated synthetic profile. It blocks provider routes. Do not run general paid Ask; the optional fixed rule-owned example must pass its zero-LLM preflight. Existing hero is an actual local QA capture.
8. Keep docs/deploy_checklist.md exact for Vercel+Render, env names only,CORS,build-timeAPIURL,approved media persistence and five post-deploy checks. Do not deploy.
9. Run full Python tests, web unit tests, lint and production build. Re-execute the v3 comparison notebook offline. Inspect plots/links, scan staged content for secrets, package submission artifacts and publish the owner-authorized cleaned GitHub history only after verification.

## Submission checklist

- Report, dataset/scored results, failure analysis and incremental/overall deltas.
- Actual judge prompt/outputs, human agreement/disagreements when provided.
- LangSmith dataset/project/case evidence; exported evidence must remain useful without private UI access.
- Executed offline notebook, reproducible commands and QA evidence.
- Loom: owner recording/link pending; no fabricated URL.
- State every remaining failed metric bar or incomplete human step clearly.
