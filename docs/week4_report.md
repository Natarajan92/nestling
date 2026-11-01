# Nestling · Week 4 evaluation report

## Evaluation one-liner

Evaluate Nestling Ask on emergency escalation, routing, source faithfulness, p95 latency and mean INR cost, using one frozen 62-case regression set and a 40-case submission view; compare a fresh baseline with targeted changes through code scoring and a separate Qwen judge. Targets: 100% escalation, ≥90% routing/faithfulness, p95 <8s and mean <INR2.

## Agent under test

Nestling's current LangGraph Ask pipeline: code-owned Guardian → Concierge → specialist/retrieval → runtime Verifier, with approved fixed lessons where applicable. DeepSeek-V4-Pro handles specialists/verification and DeepSeek-V4.1-Flash handles classification/routing; the evaluation judge is Qwen3-235B on Nebius.

## User outcome

A first-time parent in India gets prompt danger-sign escalation or relevant, sourced help without diagnoses, medicine doses or invented policy clauses. A safe abstention is reported separately from completing the request.

## Metrics and judge method

| Metric | Scoring method / user meaning |
| --- | --- |
| Escalation recall | Code: correctly escalated ÷ expected-danger cases; false alarms shown separately. |
| Routing accuracy | Code: selected route is one of the reviewed allowed routes. |
| Faithfulness | Qwen: every extracted factual claim supported by saved evidence; errors/zero claims cannot automatically pass. |
| p95 latency | Code: nearest-rank 95th percentile of pipeline response time, excluding offline judge. |
| Mean cost | Code: average pipeline token cost in INR; judge spend and reservations separately tracked. |

[Code evaluators](../evals/evaluators.py) and [judge prompt/schema](../evals/v3_run.py) define the rubric. Supplemental task completion requires expected behavior, required content and avoidance constraints all to pass; visible source-ID completeness is a code format diagnostic, not clinical truth.

## Golden dataset

[Frozen v3](../evals/golden_v3.csv): 62 owner-reviewed cases, 20 happy / 26 edge / 12 known-fail / 4 adversarial. The latest owner clarification identifies all 62 as the owner's own: owner-attested human-authored, not independently verified; no explanation for the earlier differing interpretation is inferred.

SHA-256: `8075c270caa94751047580136d7588ba1d49a51fb9a194688c54be92fc387012`. Questions, context and labels remain unchanged; [freeze/review record](../evals/golden_v3.freeze.json) preserves the attestation. The [submission40 selector](../evals/golden_v3.submission40.json) takes lexicographically first IDs by stratum (20/12/6/2), defined after baseline and before first improvement measurement without scores; it is retrospective, not an unseen holdout or preregistered benchmark. All 62 failures remain the primary gates.

## Pass bars

| Gate | Target |
| --- | --- |
| Escalation / refusal | 100% / 100% |
| Routing / faithfulness | ≥90% / ≥90% |
| p95 latency | <8 seconds |
| Mean / p95 pipeline cost | <INR2 / <INR2 |

Source-ID match is diagnostic with no separate pass bar; source registration and owner review are not clinical validation. B11 still requests USER-POLICY without an attachment, so its citation failure can reflect a reference-label limitation.

## Instrumentation

Each case has a LangSmith root linked to its frozen example, with LangGraph/model/tool child runs and read-back verification. Plan §9.4 metadata records case/scenario, dataset hash/version, pipeline/prompt/model versions, expected/predicted escalation and route, refusal, sources, correctness, latency, tokens, cost and errors; rule IDs and retrieval mode remain inspectable.

Traces use frozen test inputs, without browser profiles or uploaded personal documents. Successful outputs/evidence persist before judging; retries reuse completed inference, and request reservations share the owner-authorized ₹350 cap.

## Baseline run

[Baseline project](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/122b1a9c-81b7-4ee4-9408-3e1d05498c0a); verified example [H01](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/122b1a9c-81b7-4ee4-9408-3e1d05498c0a/r/859df4a7-0007-4cda-9573-c2bce042771f?poll=true). Saved run `nestling-ask-golden-v3-baseline-817ee67b`; 62 completed cases, zero pipeline errors.

| Metric | Full-set baseline | n |
| --- | ---: | ---: |
| escalation_recall | 100.0% | 18 |
| refusal_accuracy | 100.0% | 62 |
| routing_accuracy | 95.2% | 62 |
| citation_match | 69.6% | 46 |
| p95_latency_s | 22.5500 | 62 |
| mean_cost_inr | 0.6810 | 62 |
| p95_cost_inr | 1.4280 | 62 |
| Faithfulness | 82.9% | 35 valid / 38 eligible |
| Task completion | 75.8% | 62 |

Abstentions: 6; judge errors: 0. Faithfulness and latency targets are assessed on the full set, even if the 40-case view scores better.

Baseline targets missed: p95_latency_s, faithfulness.

## Failure analysis

Top three overlapping baseline clusters; INR figures are observed pipeline spend on affected cases, not losses to parents, savings estimates or additive totals.

| Failure mode | Frequency | Observed INR | Qualitative parent impact | Example trace |
| --- | ---: | ---: | --- | --- |
| task incomplete | 15 | 13.2397 | Request remains partly unanswered | [H07](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/122b1a9c-81b7-4ee4-9408-3e1d05498c0a/r/3cc681e6-6164-4eec-a2b3-4ca97d8669c8?poll=true) |
| expected-source mismatch | 14 | 13.0142 | Expected reference trail is absent | [H07](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/122b1a9c-81b7-4ee4-9408-3e1d05498c0a/r/3cc681e6-6164-4eec-a2b3-4ca97d8669c8?poll=true) |
| unsupported claims | 6 | 6.2362 | A factual assertion lacks supplied evidence | [H09](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/122b1a9c-81b7-4ee4-9408-3e1d05498c0a/r/fab7efed-c717-4c2b-9ab6-f1caf50cdf5e?poll=true) |

## Improvement hypotheses

Only saved pre-call hypotheses are listed; unmeasured changes are proposals, not results. Three measured changes are complete, including the rejected candidates; all decisions and regressions remain visible.

| Round | Pre-call hypothesis / one lever | Target cluster | Predicted direction |
| --- | --- | --- | --- |
| round1 | Prevent matching a source-ID suffix inside an already valid citation, preserving multi-hyphen source markers and evidence selection before verification. This should reduce false abstentions without changing models or trusted sources. One regex boundary in nestling/agents/__init__.py::_BARE; no prompt, model, retrieval, judge or safety-rule changes. | Observed H01 visible ICMR citation corruption; deterministic mixed-source evidence pruning; H07 false abstention is a candidate mechanism, not yet proven. | Broken visible source markers fall to zero; substantive task fulfillment improves and abstention falls; paired faithfulness does not fall; latency/cost stay stable or improve. |
| round2 | The specialist over-generates tangential timelines, food quantities and background claims. A source-focused90-word/three-point answer budget should reduce unsupported material and verifier work while preserving required answers. Specialist BASE_PROMPT only: exact-question focus, at most90 words and three concise points; omit unsolicited background. Bump app prompt tag only to identify this change. | Remaining 12.11s p95 latency; ten task-incomplete answers and unnecessary factual claims after citation repair. | Lower pipelinep95 and mean/p95cost; source faithfulness and task fulfillment stable or higher; no increase in abstention or safety/refusal errors. |
| round3 | Repeating every supported claim in verifier output adds tokens and latency. Return only the total checked count and unsupported claims while preserving the same MAIN model, full strict scope and repair path. Compact verifier response representation plus app activation/trace tag; generation prompt restored exactly to retained R1. No model, judge, source, safety-rule or rewrite-policy change. | Remaining 12.11s retained R1p95 and checker output repetition: five slowestR1 checks repeated41claims,34supported,using1466outputtokens; other provider/retrieval tails remain. | Lower checker/pipeline latency and mean token cost; paired faithfulness and task fulfillment stable or higher; no increase in abstention or safety errors. This does not guarantee the8s target because retrieval/classifier tails remain. |

## Post-improvement results

Latest completed: **round3** (reject). Selected retained candidate: **round1** (keep).

Shared evaluation ledger: **₹183.9041 / ₹350 accounted** across pipeline and judge requests, including any retained unknown-outcome reservations. This is measured evaluation spend, not an estimate of parent harm.

### Incremental baseline → round1

Scope: full 62-case comparison; 62 identical case IDs.

| Metric | Previous on same IDs | Current | Delta |
| --- | ---: | ---: | ---: |
| escalation_recall | 100.0% | 100.0% | +0.00 pp |
| refusal_accuracy | 100.0% | 100.0% | +0.00 pp |
| routing_accuracy | 95.2% | 93.5% | -1.61 pp |
| citation_match | 69.6% | 76.1% | +6.52 pp |
| p95_latency_s | 22.5500 | 12.1100 | -10.4400 |
| mean_cost_inr | 0.6810 | 0.7190 | +0.0380 |
| p95_cost_inr | 1.4280 | 1.5340 | +0.1060 |
| Faithfulness (paired valid, n=33) | 81.8% | 90.9% | +9.09 pp |
| Task completion (paired valid, n=62) | 75.8% | 83.9% | +8.06 pp |

Faithfulness eligible: 38 → 37; paired valid n=33; errors/nulls-as-false n=37. Conservative support: 75.7% → 86.5%. Visible full IDs: 49/52 → 52/52. Higher latency/cost deltas are regressions.

**Decision: keep.** Deterministic citation corruption and evidence pruning fixed. Full 62-case safety/refusal remain100%; visible full source markers 49/52→52/52; paired faithfulness 27/33→30/33; task fulfillment 47/62→52/62; p95 latency22.55→12.11s. Mean pipeline cost0.681→0.719INR is a measured tradeoff.

Current round's unpaired headline: faithfulness 91.4%, 35 valid / 37 eligible; task completion 83.9%, n=62. Use the paired table for the improvement claim.

Abstentions: 6 → 5. Keep/revert decisions remain in the [detailed report](v3_evaluation_report.md).

Observed case regressions (previous pass → current fail): route_match: 1 ([E03](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/467aa6be-d863-4dee-92e5-1b09ca8c8824/r/4f19f4b9-ff19-4977-8d26-4e8cec9c7a7f?poll=true)); citation_match: 2 ([M04](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/467aa6be-d863-4dee-92e5-1b09ca8c8824/r/dc9df9c2-29cf-4a15-8a2f-75161a13da76?poll=true), [M12](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/467aa6be-d863-4dee-92e5-1b09ca8c8824/r/0e9dde58-c1d7-4318-99d8-56ddb5bce86f?poll=true)); faithful: 1 ([F07](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/467aa6be-d863-4dee-92e5-1b09ca8c8824/r/8495c521-5683-4a1d-bffa-5b60e6b61ec8?poll=true)); task_fulfilled: 2 ([H17](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/467aa6be-d863-4dee-92e5-1b09ca8c8824/r/64e9db42-3dd4-478d-a4b7-fe14643d0870?poll=true), [M04](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/467aa6be-d863-4dee-92e5-1b09ca8c8824/r/dc9df9c2-29cf-4a15-8a2f-75161a13da76?poll=true)).

### Incremental round1 → round2

Scope: full 62-case comparison; 62 identical case IDs.

| Metric | Previous on same IDs | Current | Delta |
| --- | ---: | ---: | ---: |
| escalation_recall | 100.0% | 100.0% | +0.00 pp |
| refusal_accuracy | 100.0% | 100.0% | +0.00 pp |
| routing_accuracy | 93.5% | 95.2% | +1.61 pp |
| citation_match | 76.1% | 73.9% | -2.18 pp |
| p95_latency_s | 12.1100 | 9.2300 | -2.8800 |
| mean_cost_inr | 0.7190 | 0.5900 | -0.1290 |
| p95_cost_inr | 1.5340 | 1.3430 | -0.1910 |
| Faithfulness (paired valid, n=30) | 93.3% | 90.0% | -3.33 pp |
| Task completion (paired valid, n=62) | 83.9% | 77.4% | -6.45 pp |

Faithfulness eligible: 37 → 39; paired valid n=30; errors/nulls-as-false n=37. Conservative support: 86.5% → 75.7%. Visible full IDs: 52/52 → 50/50. Higher latency/cost deltas are regressions.

**Decision: reject.** The 90-word/three-point prompt reduced latency/cost but worsened useful-answer coverage and paired faithfulness. Revert to the retainedround 1prompt beforeround 3.

Current round's unpaired headline: faithfulness 90.9%, 33 valid / 39 eligible; task completion 77.4%, n=62. Use the paired table for the improvement claim.

Abstentions: 5 → 10. Keep/revert decisions remain in the [detailed report](v3_evaluation_report.md).

Observed case regressions (previous pass → current fail): citation_match: 1 ([M24](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/935ba1ed-ca65-4e76-b4dc-1a03a482c5a5/r/70c75f7c-5958-442b-9230-162d43d70554?poll=true)); faithful: 1 ([E10](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/935ba1ed-ca65-4e76-b4dc-1a03a482c5a5/r/3eb1a290-c01b-41bb-a7d8-a3fe184c5a56?poll=true)); task_fulfilled: 6 ([B09](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/935ba1ed-ca65-4e76-b4dc-1a03a482c5a5/r/66a199f7-95d9-4e38-9e4e-5a6034cd08fb?poll=true), [B11](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/935ba1ed-ca65-4e76-b4dc-1a03a482c5a5/r/6a651e63-f66d-4746-90cb-c03b9bf7f1d2?poll=true), [B13](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/935ba1ed-ca65-4e76-b4dc-1a03a482c5a5/r/966b1159-99bf-40e7-adeb-acd8af2f7232?poll=true)).

Declared restored base: **round1** plus the new lever; chronological predecessor round2 used another configuration. The latter difference is not a one-lever causal comparison.

### Incremental round1 → round3

Scope: full 62-case comparison; 62 identical case IDs.

| Metric | Previous on same IDs | Current | Delta |
| --- | ---: | ---: | ---: |
| escalation_recall | 100.0% | 100.0% | +0.00 pp |
| refusal_accuracy | 100.0% | 100.0% | +0.00 pp |
| routing_accuracy | 93.5% | 93.5% | +0.00 pp |
| citation_match | 76.1% | 76.1% | +0.00 pp |
| p95_latency_s | 12.1100 | 11.8900 | -0.2200 |
| mean_cost_inr | 0.7190 | 0.7530 | +0.0340 |
| p95_cost_inr | 1.5340 | 1.5740 | +0.0400 |
| Faithfulness (paired valid, n=30) | 96.7% | 90.0% | -6.67 pp |
| Task completion (paired valid, n=62) | 83.9% | 75.8% | -8.06 pp |

Faithfulness eligible: 37 → 37; paired valid n=30; errors/nulls-as-false n=36. Conservative support: 86.1% → 75.0%. Visible full IDs: 52/52 → 48/48. Higher latency/cost deltas are regressions.

**Decision: reject.** The compact verifier candidate worsened paired faithfulness, task fulfillment and abstention. Its 0.22s p95 latency improvement did not offset lower quality and higher mean cost; reject under the recorded round 3 gates and retain round 1.

Current round's unpaired headline: faithfulness 90.3%, 31 valid / 37 eligible; task completion 75.8%, n=62. Use the paired table for the improvement claim.

Abstentions: 5 → 6. Keep/revert decisions remain in the [detailed report](v3_evaluation_report.md).

Observed case regressions (previous pass → current fail): route_match: 1 ([H16](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/1b51a018-3346-4d40-a602-bc91afee8530/r/774b1269-2a74-411d-adda-0d7667bc551d?poll=true)); citation_match: 1 ([M08](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/1b51a018-3346-4d40-a602-bc91afee8530/r/cbb43248-1190-47dd-a49a-60ed07b6d94b?poll=true)); faithful: 2 ([E10](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/1b51a018-3346-4d40-a602-bc91afee8530/r/0d9a506d-ad50-48cb-8304-f24cd7c99454?poll=true), [M10](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/1b51a018-3346-4d40-a602-bc91afee8530/r/46be8e51-a157-4d64-ac92-6df4c207527b?poll=true)); task_fulfilled: 6 ([B09](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/1b51a018-3346-4d40-a602-bc91afee8530/r/b37f27e8-2de2-448c-a7e7-22e41b65a75a?poll=true), [B11](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/1b51a018-3346-4d40-a602-bc91afee8530/r/0a93bc9c-0899-4aad-88d6-2b0fed8436f0?poll=true), [E10](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/1b51a018-3346-4d40-a602-bc91afee8530/r/0d9a506d-ad50-48cb-8304-f24cd7c99454?poll=true)).

### Overall baseline → round1 (selected retained candidate)

Scope: full 62-case comparison; 62 identical case IDs.

| Metric | Previous on same IDs | Current | Delta |
| --- | ---: | ---: | ---: |
| escalation_recall | 100.0% | 100.0% | +0.00 pp |
| refusal_accuracy | 100.0% | 100.0% | +0.00 pp |
| routing_accuracy | 95.2% | 93.5% | -1.61 pp |
| citation_match | 69.6% | 76.1% | +6.52 pp |
| p95_latency_s | 22.5500 | 12.1100 | -10.4400 |
| mean_cost_inr | 0.6810 | 0.7190 | +0.0380 |
| p95_cost_inr | 1.4280 | 1.5340 | +0.1060 |
| Faithfulness (paired valid, n=33) | 81.8% | 90.9% | +9.09 pp |
| Task completion (paired valid, n=62) | 75.8% | 83.9% | +8.06 pp |

Faithfulness eligible: 38 → 37; paired valid n=33; errors/nulls-as-false n=37. Conservative support: 75.7% → 86.5%. Visible full IDs: 49/52 → 52/52. Higher latency/cost deltas are regressions.

![Quality, latency and cost tradeoffs](media/tradeoff.png)

![Completed-round metrics](media/metrics_by_version.png)

## Human-versus-judge agreement

**PENDING human labels.** No agreement percentage is defined for an unlabelled sample.

| Dimension | Human-labelled / sample | Agreement | False passes / false failures |
| --- | ---: | ---: | ---: |
| faithfulness | 0/20 | pending | 0 / 0 |
| task_fulfillment | 0/20 | pending | 0 / 0 |

Reviewing expected answers is separate from judging actual saved outputs. The owner labels faithfulness/task completion in `evals/results/golden_v3/human_review.csv`; saved source passages and judge reasons support disagreement review, without inventing labels. This purposive sample does not establish clinical validation or population accuracy.

```powershell
uv run python -m evals.label_calibration --report
```

## What is next and production monitoring

Prioritize the retained candidate's remaining failed bars, complete human/judge review and record the demo. This previously exposed regression set needs a future independent holdout before claiming generalization.

Proposed alerts: weekly faithfulness/task completion drop >5 percentage points; p95 cost >INR2.50; sustained p95 latency >8s; guardrail rate >2× baseline; tool errors >5% in an hour. These are monitoring plans, not deployed-service claims.

**Loom:** pending owner recording/link

Evidence: [detailed v3 report](v3_evaluation_report.md), [deliverable checklist](SUBMISSION.md), [saved v3 outputs](../evals/results/golden_v3/). No retired-run metrics are used.
