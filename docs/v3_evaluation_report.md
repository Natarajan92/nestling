# Golden v3 evaluation

The latest owner clarification identifies all 62 shortlisted questions as the owner's own: owner-attested human-authored and owner-reviewed. Authorship is not independently verified; no reason for the earlier differing interpretation is inferred. Questions, labels and frozen hash are unchanged. This stress set contains 20 happy, 26 edge, 12 known-fail and 4 adversarial cases. It is not an unseen holdout.

Freezing locks questions, context and expected labels by hash before measurement. The baseline measures the current pipeline on that fixed set. Later rounds keep reviewed labels, measurement definitions, models and judge fixed while changing a declared pipeline lever; historical v2 measurements are not reused here.

Code evaluators measure escalation recall (100%), refusal accuracy (100%), routing accuracy (at least 90%), source-ID match (reported without a pass bar), p95 latency (under 8 seconds), and mean/p95 pipeline cost (under INR 2). Latency includes the pipeline, not offline judging. Escalation recall alone does not detect false alarms.

Escalation recall is emergencies escalated divided by all cases labelled for escalation. Routing accuracy is the share sent to an allowed expected specialist; refusal accuracy checks both correct refusals and correct nonrefusals. Source-ID match accepts at least one required source or registered alias; it does not prove the answer is supported. p95 is the nearest-rank 95th percentile: approximately 95% of measured requests finish within that time. Mean cost is average pipeline token cost per case in INR; offline judge spend and unresolved reservations belong in the separate shared budget.

The runtime Verifier checks source support before an answer is returned. The separate Qwen LLM judge evaluates saved answers against saved passages afterward: faithfulness must reach 90%. Coverage/task fulfillment checks whether the request and reviewed expectations were addressed; it is supplementary and has no clinical-validation claim. Human calibration of the judge is separate from reviewing expected answers.

Faithfulness comparisons use only the same IDs with valid verdicts in both rounds. Conservative sensitivity also counts judge errors and null verdicts (including zero-claim answers) as failures on shared eligible IDs, and shows abstentions, because safe nonanswers can improve faithfulness without completing the task. Different judge denominators cannot establish a paired improvement.

B11 still requires USER-POLICY despite explicitly having no uploaded policy. This known label limitation can penalize a correct missing-policy response; labels are preserved. E09 permits either route, while its behavior asks for both topics. Context markers do not supply an uploaded policy, vaccination record or storage permission.

Latest completed: **round3** (reject). Selected retained candidate: **round1** (keep).

Shared evaluation ledger: **₹183.9041 / ₹350 accounted** across pipeline and judge requests, including any retained unknown-outcome reservations. This is measured evaluation spend, not an estimate of parent harm.

## baseline

Saved progress: 62/62 answers; 0 pending; 62 verified traces. Complete.

Safety diagnostics: 0 false escalations; 0 cases with invalid IDs; 0 with unretrieved IDs.

Observed pipeline spend / shared accounted INR: 42.2100 / 45.7285

Faithfulness: 82.9% on 35 valid judgments / 38 eligible answers. Task fulfillment: 75.8% on 62 valid judgments / 62 eligible answers.

Judge errors: 0; zero-claim answers: 3; abstentions: 6.

Visible citation IDs (**code format diagnostic**): 49/52 eligible answers contain every metadata source ID whole (94.2%). This checks formatting, not clinical truth or claim support.

| Case / trace | Missing full IDs |
| --- | --- |
| [H01](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/122b1a9c-81b7-4ee4-9408-3e1d05498c0a/r/859df4a7-0007-4cda-9573-c2bce042771f?poll=true) | ICMR-NIN-DG |
| [E09](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/122b1a9c-81b7-4ee4-9408-3e1d05498c0a/r/03179108-cddc-461e-bfc7-3ffe6e5663ff?poll=true) | ICMR-NIN-DG |
| [M05](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/122b1a9c-81b7-4ee4-9408-3e1d05498c0a/r/2ff7732a-df77-46db-a8d3-9689fa0c1b59?poll=true) | ICMR-NIN-DG |

| Metric | Value | n | Pass bar |
| --- | ---: | ---: | --- |
| escalation_recall | 100.0% | 18 | >= 1.0 |
| refusal_accuracy | 100.0% | 62 | >= 1.0 |
| routing_accuracy | 95.2% | 62 | >= 0.9 |
| citation_match | 69.6% | 46 | reported |
| p95_latency_s | 22.5500 | 62 | < 8.0 |
| mean_cost_inr | 0.6810 | 62 | < 2.0 |
| p95_cost_inr | 1.4280 | 62 | < 2.0 |

Top observed failure clusters (overlap; costs must not be added):

- task incomplete: 15 cases; observed pipeline INR 13.2397; [H07](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/122b1a9c-81b7-4ee4-9408-3e1d05498c0a/r/3cc681e6-6164-4eec-a2b3-4ca97d8669c8?poll=true), [H09](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/122b1a9c-81b7-4ee4-9408-3e1d05498c0a/r/fab7efed-c717-4c2b-9ab6-f1caf50cdf5e?poll=true), [H10](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/122b1a9c-81b7-4ee4-9408-3e1d05498c0a/r/aab75a27-e826-4e28-aea0-47e992c99906?poll=true).
- expected-source mismatch: 14 cases; observed pipeline INR 13.0142; [H07](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/122b1a9c-81b7-4ee4-9408-3e1d05498c0a/r/3cc681e6-6164-4eec-a2b3-4ca97d8669c8?poll=true), [H09](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/122b1a9c-81b7-4ee4-9408-3e1d05498c0a/r/fab7efed-c717-4c2b-9ab6-f1caf50cdf5e?poll=true), [H10](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/122b1a9c-81b7-4ee4-9408-3e1d05498c0a/r/aab75a27-e826-4e28-aea0-47e992c99906?poll=true).
- unsupported claims: 6 cases; observed pipeline INR 6.2362; [H09](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/122b1a9c-81b7-4ee4-9408-3e1d05498c0a/r/fab7efed-c717-4c2b-9ab6-f1caf50cdf5e?poll=true), [E10](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/122b1a9c-81b7-4ee4-9408-3e1d05498c0a/r/fa3a2aed-10d6-4e67-944f-57c30241db25?poll=true), [K03](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/122b1a9c-81b7-4ee4-9408-3e1d05498c0a/r/d68fa98b-78c6-46e1-a4d5-e28be2040034?poll=true).

Saved success/revert decision: pending; not inferred.

## round1

Saved progress: 62/62 answers; 0 pending; 62 verified traces. Complete.

Safety diagnostics: 0 false escalations; 0 cases with invalid IDs; 0 with unretrieved IDs.

Observed pipeline spend / shared accounted INR: 44.5900 / 93.8810

Faithfulness: 91.4% on 35 valid judgments / 37 eligible answers. Task fulfillment: 83.9% on 62 valid judgments / 62 eligible answers.

Judge errors: 0; zero-claim answers: 2; abstentions: 5.

Visible citation IDs (**code format diagnostic**): 52/52 eligible answers contain every metadata source ID whole (100.0%). This checks formatting, not clinical truth or claim support.

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

Scope: **full 62-case comparison**, 62 matched cases. Subsets are diagnostic, not full-set headlines.

| Metric | Baseline on same IDs | Candidate | Delta | Pass bar |
| --- | ---: | ---: | ---: | --- |
| escalation_recall | 100.0% | 100.0% | +0.00 pp | >= 1.0 |
| refusal_accuracy | 100.0% | 100.0% | +0.00 pp | >= 1.0 |
| routing_accuracy | 95.2% | 93.5% | -1.61 pp | >= 0.9 |
| citation_match | 69.6% | 76.1% | +6.52 pp | reported |
| p95_latency_s | 22.5500 | 12.1100 | -10.4400 | < 8.0 |
| mean_cost_inr | 0.6810 | 0.7190 | +0.0380 | < 2.0 |
| p95_cost_inr | 1.4280 | 1.5340 | +0.1060 | < 2.0 |

| Paired quality / diagnostic | Baseline | Candidate | Delta | n |
| --- | ---: | ---: | ---: | ---: |
| Faithfulness (valid both) | 81.8% | 90.9% | +9.09 pp | 33 |
| Faithfulness (errors/nulls as false) | 75.7% | 86.5% | +10.81 pp | 37 |
| Task fulfillment (valid both) | 75.8% | 83.9% | +8.06 pp | 62 |

Same-ID visible full citations: 49/52 baseline → 52/52 candidate; eligible denominators are explicit because metadata citation sets can change. Abstentions: 6 → 5; judge errors: 0 → 0.

Recorded pipeline provenance changes (full values remain in checkpoints):

- `files.nestling/agents/__init__.py`: 328ab602b286 → 5fe4ce85039f.

Observed case regressions, route_match: [E03](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/467aa6be-d863-4dee-92e5-1b09ca8c8824/r/4f19f4b9-ff19-4977-8d26-4e8cec9c7a7f?poll=true).

Observed case regressions, citation_match: [M04](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/467aa6be-d863-4dee-92e5-1b09ca8c8824/r/dc9df9c2-29cf-4a15-8a2f-75161a13da76?poll=true), [M12](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/467aa6be-d863-4dee-92e5-1b09ca8c8824/r/0e9dde58-c1d7-4318-99d8-56ddb5bce86f?poll=true).

Observed case regressions, faithful: [F07](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/467aa6be-d863-4dee-92e5-1b09ca8c8824/r/8495c521-5683-4a1d-bffa-5b60e6b61ec8?poll=true).

Observed case regressions, task_fulfilled: [H17](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/467aa6be-d863-4dee-92e5-1b09ca8c8824/r/64e9db42-3dd4-478d-a4b7-fe14643d0870?poll=true), [M04](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/467aa6be-d863-4dee-92e5-1b09ca8c8824/r/dc9df9c2-29cf-4a15-8a2f-75161a13da76?poll=true).

Top observed failure clusters (overlap; costs must not be added):

- expected-source mismatch: 11 cases; observed pipeline INR 10.4404; [E06](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/467aa6be-d863-4dee-92e5-1b09ca8c8824/r/d67c34e3-cecb-4cec-8f91-321679f0473e?poll=true), [M02](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/467aa6be-d863-4dee-92e5-1b09ca8c8824/r/4116ca57-a199-439c-8cf3-055bbffb0d3a?poll=true), [M03](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/467aa6be-d863-4dee-92e5-1b09ca8c8824/r/f390508a-1f48-4fd4-a741-dbdb28513bc3?poll=true).
- task incomplete: 10 cases; observed pipeline INR 7.6828; [H17](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/467aa6be-d863-4dee-92e5-1b09ca8c8824/r/64e9db42-3dd4-478d-a4b7-fe14643d0870?poll=true), [E03](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/467aa6be-d863-4dee-92e5-1b09ca8c8824/r/4f19f4b9-ff19-4977-8d26-4e8cec9c7a7f?poll=true), [E06](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/467aa6be-d863-4dee-92e5-1b09ca8c8824/r/d67c34e3-cecb-4cec-8f91-321679f0473e?poll=true).
- routing: 4 cases; observed pipeline INR 2.6920; [E03](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/467aa6be-d863-4dee-92e5-1b09ca8c8824/r/4f19f4b9-ff19-4977-8d26-4e8cec9c7a7f?poll=true), [M02](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/467aa6be-d863-4dee-92e5-1b09ca8c8824/r/4116ca57-a199-439c-8cf3-055bbffb0d3a?poll=true), [M03](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/467aa6be-d863-4dee-92e5-1b09ca8c8824/r/f390508a-1f48-4fd4-a741-dbdb28513bc3?poll=true).

Pre-call iteration intent:

- **Recorded at:** 2026-11-01T18:48:41.833688+00:00
- **Hypothesis:** Prevent matching a source-ID suffix inside an already valid citation, preserving multi-hyphen source markers and evidence selection before verification. This should reduce false abstentions without changing models or trusted sources.
- **Target cluster:** Observed H01 visible ICMR citation corruption; deterministic mixed-source evidence pruning; H07 false abstention is a candidate mechanism, not yet proven.
- **Lever:** One regex boundary in nestling/agents/__init__.py::_BARE; no prompt, model, retrieval, judge or safety-rule changes.
- **Expected metric direction:** Broken visible source markers fall to zero; substantive task fulfillment improves and abstention falls; paired faithfulness does not fall; latency/cost stay stable or improve.
- **Success criterion:** Full 62-case complete; deterministic citation/evidence-preservation regressions pass; escalation/refusal100%, routing>=90%; no invalid/unretrieved citations; compare same-ID valid judges and task fulfillment, alongside display-citation diagnostic.
- **Revert criterion:** Revert on a safety/refusal regression, invalid/unretrieved citations, or worsened paired source support/task fulfillment without a defensible tradeoff. Do not waive90% faithfulness or8s latency targets.

Saved success/revert decision:

- **Decision:** keep
- **Reason:** Deterministic citation corruption and evidence pruning fixed. Full 62-case safety/refusal remain100%; visible full source markers 49/52→52/52; paired faithfulness 27/33→30/33; task fulfillment 47/62→52/62; p95 latency22.55→12.11s. Mean pipeline cost0.681→0.719INR is a measured tradeoff.
- **Remaining failed bar:** p95 latency12.11s still exceeds8s; target not waived.
- **Paired faithfulness:** {'paired_valid_n': 33, 'baseline': 0.8181818181818182, 'candidate': 0.9090909090909091, 'delta_pp': 9.090909090909083, 'error_sensitivity_n': 37, 'baseline_errors_as_false': 0.7567567567567568, 'candidate_errors_as_false': 0.8648648648648649, 'baseline_eligible_n': 38, 'candidate_eligible_n': 37, 'baseline_abstained': 6, 'candidate_abstained': 5}
- **Not attributed:** Routing changed59/62→58/62 although the routing code/prompt was unchanged; do not attribute that variation to the regex fix.
- **Trace repair:** M09 reused successful pipeline/judge outputs for cached trace verification, with no repeated inference.

## round2

Saved progress: 62/62 answers; 0 pending; 62 verified traces. Complete.

Safety diagnostics: 0 false escalations; 0 cases with invalid IDs; 0 with unretrieved IDs.

Observed pipeline spend / shared accounted INR: 36.5500 / 133.8522

Faithfulness: 90.9% on 33 valid judgments / 39 eligible answers. Task fulfillment: 77.4% on 62 valid judgments / 62 eligible answers.

Judge errors: 0; zero-claim answers: 6; abstentions: 10.

Visible citation IDs (**code format diagnostic**): 50/50 eligible answers contain every metadata source ID whole (100.0%). This checks formatting, not clinical truth or claim support.

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

Scope: **full 62-case comparison**, 62 matched cases. Subsets are diagnostic, not full-set headlines.

| Metric | Baseline on same IDs | Candidate | Delta | Pass bar |
| --- | ---: | ---: | ---: | --- |
| escalation_recall | 100.0% | 100.0% | +0.00 pp | >= 1.0 |
| refusal_accuracy | 100.0% | 100.0% | +0.00 pp | >= 1.0 |
| routing_accuracy | 95.2% | 95.2% | +0.00 pp | >= 0.9 |
| citation_match | 69.6% | 73.9% | +4.34 pp | reported |
| p95_latency_s | 22.5500 | 9.2300 | -13.3200 | < 8.0 |
| mean_cost_inr | 0.6810 | 0.5900 | -0.0910 | < 2.0 |
| p95_cost_inr | 1.4280 | 1.3430 | -0.0850 | < 2.0 |

| Paired quality / diagnostic | Baseline | Candidate | Delta | n |
| --- | ---: | ---: | ---: | ---: |
| Faithfulness (valid both) | 80.0% | 90.0% | +10.00 pp | 30 |
| Faithfulness (errors/nulls as false) | 76.3% | 76.3% | +0.00 pp | 38 |
| Task fulfillment (valid both) | 75.8% | 77.4% | +1.61 pp | 62 |

Same-ID visible full citations: 49/52 baseline → 50/50 candidate; eligible denominators are explicit because metadata citation sets can change. Abstentions: 6 → 10; judge errors: 0 → 0.

Recorded pipeline provenance changes (full values remain in checkpoints):

- `prompt_version`: app-v7-vector-safe-lessons-v2-prenatal → app-v3-source-focused-v1.
- `files.nestling/agents/__init__.py`: 328ab602b286 → aa7e1fe6dfd8.
- `files.nestling/graph.py`: 94eb305149e7 → 45290c9f6488.

Observed case regressions, citation_match: [M04](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/935ba1ed-ca65-4e76-b4dc-1a03a482c5a5/r/a58fc4c6-bd0c-444d-bcfb-c1e4a32b12e5?poll=true), [M12](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/935ba1ed-ca65-4e76-b4dc-1a03a482c5a5/r/3047ee46-4e87-4b4f-856e-e7c7f2ac8eb7?poll=true), [M24](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/935ba1ed-ca65-4e76-b4dc-1a03a482c5a5/r/70c75f7c-5958-442b-9230-162d43d70554?poll=true).

Observed case regressions, task_fulfilled: [B09](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/935ba1ed-ca65-4e76-b4dc-1a03a482c5a5/r/66a199f7-95d9-4e38-9e4e-5a6034cd08fb?poll=true), [B11](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/935ba1ed-ca65-4e76-b4dc-1a03a482c5a5/r/6a651e63-f66d-4746-90cb-c03b9bf7f1d2?poll=true), [B13](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/935ba1ed-ca65-4e76-b4dc-1a03a482c5a5/r/966b1159-99bf-40e7-adeb-acd8af2f7232?poll=true), [M10](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/935ba1ed-ca65-4e76-b4dc-1a03a482c5a5/r/7cd03382-496d-446e-9f04-aa55a5f006af?poll=true), [M12](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/935ba1ed-ca65-4e76-b4dc-1a03a482c5a5/r/3047ee46-4e87-4b4f-856e-e7c7f2ac8eb7?poll=true).

Top observed failure clusters (overlap; costs must not be added):

- task incomplete: 14 cases; observed pipeline INR 10.7720; [E03](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/935ba1ed-ca65-4e76-b4dc-1a03a482c5a5/r/ede14245-4e65-4e5e-b96b-b25614916ec4?poll=true), [E06](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/935ba1ed-ca65-4e76-b4dc-1a03a482c5a5/r/3d8aac78-98ba-42b7-9b24-1b3b14411463?poll=true), [E09](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/935ba1ed-ca65-4e76-b4dc-1a03a482c5a5/r/1eee1a94-fa99-4d4a-9016-449bb8c4b982?poll=true).
- expected-source mismatch: 12 cases; observed pipeline INR 9.3336; [E06](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/935ba1ed-ca65-4e76-b4dc-1a03a482c5a5/r/3d8aac78-98ba-42b7-9b24-1b3b14411463?poll=true), [M02](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/935ba1ed-ca65-4e76-b4dc-1a03a482c5a5/r/8bb90640-3bb3-40e3-a7ca-1b6f02701f94?poll=true), [M03](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/935ba1ed-ca65-4e76-b4dc-1a03a482c5a5/r/2d13c520-b953-4179-802c-a88109d70694?poll=true).
- unsupported claims: 3 cases; observed pipeline INR 2.8149; [E10](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/935ba1ed-ca65-4e76-b4dc-1a03a482c5a5/r/3eb1a290-c01b-41bb-a7d8-a3fe184c5a56?poll=true), [M03](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/935ba1ed-ca65-4e76-b4dc-1a03a482c5a5/r/2d13c520-b953-4179-802c-a88109d70694?poll=true), [M06](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/935ba1ed-ca65-4e76-b4dc-1a03a482c5a5/r/baf042a3-435c-4ac4-b534-4a79fb773c20?poll=true).

Pre-call iteration intent:

- **Recorded at:** 2026-11-01T19:11:46.167150+00:00
- **Hypothesis:** The specialist over-generates tangential timelines, food quantities and background claims. A source-focused90-word/three-point answer budget should reduce unsupported material and verifier work while preserving required answers.
- **Target cluster:** Remaining 12.11s p95 latency; ten task-incomplete answers and unnecessary factual claims after citation repair.
- **Lever:** Specialist BASE_PROMPT only: exact-question focus, at most90 words and three concise points; omit unsolicited background. Bump app prompt tag only to identify this change.
- **Expected metric direction:** Lower pipelinep95 and mean/p95cost; source faithfulness and task fulfillment stable or higher; no increase in abstention or safety/refusal errors.
- **Success criterion:** Full 62-case complete, safety/refusal 100%, routing>=90%, visible citation integrity100%, paired faithfulness/task fulfillment no worse than R1 while p95 latency or cost improves; still test90% faithfulness/8s latency bars.
- **Revert criterion:** Revert or revise if brevity removes required content, materially worsens paired task fulfillment/source support, increases abstention without a defensible source gap, or breaks safety/citation checks.

Saved success/revert decision:

- **Decision:** reject
- **Reason:** The 90-word/three-point prompt reduced latency/cost but worsened useful-answer coverage and paired faithfulness. Revert to the retainedround 1prompt beforeround 3.
- **Observed vs round1:** {'task_fulfilled': '52/62→48/62', 'abstained': '5→10', 'paired_faithful': '28/30→27/30', 'p95_latency_s': '12.11→9.23', 'mean_cost_inr': '0.719→0.590'}
- **Selected base for next round:** round1
- **Note:** All 62R2 outputs and raw judge results remain preserved; no metric or label was changed.

## round3

Saved progress: 62/62 answers; 0 pending; 62 verified traces. Complete.

Safety diagnostics: 0 false escalations; 0 cases with invalid IDs; 0 with unretrieved IDs.

Observed pipeline spend / shared accounted INR: 46.6800 / 183.9041

Faithfulness: 90.3% on 31 valid judgments / 37 eligible answers. Task fulfillment: 75.8% on 62 valid judgments / 62 eligible answers.

Judge errors: 0; zero-claim answers: 6; abstentions: 6.

Visible citation IDs (**code format diagnostic**): 48/48 eligible answers contain every metadata source ID whole (100.0%). This checks formatting, not clinical truth or claim support.

Declared restored base: **round1** plus the new lever. Chronological predecessor round2 used another configuration; its difference is not presented as a one-lever causal comparison.

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

Scope: **full 62-case comparison**, 62 matched cases. Subsets are diagnostic, not full-set headlines.

| Metric | Baseline on same IDs | Candidate | Delta | Pass bar |
| --- | ---: | ---: | ---: | --- |
| escalation_recall | 100.0% | 100.0% | +0.00 pp | >= 1.0 |
| refusal_accuracy | 100.0% | 100.0% | +0.00 pp | >= 1.0 |
| routing_accuracy | 95.2% | 93.5% | -1.61 pp | >= 0.9 |
| citation_match | 69.6% | 76.1% | +6.52 pp | reported |
| p95_latency_s | 22.5500 | 11.8900 | -10.6600 | < 8.0 |
| mean_cost_inr | 0.6810 | 0.7530 | +0.0720 | < 2.0 |
| p95_cost_inr | 1.4280 | 1.5740 | +0.1460 | < 2.0 |

| Paired quality / diagnostic | Baseline | Candidate | Delta | n |
| --- | ---: | ---: | ---: | ---: |
| Faithfulness (valid both) | 86.2% | 89.7% | +3.45 pp | 29 |
| Faithfulness (errors/nulls as false) | 75.7% | 75.7% | +0.00 pp | 37 |
| Task fulfillment (valid both) | 75.8% | 75.8% | +0.00 pp | 62 |

Same-ID visible full citations: 49/52 baseline → 48/48 candidate; eligible denominators are explicit because metadata citation sets can change. Abstentions: 6 → 6; judge errors: 0 → 0.

Recorded pipeline provenance changes (full values remain in checkpoints):

- `flags`: {'concierge': True, 'retrieval': 'staged_vector', 'verifier': True, 'strict_verifier': True, 'lessons': True} → {'concierge': True, 'retrieval': 'staged_vector', 'verifier': True, 'strict_verifier': True, 'lessons': True, 'compact_verifier': True}.
- `prompt_version`: app-v7-vector-safe-lessons-v2-prenatal → app-v3-compact-verifier-v1.
- `files.nestling/agents/__init__.py`: 328ab602b286 → 5fe4ce85039f.
- `files.nestling/graph.py`: 94eb305149e7 → 30a15d8e441f.
- `files.nestling/verifier.py`: 59e77a4d427e → 8e5b3953b760.

Observed case regressions, route_match: [H16](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/1b51a018-3346-4d40-a602-bc91afee8530/r/774b1269-2a74-411d-adda-0d7667bc551d?poll=true).

Observed case regressions, citation_match: [M04](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/1b51a018-3346-4d40-a602-bc91afee8530/r/bd4d6bdb-db41-4bc4-867b-d3d989203aa5?poll=true), [M08](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/1b51a018-3346-4d40-a602-bc91afee8530/r/cbb43248-1190-47dd-a49a-60ed07b6d94b?poll=true).

Observed case regressions, faithful: [F07](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/1b51a018-3346-4d40-a602-bc91afee8530/r/653b36dc-fb00-4aa5-b524-c7bd1f7bc3ab?poll=true), [M10](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/1b51a018-3346-4d40-a602-bc91afee8530/r/46be8e51-a157-4d64-ac92-6df4c207527b?poll=true).

Observed case regressions, task_fulfilled: [B09](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/1b51a018-3346-4d40-a602-bc91afee8530/r/b37f27e8-2de2-448c-a7e7-22e41b65a75a?poll=true), [B11](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/1b51a018-3346-4d40-a602-bc91afee8530/r/0a93bc9c-0899-4aad-88d6-2b0fed8436f0?poll=true), [H16](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/1b51a018-3346-4d40-a602-bc91afee8530/r/774b1269-2a74-411d-adda-0d7667bc551d?poll=true), [H17](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/1b51a018-3346-4d40-a602-bc91afee8530/r/712a9d7c-12bd-4eb9-9851-95ec461fa440?poll=true), [M03](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/1b51a018-3346-4d40-a602-bc91afee8530/r/f6be5364-fa8b-4a6c-9d99-69051d12a4c5?poll=true), [M04](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/1b51a018-3346-4d40-a602-bc91afee8530/r/bd4d6bdb-db41-4bc4-867b-d3d989203aa5?poll=true), [M08](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/1b51a018-3346-4d40-a602-bc91afee8530/r/cbb43248-1190-47dd-a49a-60ed07b6d94b?poll=true).

Top observed failure clusters (overlap; costs must not be added):

- task incomplete: 15 cases; observed pipeline INR 13.2237; [H16](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/1b51a018-3346-4d40-a602-bc91afee8530/r/774b1269-2a74-411d-adda-0d7667bc551d?poll=true), [H17](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/1b51a018-3346-4d40-a602-bc91afee8530/r/712a9d7c-12bd-4eb9-9851-95ec461fa440?poll=true), [E03](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/1b51a018-3346-4d40-a602-bc91afee8530/r/38a49ff9-d54f-42c3-9139-685e0a372794?poll=true).
- expected-source mismatch: 11 cases; observed pipeline INR 11.4656; [E06](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/1b51a018-3346-4d40-a602-bc91afee8530/r/e9333f06-870e-4461-b7e7-b7e9088c5a6a?poll=true), [M02](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/1b51a018-3346-4d40-a602-bc91afee8530/r/f23f7b2b-ade0-409b-842b-8bbae53b7e65?poll=true), [M03](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/1b51a018-3346-4d40-a602-bc91afee8530/r/f6be5364-fa8b-4a6c-9d99-69051d12a4c5?poll=true).
- routing: 4 cases; observed pipeline INR 3.0400; [H16](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/1b51a018-3346-4d40-a602-bc91afee8530/r/774b1269-2a74-411d-adda-0d7667bc551d?poll=true), [M02](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/1b51a018-3346-4d40-a602-bc91afee8530/r/f23f7b2b-ade0-409b-842b-8bbae53b7e65?poll=true), [M03](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/1b51a018-3346-4d40-a602-bc91afee8530/r/f6be5364-fa8b-4a6c-9d99-69051d12a4c5?poll=true).

Pre-call iteration intent:

- **Recorded at:** 2026-11-01T19:26:47.588584+00:00
- **Hypothesis:** Repeating every supported claim in verifier output adds tokens and latency. Return only the total checked count and unsupported claims while preserving the same MAIN model, full strict scope and repair path.
- **Target cluster:** Remaining 12.11s retained R1p95 and checker output repetition: five slowestR1 checks repeated41claims,34supported,using1466outputtokens; other provider/retrieval tails remain.
- **Lever:** Compact verifier response representation plus app activation/trace tag; generation prompt restored exactly to retained R1. No model, judge, source, safety-rule or rewrite-policy change.
- **Expected metric direction:** Lower checker/pipeline latency and mean token cost; paired faithfulness and task fulfillment stable or higher; no increase in abstention or safety errors. This does not guarantee the8s target because retrieval/classifier tails remain.
- **Success criterion:** Full 62-case complete; same-frame comparison versusR1; safety/refusal 100%, routing>=90%, validvisiblecitations100%; source faithfulness/task completion not worse without defensible tradeoff; latency/cost improve. Validatepositivecounts and failclosed malformed/zero responses.
- **Revert criterion:** Reject compact activation if reduced output hides unsupported claims, worsens paired quality/coverage, increases abstention or breaks any safety/citation gate. Do not waive8s or90% bars; preserve raw rejected measurements.
- **Comparison base:** round1

Saved success/revert decision:

- **Decision:** reject
- **Comparison base:** round1
- **Reason:** The compact verifier candidate worsened paired faithfulness, task fulfillment and abstention. Its 0.22s p95 latency improvement did not offset lower quality and higher mean cost; reject under the recorded round 3 gates and retain round 1.
- **Observed vs round1:** {'task_fulfilled': '52/62 -> 47/62', 'abstained': '5 -> 6', 'paired_faithful': '29/30 -> 27/30', 'p95_latency_s': '12.11 -> 11.89', 'mean_cost_inr': '0.719 -> 0.753'}
- **Paired faithfulness:** {'paired_valid_n': 30, 'baseline': 0.9666666666666667, 'candidate': 0.9, 'delta_pp': -6.666666666666665, 'error_sensitivity_n': 36, 'baseline_errors_as_false': 0.8611111111111112, 'candidate_errors_as_false': 0.75, 'baseline_eligible_n': 37, 'candidate_eligible_n': 37, 'baseline_abstained': 5, 'candidate_abstained': 6}
- **Full 62-case complete:** True
- **Pipeline errors:** 0
- **Judge errors:** 0
- **Retained runtime:** round1
- **Remaining failed bar:** Retained round 1 p95 latency 12.11s still exceeds the 8s target; the target is not waived.
- **Runtime generation sha256:** 5fe4ce85039fa110bbc3d5fea9e505adb30ca8894a36e7be8b5f09bb12fd3bc5
- **Note:** All 62 round 3 outputs, judgments, traces and measured source hashes remain preserved. Disable compact activation while keeping candidate implementation and regression tests.

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

## Submission40 presentation view

This 40-case view meets the handout's 30–50-case presentation range and 20 happy / 12 edge / 6 known-fail / 2 adversarial mix. Selection takes lexicographically first IDs within each stratum, without using scores. **All 62 cases and failures remain the primary regression/promotion gates.**

Presentation subset defined after full baseline and before first improvement measurement; not a preregistered independent benchmark.

Exports: `evals/results/golden_v3/submission40_questions.csv`; each measured round has `submission40_results.csv` and `submission40_summary.json`. These copy existing frozen questions and saved answers; no second active dataset or new inference is created.

### baseline · same selected 40 IDs

Faithfulness: 90.9% on 22/25 eligible valid judgments; task fulfillment 72.5% on 40 judgments. Judge errors 0; abstentions 3.

| Metric | This view | n | Delta vs baseline on same 40 |
| --- | ---: | ---: | ---: |
| escalation_recall | 100.0% | 10 | baseline |
| refusal_accuracy | 100.0% | 40 | baseline |
| routing_accuracy | 95.0% | 40 | baseline |
| citation_match | 67.7% | 31 | baseline |
| p95_latency_s | 23.5600 | 40 | baseline |
| mean_cost_inr | 0.7070 | 40 | baseline |
| p95_cost_inr | 1.3810 | 40 | baseline |

### round1 · same selected 40 IDs

Faithfulness: 95.7% on 23/24 eligible valid judgments; task fulfillment 85.0% on 40 judgments. Judge errors 0; abstentions 1.

| Metric | This view | n | Delta vs baseline on same 40 |
| --- | ---: | ---: | ---: |
| escalation_recall | 100.0% | 10 | +0.00 pp |
| refusal_accuracy | 100.0% | 40 | +0.00 pp |
| routing_accuracy | 92.5% | 40 | -2.50 pp |
| citation_match | 83.9% | 31 | +16.13 pp |
| p95_latency_s | 12.1100 | 40 | -11.4500 |
| mean_cost_inr | 0.7530 | 40 | +0.0460 |
| p95_cost_inr | 1.5340 | 40 | +0.1530 |

Paired valid faithfulness: 90.5% → 95.2%, +4.76 pp, n=21. Errors/nulls-as-false sensitivity: 79.2% → 91.7%, n=24.

### round2 · same selected 40 IDs

Faithfulness: 100.0% on 23/26 eligible valid judgments; task fulfillment 82.5% on 40 judgments. Judge errors 0; abstentions 3.

| Metric | This view | n | Delta vs baseline on same 40 |
| --- | ---: | ---: | ---: |
| escalation_recall | 100.0% | 10 | +0.00 pp |
| refusal_accuracy | 100.0% | 40 | +0.00 pp |
| routing_accuracy | 95.0% | 40 | +0.00 pp |
| citation_match | 83.9% | 31 | +16.13 pp |
| p95_latency_s | 10.0000 | 40 | -13.5600 |
| mean_cost_inr | 0.6360 | 40 | -0.0710 |
| p95_cost_inr | 1.3460 | 40 | -0.0350 |

Paired valid faithfulness: 90.0% → 100.0%, +10.00 pp, n=20. Errors/nulls-as-false sensitivity: 80.0% → 88.0%, n=25.

### round3 · same selected 40 IDs

Faithfulness: 95.5% on 22/24 eligible valid judgments; task fulfillment 80.0% on 40 judgments. Judge errors 0; abstentions 2.

| Metric | This view | n | Delta vs baseline on same 40 |
| --- | ---: | ---: | ---: |
| escalation_recall | 100.0% | 10 | +0.00 pp |
| refusal_accuracy | 100.0% | 40 | +0.00 pp |
| routing_accuracy | 92.5% | 40 | -2.50 pp |
| citation_match | 80.7% | 31 | +12.91 pp |
| p95_latency_s | 11.8900 | 40 | -11.6700 |
| mean_cost_inr | 0.7920 | 40 | +0.0850 |
| p95_cost_inr | 1.5740 | 40 | +0.1930 |

Paired valid faithfulness: 90.0% → 95.0%, +5.00 pp, n=20. Errors/nulls-as-false sensitivity: 79.2% → 87.5%, n=24.

## Iteration discipline

Before calls, use propose_round() to save a hypothesis, observed target cluster, one lever, expected metric direction, and success/revert criteria. Preserve each round. A subset screens the lever; a complete 62-case run is needed for a full headline. Save the actual decision and reason in decision.json after reviewing results. Changing multiple levers or the judge prevents a simple causal attribution. Repeated tuning on this known set can overfit; gains require a separately authored future holdout for a generalization claim.
