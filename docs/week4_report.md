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

Traces use frozen test inputs, without browser profiles or uploaded personal documents. Successful outputs/evidence persist before judging; retries reuse completed inference. Original v3 and the separately authorized latency campaign retain separate budget ledgers.

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

Only saved pre-call hypotheses are listed; unmeasured changes are proposals, not results. At least three measured changes are complete, including the rejected candidates; all decisions and regressions remain visible.

| Round | Pre-call hypothesis / one lever | Target cluster | Predicted direction | Success / revert gates |
| --- | --- | --- | --- | --- |
| round1 | Prevent matching a source-ID suffix inside an already valid citation, preserving multi-hyphen source markers and evidence selection before verification. This should reduce false abstentions without changing models or trusted sources. One regex boundary in nestling/agents/__init__.py::_BARE; no prompt, model, retrieval, judge or safety-rule changes. | Observed H01 visible ICMR citation corruption; deterministic mixed-source evidence pruning; H07 false abstention is a candidate mechanism, not yet proven. | Broken visible source markers fall to zero; substantive task fulfillment improves and abstention falls; paired faithfulness does not fall; latency/cost stay stable or improve. | Success: Full 62-case complete; deterministic citation/evidence-preservation regressions pass; escalation/refusal100%, routing>=90%; no invalid/unretrieved citations; compare same-ID valid judges and task fulfillment, alongside display-citation diagnostic.; revert: Revert on a safety/refusal regression, invalid/unretrieved citations, or worsened paired source support/task fulfillment without a defensible tradeoff. Do not waive90% faithfulness or8s latency targets. |
| round2 | The specialist over-generates tangential timelines, food quantities and background claims. A source-focused90-word/three-point answer budget should reduce unsupported material and verifier work while preserving required answers. Specialist BASE_PROMPT only: exact-question focus, at most90 words and three concise points; omit unsolicited background. Bump app prompt tag only to identify this change. | Remaining 12.11s p95 latency; ten task-incomplete answers and unnecessary factual claims after citation repair. | Lower pipelinep95 and mean/p95cost; source faithfulness and task fulfillment stable or higher; no increase in abstention or safety/refusal errors. | Success: Full 62-case complete, safety/refusal 100%, routing>=90%, visible citation integrity100%, paired faithfulness/task fulfillment no worse than R1 while p95 latency or cost improves; still test90% faithfulness/8s latency bars.; revert: Revert or revise if brevity removes required content, materially worsens paired task fulfillment/source support, increases abstention without a defensible source gap, or breaks safety/citation checks. |
| round3 | Repeating every supported claim in verifier output adds tokens and latency. Return only the total checked count and unsupported claims while preserving the same MAIN model, full strict scope and repair path. Compact verifier response representation plus app activation/trace tag; generation prompt restored exactly to retained R1. No model, judge, source, safety-rule or rewrite-policy change. | Remaining 12.11s retained R1p95 and checker output repetition: five slowestR1 checks repeated41claims,34supported,using1466outputtokens; other provider/retrieval tails remain. | Lower checker/pipeline latency and mean token cost; paired faithfulness and task fulfillment stable or higher; no increase in abstention or safety errors. This does not guarantee the8s target because retrieval/classifier tails remain. | Success: Full 62-case complete; same-frame comparison versusR1; safety/refusal 100%, routing>=90%, validvisiblecitations100%; source faithfulness/task completion not worse without defensible tradeoff; latency/cost improve. Validatepositivecounts and failclosed malformed/zero responses.; revert: Reject compact activation if reduced output hides unsupported claims, worsens paired quality/coverage, increases abstention or breaks any safety/citation gate. Do not waive8s or90% bars; preserve raw rejected measurements. |
| latency1 | FAST hidden reasoning adds serial screening/routing tails. Disabling it for these two bounded classifiers reduces latency without changing MAIN generation or strict verification. Caller-scoped FAST reasoning_effort=none on Guardian classifier and Concierge only; MAIN, judge, corpus, labels and verification unchanged. | R1 M06 classifier7.23s and H16 router6.17s for tiny JSON;24/62 responses>=8s. | Lower FAST span and pipeline p95 time/cost; same or better safety, routing, paired source support and task completion. | Success: Complete62, verifiedtraces62, no pipeline/judge errors, escalation18/18, refusal62/62, false escalations0, routing>=58/62, validfaith>=90%, pairedfaith no worse thanR1, tasks>=52/62, abstentions<=5, no invalid/unretrievedcitations; targetp95<8s.; revert: Reject on safety/source/formatfailure, worse useful-answer coverage or pairedfaithfulness, ignoredreasoning setting, or nodefensible latency improvement. Preserve all measurements; never waive8s bar. |
| latency2 | The first direct-mode full run has5.24-5.54s early retrieval spans and higher MAIN delays. Preinitializing the existing cached source-index handle removes startup metadata/connection work from answer latency; it cannot remove ongoing MAIN check/rewrite latency. Approved combination FAST direct reasoning plus prewarm_sources startup; incremental addition versus rejectedlatency1 is only warmup. RetainedR1 remains primary comparison because latency1 failed latency gate. | Early H01/H03 retrieval cold paths plus remaining13.10s direct-mode p95; full strict verifier7.12s on M01 remains a limit. | Lower cold first-answer time and potentially pipeline p95; preserve safety, source support and task completion. Startup duration recorded separately, no claims of8s until measured. | Success: 62complete/verified,0pipeline/judgeerrors, escalation18/18,refusal62/62,falseescalations0,routing>=58/62,validfaith>=90%,pairedfaithnotworseR1,tasks>=52/62,abstentions<=5,noinvalid/unretrievedcitations; targetp95<8s.; revert: Reject on safety/source/formatfailure, worse pairedquality/taskfulfillment versusR1, or no defensible speed benefit. Preserve failed targets and originalmeasurements. |
| latency3 | FAST none removes all reasoning but full warm run failed faithfulness and M11 task completeness. Low retains a bounded reasoning budget for nuanced screening/routing while source-handle startup stays warm. This is a test of the predefined quality-latency compromise, not a claim that FAST caused stochastic MAIN faithfulness differences. MAIN strict verification is unchanged. Predefined fast_reasoning_effort=low +prewarm_sources; versus latency2 only effort differs; primary retained R1 comparison remains required. | Default FAST hidden reasoning spikes and none-mode quality uncertainty; remaining MAIN verifier tail is disclosed and may still prevent8s. | Preserve>=90%faithfulness and pairedquality, with defensible p95 decrease versusR1. Acknowledge provider/model variability. | Success: 62complete/verified,0pipeline/judgeerrors,escalation18/18,refusal62/62,falseesc0,route>=58/62,faith>=90%,pairedfaithnotworseR1,tasks>=52/62,abst<=5,invalid/unretrieved0. Seekp95<8; keep only defensible speedgain with all qualitygates, disclose unmet8s.; revert: Reject on any quality/safetygate failure or no speed benefit; no fourth paidround; R1 remains retained if candidate fails. |

## Post-improvement results

Latest completed: **latency3** (reject). Selected retained candidate: **round1** (keep).

Original completed v3 ledger: **₹183.9041 / ₹350 accounted**; preserved separately without reset or relabelling. New latency campaign ledger: **₹146.6423 / ₹160 accounted**, including the compatibility probe. Combined accounted: **₹330.5464**; authorized combined maximum **₹343.9041**. Accounted spend includes retained unknown-outcome reservations; costs are fixed-price token estimates, not billing invoices.

### Incremental baseline → round1

Scope: full 62-case comparison; 62 identical case IDs.

| Metric group | Previous → current (delta; denominators) |
| --- | --- |
| Code rates | escalation_recall: 100.0% → 100.0% (+0.00 pp; n=18→18); refusal_accuracy: 100.0% → 100.0% (+0.00 pp; n=62→62); routing_accuracy: 95.2% → 93.5% (-1.61 pp; n=62→62); citation_match: 69.6% → 76.1% (+6.52 pp; n=46→46) |
| Pipeline time / cost | p95_latency_s: 22.5500 → 12.1100 (-10.4400; n=62→62); mean_cost_inr: 0.6810 → 0.7190 (+0.0380; n=62→62); p95_cost_inr: 1.4280 → 1.5340 (+0.1060; n=62→62) |
| Paired judgments | Faithfulness: 81.8% → 90.9% (+9.09 pp; paired valid n=33); Task completion: 75.8% → 83.9% (+8.06 pp; paired valid n=62) |

Faithfulness eligible: 38 → 37; paired valid n=33; errors/nulls-as-false n=37. Conservative support: 75.7% → 86.5%. Visible full IDs: 49/52 → 52/52. Higher latency/cost deltas are regressions.
**Decision: keep.** Deterministic citation corruption and evidence pruning fixed. Full 62-case safety/refusal remain100%; visible full source markers 49/52→52/52; paired faithfulness 27/33→30/33; task fulfillment 47/62→52/62; p95 latency22.55→12.11s. Mean pipeline cost0.681→0.719INR is a measured tradeoff.
Current round's unpaired headline: faithfulness 91.4%, 35 valid / 37 eligible; task completion 83.9%, n=62. Use the paired table for the improvement claim. Abstentions: 6 → 5. Keep/revert decisions remain in the [detailed report](v3_evaluation_report.md).
Observed case regressions (previous pass → current fail): route_match: 1 ([E03](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/467aa6be-d863-4dee-92e5-1b09ca8c8824/r/4f19f4b9-ff19-4977-8d26-4e8cec9c7a7f?poll=true)); citation_match: 2 ([M04](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/467aa6be-d863-4dee-92e5-1b09ca8c8824/r/dc9df9c2-29cf-4a15-8a2f-75161a13da76?poll=true), [M12](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/467aa6be-d863-4dee-92e5-1b09ca8c8824/r/0e9dde58-c1d7-4318-99d8-56ddb5bce86f?poll=true)); faithful: 1 ([F07](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/467aa6be-d863-4dee-92e5-1b09ca8c8824/r/8495c521-5683-4a1d-bffa-5b60e6b61ec8?poll=true)); task_fulfilled: 2 ([H17](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/467aa6be-d863-4dee-92e5-1b09ca8c8824/r/64e9db42-3dd4-478d-a4b7-fe14643d0870?poll=true), [M04](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/467aa6be-d863-4dee-92e5-1b09ca8c8824/r/dc9df9c2-29cf-4a15-8a2f-75161a13da76?poll=true)).

### Incremental round1 → round2

Scope: full 62-case comparison; 62 identical case IDs.

| Metric group | Previous → current (delta; denominators) |
| --- | --- |
| Code rates | escalation_recall: 100.0% → 100.0% (+0.00 pp; n=18→18); refusal_accuracy: 100.0% → 100.0% (+0.00 pp; n=62→62); routing_accuracy: 93.5% → 95.2% (+1.61 pp; n=62→62); citation_match: 76.1% → 73.9% (-2.18 pp; n=46→46) |
| Pipeline time / cost | p95_latency_s: 12.1100 → 9.2300 (-2.8800; n=62→62); mean_cost_inr: 0.7190 → 0.5900 (-0.1290; n=62→62); p95_cost_inr: 1.5340 → 1.3430 (-0.1910; n=62→62) |
| Paired judgments | Faithfulness: 93.3% → 90.0% (-3.33 pp; paired valid n=30); Task completion: 83.9% → 77.4% (-6.45 pp; paired valid n=62) |

Faithfulness eligible: 37 → 39; paired valid n=30; errors/nulls-as-false n=37. Conservative support: 86.5% → 75.7%. Visible full IDs: 52/52 → 50/50. Higher latency/cost deltas are regressions.
**Decision: reject.** The 90-word/three-point prompt reduced latency/cost but worsened useful-answer coverage and paired faithfulness. Revert to the retainedround 1prompt beforeround 3.
Current round's unpaired headline: faithfulness 90.9%, 33 valid / 39 eligible; task completion 77.4%, n=62. Use the paired table for the improvement claim. Abstentions: 5 → 10. Keep/revert decisions remain in the [detailed report](v3_evaluation_report.md).
Observed case regressions (previous pass → current fail): citation_match: 1 ([M24](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/935ba1ed-ca65-4e76-b4dc-1a03a482c5a5/r/70c75f7c-5958-442b-9230-162d43d70554?poll=true)); faithful: 1 ([E10](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/935ba1ed-ca65-4e76-b4dc-1a03a482c5a5/r/3eb1a290-c01b-41bb-a7d8-a3fe184c5a56?poll=true)); task_fulfilled: 6 ([B09](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/935ba1ed-ca65-4e76-b4dc-1a03a482c5a5/r/66a199f7-95d9-4e38-9e4e-5a6034cd08fb?poll=true), [B11](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/935ba1ed-ca65-4e76-b4dc-1a03a482c5a5/r/6a651e63-f66d-4746-90cb-c03b9bf7f1d2?poll=true), [B13](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/935ba1ed-ca65-4e76-b4dc-1a03a482c5a5/r/966b1159-99bf-40e7-adeb-acd8af2f7232?poll=true)).

Declared restored base: **round1** plus the new lever; chronological predecessor round2 used another configuration. The latter difference is not a one-lever causal comparison.

### Incremental round1 → round3

Scope: full 62-case comparison; 62 identical case IDs.

| Metric group | Previous → current (delta; denominators) |
| --- | --- |
| Code rates | escalation_recall: 100.0% → 100.0% (+0.00 pp; n=18→18); refusal_accuracy: 100.0% → 100.0% (+0.00 pp; n=62→62); routing_accuracy: 93.5% → 93.5% (+0.00 pp; n=62→62); citation_match: 76.1% → 76.1% (+0.00 pp; n=46→46) |
| Pipeline time / cost | p95_latency_s: 12.1100 → 11.8900 (-0.2200; n=62→62); mean_cost_inr: 0.7190 → 0.7530 (+0.0340; n=62→62); p95_cost_inr: 1.5340 → 1.5740 (+0.0400; n=62→62) |
| Paired judgments | Faithfulness: 96.7% → 90.0% (-6.67 pp; paired valid n=30); Task completion: 83.9% → 75.8% (-8.06 pp; paired valid n=62) |

Faithfulness eligible: 37 → 37; paired valid n=30; errors/nulls-as-false n=36. Conservative support: 86.1% → 75.0%. Visible full IDs: 52/52 → 48/48. Higher latency/cost deltas are regressions.
**Decision: reject.** The compact verifier candidate worsened paired faithfulness, task fulfillment and abstention. Its 0.22s p95 latency improvement did not offset lower quality and higher mean cost; reject under the recorded round 3 gates and retain round 1.
Current round's unpaired headline: faithfulness 90.3%, 31 valid / 37 eligible; task completion 75.8%, n=62. Use the paired table for the improvement claim. Abstentions: 5 → 6. Keep/revert decisions remain in the [detailed report](v3_evaluation_report.md).
Observed case regressions (previous pass → current fail): route_match: 1 ([H16](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/1b51a018-3346-4d40-a602-bc91afee8530/r/774b1269-2a74-411d-adda-0d7667bc551d?poll=true)); citation_match: 1 ([M08](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/1b51a018-3346-4d40-a602-bc91afee8530/r/cbb43248-1190-47dd-a49a-60ed07b6d94b?poll=true)); faithful: 2 ([E10](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/1b51a018-3346-4d40-a602-bc91afee8530/r/0d9a506d-ad50-48cb-8304-f24cd7c99454?poll=true), [M10](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/1b51a018-3346-4d40-a602-bc91afee8530/r/46be8e51-a157-4d64-ac92-6df4c207527b?poll=true)); task_fulfilled: 6 ([B09](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/1b51a018-3346-4d40-a602-bc91afee8530/r/b37f27e8-2de2-448c-a7e7-22e41b65a75a?poll=true), [B11](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/1b51a018-3346-4d40-a602-bc91afee8530/r/0a93bc9c-0899-4aad-88d6-2b0fed8436f0?poll=true), [E10](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/1b51a018-3346-4d40-a602-bc91afee8530/r/0d9a506d-ad50-48cb-8304-f24cd7c99454?poll=true)).

Declared restored base: **round1** plus the new lever; chronological predecessor round3 used another configuration. The latter difference is not a one-lever causal comparison.

### Incremental round1 → latency1

Scope: full 62-case comparison; 62 identical case IDs.

| Metric group | Previous → current (delta; denominators) |
| --- | --- |
| Code rates | escalation_recall: 100.0% → 100.0% (+0.00 pp; n=18→18); refusal_accuracy: 100.0% → 100.0% (+0.00 pp; n=62→62); routing_accuracy: 93.5% → 93.5% (+0.00 pp; n=62→62); citation_match: 76.1% → 82.6% (+6.52 pp; n=46→46) |
| Pipeline time / cost | p95_latency_s: 12.1100 → 13.1000 (+0.9900; n=62→62); mean_cost_inr: 0.7190 → 0.7100 (-0.0090; n=62→62); p95_cost_inr: 1.5340 → 1.4640 (-0.0700; n=62→62) |
| Paired judgments | Faithfulness: 91.2% → 94.1% (+2.94 pp; paired valid n=34); Task completion: 83.9% → 88.7% (+4.84 pp; paired valid n=62) |

Faithfulness eligible: 37 → 39; paired valid n=34; errors/nulls-as-false n=37. Conservative support: 86.5% → 89.2%. Visible full IDs: 52/52 → 54/55. Higher latency/cost deltas are regressions.
**Decision: reject.** FAST direct mode passed hosted compatibility and improved quality, but full-set p95 rose12.11->13.10s, so it did not satisfy the declared latency success gate. Keep R1 selected while testing approved startup warmup.
Current round's unpaired headline: faithfulness 94.6%, 37 valid / 39 eligible; task completion 88.7%, n=62. Use the paired table for the improvement claim. Abstentions: 5 → 5. Keep/revert decisions remain in the [detailed report](v3_evaluation_report.md).
Observed case regressions (previous pass → current fail): route_match: 2 ([E07](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/724d00e2-f8f5-4660-bb73-6f1c05b222e4/r/80a494f6-114b-43df-83a3-19b339326a21?poll=true), [F06](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/724d00e2-f8f5-4660-bb73-6f1c05b222e4/r/e295c45c-18fe-4229-973a-54c5988ac2e7?poll=true)); faithful: 1 ([F01](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/724d00e2-f8f5-4660-bb73-6f1c05b222e4/r/24b98c59-e5f7-4862-8183-a896cc8fd56b?poll=true)); task_fulfilled: 1 ([M11](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/724d00e2-f8f5-4660-bb73-6f1c05b222e4/r/39c29262-b167-419e-9735-8c8676051ec7?poll=true)).

Declared restored base: **round1** plus the new lever; chronological predecessor latency1 used another configuration. The latter difference is not a one-lever causal comparison.

### Incremental round1 → latency2

Scope: full 62-case comparison; 62 identical case IDs.

| Metric group | Previous → current (delta; denominators) |
| --- | --- |
| Code rates | escalation_recall: 100.0% → 100.0% (+0.00 pp; n=18→18); refusal_accuracy: 100.0% → 100.0% (+0.00 pp; n=62→62); routing_accuracy: 93.5% → 95.2% (+1.61 pp; n=62→62); citation_match: 76.1% → 84.8% (+8.69 pp; n=46→46) |
| Pipeline time / cost | p95_latency_s: 12.1100 → 11.1900 (-0.9200; n=62→62); mean_cost_inr: 0.7190 → 0.7030 (-0.0160; n=62→62); p95_cost_inr: 1.5340 → 1.4830 (-0.0510; n=62→62) |
| Paired judgments | Faithfulness: 91.2% → 88.2% (-2.94 pp; paired valid n=34); Task completion: 83.9% → 83.9% (+0.00 pp; paired valid n=62) |

Faithfulness eligible: 37 → 39; paired valid n=34; errors/nulls-as-false n=37. Conservative support: 86.5% → 83.8%. Visible full IDs: 52/52 → 53/54. Higher latency/cost deltas are regressions.
**Decision: reject.** Warm startup plus direct FAST reduced p95 12.11->11.19s but faithfulness 33/37=89.19% fails90% and pairedR1faithfulness31/34->30/34 regresses. Keep R1; no quality tradeoff promotion.
Current round's unpaired headline: faithfulness 89.2%, 37 valid / 39 eligible; task completion 83.9%, n=62. Use the paired table for the improvement claim. Abstentions: 5 → 4. Keep/revert decisions remain in the [detailed report](v3_evaluation_report.md).
Observed case regressions (previous pass → current fail): route_match: 1 ([E07](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/85c3f52c-6416-46d2-b563-c4718ac830ce/r/c7ee8087-d7be-4e11-a8d7-ecde7faa504d?poll=true)); faithful: 2 ([E10](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/85c3f52c-6416-46d2-b563-c4718ac830ce/r/35b84812-7371-4c33-bf85-e7063d1863db?poll=true), [M09](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/85c3f52c-6416-46d2-b563-c4718ac830ce/r/edffab93-717b-4df6-88e2-ba4e60ad95fc?poll=true)); task_fulfilled: 2 ([E10](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/85c3f52c-6416-46d2-b563-c4718ac830ce/r/35b84812-7371-4c33-bf85-e7063d1863db?poll=true), [M11](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/85c3f52c-6416-46d2-b563-c4718ac830ce/r/0ffdcb27-d3ce-4b41-819e-eafa25a699fa?poll=true)).

Declared restored base: **round1** plus the new lever; chronological predecessor latency2 used another configuration. The latter difference is not a one-lever causal comparison.

### Incremental round1 → latency3

Scope: full 62-case comparison; 62 identical case IDs.

| Metric group | Previous → current (delta; denominators) |
| --- | --- |
| Code rates | escalation_recall: 100.0% → 100.0% (+0.00 pp; n=18→18); refusal_accuracy: 100.0% → 100.0% (+0.00 pp; n=62→62); routing_accuracy: 93.5% → 95.2% (+1.61 pp; n=62→62); citation_match: 76.1% → 80.4% (+4.34 pp; n=46→46) |
| Pipeline time / cost | p95_latency_s: 12.1100 → 11.2400 (-0.8700; n=62→62); mean_cost_inr: 0.7190 → 0.7370 (+0.0180; n=62→62); p95_cost_inr: 1.5340 → 1.4960 (-0.0380; n=62→62) |
| Paired judgments | Faithfulness: 90.6% → 87.5% (-3.12 pp; paired valid n=32); Task completion: 83.9% → 83.9% (+0.00 pp; paired valid n=62) |

Faithfulness eligible: 37 → 39; paired valid n=32; errors/nulls-as-false n=37. Conservative support: 86.5% → 81.1%. Visible full IDs: 52/52 → 53/53. Higher latency/cost deltas are regressions.
**Decision: reject.** Low FAST reasoning plus warmup reduced p95 12.11->11.24s but faithfulness 32/36=88.89% fails90%; pairedR1faithfulness29/32->28/32 regresses and abstentions5->6 exceed gate. R1 stays selected.
Current round's unpaired headline: faithfulness 88.9%, 36 valid / 39 eligible; task completion 83.9%, n=62. Use the paired table for the improvement claim. Abstentions: 5 → 6. Keep/revert decisions remain in the [detailed report](v3_evaluation_report.md).
Observed case regressions (previous pass → current fail): citation_match: 1 ([M05](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/e46eab2a-8338-4fc7-a3d5-7f4ec41995aa/r/9e4425d9-2eab-47b7-8b5d-3dddc2d83c06?poll=true)); faithful: 2 ([E10](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/e46eab2a-8338-4fc7-a3d5-7f4ec41995aa/r/1cf983e8-b03c-412e-938a-e596f0a0406f?poll=true), [F01](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/e46eab2a-8338-4fc7-a3d5-7f4ec41995aa/r/5aa989a4-3860-4e0c-9d48-b9c5578f434a?poll=true)); task_fulfilled: 4 ([E10](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/e46eab2a-8338-4fc7-a3d5-7f4ec41995aa/r/1cf983e8-b03c-412e-938a-e596f0a0406f?poll=true), [F06](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/e46eab2a-8338-4fc7-a3d5-7f4ec41995aa/r/75e2d7df-74bd-47b7-9f4a-72639ee77f42?poll=true), [M05](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/e46eab2a-8338-4fc7-a3d5-7f4ec41995aa/r/9e4425d9-2eab-47b7-8b5d-3dddc2d83c06?poll=true)).

### Overall baseline → round1 (selected retained candidate)

Scope: full 62-case comparison; 62 identical case IDs.

| Metric group | Previous → current (delta; denominators) |
| --- | --- |
| Code rates | escalation_recall: 100.0% → 100.0% (+0.00 pp; n=18→18); refusal_accuracy: 100.0% → 100.0% (+0.00 pp; n=62→62); routing_accuracy: 95.2% → 93.5% (-1.61 pp; n=62→62); citation_match: 69.6% → 76.1% (+6.52 pp; n=46→46) |
| Pipeline time / cost | p95_latency_s: 22.5500 → 12.1100 (-10.4400; n=62→62); mean_cost_inr: 0.6810 → 0.7190 (+0.0380; n=62→62); p95_cost_inr: 1.4280 → 1.5340 (+0.1060; n=62→62) |
| Paired judgments | Faithfulness: 81.8% → 90.9% (+9.09 pp; paired valid n=33); Task completion: 75.8% → 83.9% (+8.06 pp; paired valid n=62) |

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
