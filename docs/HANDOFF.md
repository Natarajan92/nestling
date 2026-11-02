# Nestling handoff - 2 November 2026

## Latency campaign closed - R1 retained

All three approved latency evaluations completed 62 cases with 62 verified traces and zero pipeline/judge errors each. **All were rejected**: direct FAST had p95 13.10s despite better quality; direct FAST plus warmup had p95 11.19s but faithfulness 33/37=89.19%; low FAST plus warmup had p95 11.24s but faithfulness 32/36=88.89%, paired R1 29/32 ->28/32, and six abstentions. Do not promote a failed candidate or claim the 8s target passed. R1 remains the answer configuration, p95 12.11s, faithfulness32/35.

The separate owner-approved INR160 campaign closed at **INR146.6423**, zero pending reservations. Unknown-outcome conservative charges remain accounted. Original ledger **INR183.9041** is unchanged; combined v3 accounting **INR330.5464**, below the approved maximum INR343.9041. Scope of three full latency rounds is exhausted; no further paid round is authorized by this campaign.

After measurements, API startup gained an explicit default-off `NESTLING_PREWARM_SOURCES=1` option. It initializes only the cached source handle, with a five-second maximum wait; failures/timeouts retain a fixed degraded state and allow health/Guardian service. A timed-out network thread may finish later. R1 graph flags, FAST defaults, MAIN generation and strict verification are unchanged. This is operational cold-start work: the observed ~2.5s startup duration is neither a proven per-request saving nor a new measured full-set p95. Historical R1 scores were prewarm-off. See [latency diagnosis and decisions](latency_improvements.md). Source changes after measurement deliberately prevent mixing them into an old live checkpoint.

Final regression verification and refreshed submission artifacts accompany this checkpoint; use the dated [latency QA](../evals/results/golden_v3/qa/latency-final-summary.json). Full source passages/checkpoints remain excluded from the submission ZIP. No deployment, Pinecone writes, new lesson versions, judge changes or frozen-label changes occurred.

## Submission state

Owner deadline: **2 November, 10:00 AM IST**; official cutoff **noon IST**, per owner clarification. The morning tasks are actual-output human calibration and recording/linking the Loom. Public hosting has not been deployed. Start with [the submission checklist](SUBMISSION.md) and [the canonical report](week4_report.md).

Sole active Ask dataset: `evals/golden_v3.csv`, 62 unchanged reviewed cases, normalized SHA256 `8075c270caa94751047580136d7588ba1d49a51fb9a194688c54be92fc387012`. Latest owner clarification: all shortlisted questions are their own; record **owner-attested human authorship/review**, not independent verification. Freeze record: `evals/golden_v3.freeze.json`. Strict LangSmith readback checked dataset `nestling-golden-v3`, ID `074666bd-96ef-48a5-be48-8500785de4ed`.

The Submission40 view takes lexicographically first IDs by stratum (20 happy / 12 edge / 6 known-fail / 2 adversarial), selected after baseline and before the first improvement measurement without using scores. It is a presentation view, not another dataset or unseen holdout. All 62 cases remain primary regression gates. Source labels have disclosed limitations, including B11 requiring USER-POLICY without an attachment; never silently repair frozen expectations.

## Selected implementation and evidence

**Retain Round 1**: citation parser now preserves complete multi-hyphen source IDs. All 62 cases complete with verified traces in each of baseline/R1/R2/R3; zero pipeline/judge errors. R1 faithfulness 32/35=91.43%, paired baseline 27/33 -> 30/33, task completion 52/62=83.87%, routing 58/62=93.55%, escalation 18/18, refusal 62/62, p95 12.11s, mean pipeline INR 0.719. Latency still fails the 8s target. Faithfulness denominators exclude zero-claim answers; inspect coverage and paired/error-sensitivity analyses.

R2's short-answer prompt was rejected (task completion 48/62, 10 abstentions). R3's compact verifier response was rejected (task completion 47/62, paired R1 faithfulness 29/30 -> 27/30, mean INR 0.753). R3 candidate verifier code/tests remain available but **compact_verifier is disabled in the app**. Generation prompt and active tag return to R1. Models, safety rules, judge and labels stayed fixed across measurements. Saved plans/decisions/raw results preserve negative experiments; never rewrite them to imply every change improved outcomes.

Runtime app version `v7_vector_safe+lessons`, full DeepSeek MAIN strict verifier, staged retrieval. Nebius MAIN `deepseek-ai/DeepSeek-V4-Pro`, FAST `deepseek-ai/DeepSeek-V4.1-Flash`; independent evaluation judge `Qwen/Qwen3-235B-A22B-Instruct-2507`. No Anthropic runtime calls. Plan section 2 constitution controls; section 9.4 specifies trace metadata.

## Evaluation and authorization

`evals.v3_run` owns request reservations/provenance, successful-output caching, same-protocol judging and verified LangSmith exports. Artifacts: `evals/results/golden_v3/`. Owner authorized one fresh INR 350 shared cap for baseline and up to 3 improvement rounds with deidentified traces. The original four measurements are complete: **INR 183.9041 accounted, zero pending reservations**. The separately approved latency campaign and its closed budget are recorded above; the ledgers stay separate. Costs are fixed-price token estimates at comparison FX94.91INR/USD; not billing invoices or hosting costs.

Legacy live entry points reject the active v3 dataset. Never reset old budgets, infer successful inference must rerun after a trace-only error, or change pinned runtime during a live round. No deployment, new Pinecone writes or new lesson versions authorized by this evaluation.

Offline commands:

```powershell
uv run python -m nestling.golden
uv run python -m evals.v3_run --status
uv run python -m evals.v3_compare
uv run --with matplotlib python -m evals.plot_tradeoff
uv run python -m evals.label_calibration --report
```

Human review: `uv run python -m evals.label_calibration`. Exact evidence is read from saved checkpoints; local HTML packet `.superpowers/sdd/plan/v3-human-review.html` is available. **0/20 actual outputs labelled**; only the owner supplies human judgments/reasons/date. Reviewing expected answers is separate. Do not report invented agreement or clinical validation.

## Application and media

All 12 current lesson versions have owner approval of every scene and saved source-fidelity checks. Original six: bathing v1, burping v1, latching v2, cord-care v4, holding v3, swaddling v5. Prenatal: labour-room readiness v1, yoga class preparation v1, breathing v1, bed movement v1, stair comfort v2, preparing safely for birth v1. Never modify those storyboards/reviews/media under an existing approval. Media in `lessons/<id>/renders/` is ignored; securely copy approved files to a new host. Missing media or mismatched approval hides the lesson.

Local web port 3000 / API port 8010. Frontend `NEXT_PUBLIC_API_URL=http://127.0.0.1:8010` is a build-time value. API health `/api/health`; origins from `NESTLING_WEB_ORIGINS`. Personal profile/journal/checklist stay in browser `nestling:` keys; server uploads are processed in memory and app trace contents are hidden. Do not send personal inputs to evaluation traces.

Dated UI evidence remains `evals/results/ui_qa_2026-11-01.json`: navigation fixes, mobile/desktop flows and all 12 lesson publication checks. Real devices, microphone and native sharing still need manual testing. New v3 QA evidence must be read from its saved QA artifacts; never promote old test counts as a fresh run.

## Publication and cleanup

Owner explicitly authorized publishing/merging changes and removing old Ask datasets/results from GitHub history. Development branch was `evals/golden-v3-iterations`. Old Ask files were SHA-verified into ignored `.superpowers/sdd/archive/old-ask-files/`; full private Git backup `.superpowers/sdd/archive/before-v3-rewrite.bundle` verifies. Do not upload private backups or Codex refs. Keep current lesson/QA evidence distinct from retired Ask benchmarks.

History cleanup is published and verified across all five GitHub branches; local main tracks cleaned origin/main. The [cleanup record](github_cleanup.md) documents exact-tree verification and the limitation for GitHub-managed closed PR refs/cached commits. Public deployment still needs separate approval. Private local backups retain the old objects for recovery and must never be pushed.
