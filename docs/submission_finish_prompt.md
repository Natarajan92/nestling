# Nestling submission finishing prompt — saved v3 evidence

Finish Nestling's Week 4 submission. Make the README understandable in under two minutes. Read docs/HANDOFF.md, docs/NESTLING_PLAN.md, docs/week4_report.md and docs/v3_evaluation_report.md first. The owner's target is 2 November 2026, 10:00 AM IST; the owner-confirmed cutoff is noon IST.

Retained measured configuration: **round1**. Completed rejected experiments stay visible and must not be promoted because they are newer.

| Run | Escalation | Refusal | Routing | Faithful / valid | Task fulfilled | p95 s | Mean INR |
|---|---|---|---|---|---|---|---|
| baseline | 18/18 | 62/62 | 59/62 | 29/35 | 47/62 | 22.55 | 0.681 |
| round1 | 18/18 | 62/62 | 58/62 | 32/35 | 52/62 | 12.11 | 0.719 |
| round2 | 18/18 | 62/62 | 59/62 | 30/33 | 48/62 | 9.23 | 0.59 |
| round3 | 18/18 | 62/62 | 58/62 | 28/31 | 47/62 | 11.89 | 0.753 |
| latency1 | 18/18 | 62/62 | 58/62 | 35/37 | 55/62 | 13.1 | 0.71 |
| latency2 | 18/18 | 62/62 | 59/62 | 33/37 | 52/62 | 11.19 | 0.703 |
| latency3 | 18/18 | 62/62 | 59/62 | 32/36 | 52/62 | 11.24 | 0.737 |

Primary paired comparison: baseline → retained round1; 81.82% → 90.91%, n=33, delta +9.09 percentage points. Headline fractions can have different eligible cohorts; retain paired comparisons, zero-claim answers, abstentions and errors.

Budget accounting: original v3 ledger INR 183.9041; latency campaign INR 146.6423 / 160; combined INR 330.5464. The approved combined maximum is INR343.9041. Unknown-outcome reservations remain accounted. Do not reset or merge ledgers.

## Rules

- Sole active Ask dataset: golden_v3, 62 unchanged cases, normalized SHA256 `8075c270caa94751047580136d7588ba1d49a51fb9a194688c54be92fc387012`. Owner-attested human authorship/review is not independent verification or clinical validation.
- Submission40 is a retrospective stratified view defined after baseline and before R1, without scores. Full 62-case results remain primary; this exposed regression set does not establish unseen-case accuracy.
- Preserve all raw results, source/label limitations, pre-call plans, decisions and trace evidence. Never fill human labels, manufacture a Loom URL or claim an unmet latency target passed.
- The owner approved INR160 for compatibility checks and up to three full latency rounds with the same Qwen judge and deidentified LangSmith traces. Read the ledger/remaining scope before any further paid action; new spending beyond the approval needs explicit approval.
- No deployment, Pinecone writes, lesson-version changes, secret publication or personal-data caching. Existing exact-version lesson approvals remain unchanged.

## Finish and verify

1. Keep README concise: product, three differentiators, real synthetic-profile screenshot, actual retained scorecard, measured paired improvement and limitations, architecture, quickstart and evidence links.
2. Regenerate reports and plots offline: `uv run python -m evals.v3_compare`; `uv run --with matplotlib python -m evals.plot_tradeoff`. Keep the canonical report under250 lines in handout order.
3. Preserve three leading failure clusters, observed pipeline costs, parent impact, each hypothesis, actual metric deltas/regressions and keep/reject decisions. Explain FAST reasoning and startup observations only from saved evidence.
4. Re-execute notebooks/09_v3_evaluation.ipynb offline. Regenerate PDF before ZIP: `uv run python scripts/build_submission_pdf.py`; `uv run python scripts/package_submission.py`. Inspect every page; verify provenance and ZIP integrity. Exclude source passages, secrets and private backups.
5. Owner records the five-minute Loom using docs/loom_script.md, then supplies the real link. Owner labels actual saved outputs using `uv run python -m evals.label_calibration`; `--report` reports agreement only for entered labels. Expected-answer review does not label actual-output quality.
6. Run appropriate Python/web checks after changes. Preserve the documented development dependency advisory and physical-device/microphone/native-sharing limitations. Do not infer security certification from unit tests.
7. Publish only verified code/results under the owner's GitHub authorization. Normal-ref old Ask history cleanup is complete; GitHub closed-PR caches may retain old objects. Do not repush old private branches/backups. Public deployment requires separate approval.
