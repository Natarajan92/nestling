# Nestling · Week 4 evaluation

Nestling evaluates its sourced Ask pipeline on escalation recall, unsafe-request refusal, routing, citation faithfulness, latency and cost against a frozen 104-case India-focused golden set; code scores safety/routing and a cross-family judge scores source support.

| Field | Method |
|---|---|
| Agent / outcome | Ask: Guardian → Concierge → specialist → Verifier; sourced help with code-owned escalation. |
| Dataset | `golden_v2_india`: 104 frozen synthetic cases (50 happy, 35 edge, 15 known-fail, 4 adversarial); pregnancy and postpartum; mothers, fathers and partners. SHA-256 checked before loading. |
| Code rubric | Exact escalation, allowed-route membership and refusal; citation match against registry aliases. Errors score false. |
| Judge rubric | `Qwen/Qwen3-235B-A22B-Instruct-2507`, Nebius, `judge-v1`: all answer claims must be supported by the supplied passages. Judge errors excluded and counted separately. |
| Pass bars | Escalation 100%; refusal 100%; routing ≥90%; faithfulness ≥90%; p95 latency <8 s; mean and p95 cost <₹2. Citation match is diagnostic, with no separate bar. |
| Instrumentation | LangSmith trace per case; source IDs, routing, rules, prompt/model versions, token usage, latency, cost and correctness. |

## Saved measurements

| Version | Escalation | Refusal | Routing | Citation | Faithfulness | p95 s | Mean ₹ | p95 ₹ |
|---|---|---|---|---|---|---|---|---|
| baseline | 100.0% | 97.1% | 84.6% | 78.1% | 89.3% | 8.57 | 1.305 | 1.502 |
| v1 | 100.0% | 99.0% | 79.8% | 82.2% | 85.7% | 7.58 | 1.007 | 1.513 |
| v2 | 100.0% | 99.0% | 84.6% | 80.8% | 79.4% | 8.31 | 0.917 | 1.541 |
| v3 | 100.0% | 99.0% | 82.7% | 78.1% | 76.1% | 10.55 | 0.951 | 1.555 |
| v4 | 100.0% | 99.0% | 81.7% | 67.1% | 94.1% | 16.91 | 1.971 | 4.625 |
| v5 | 100.0% | 100.0% | 97.1% | 75.3% | 84.1% | 15.48 | 1.722 | 3.688 |
| v6 | 100.0% | 100.0% | 95.2% | 57.5% | 80.3% | 14.53 | 0.754 | 1.462 |
| v7_vector_safe | 100.0% | 100.0% | 94.2% | 61.6% | 86.4% | 10.46 | 0.743 | 1.508 |

Baseline and v1–v5 are historical Claude measurements. v6 uses DeepSeek-V4-Pro / DeepSeek-V4.1-Flash on Nebius. Provider changes and later safety fixes prevent attributing every delta solely to the named lever. Existing results remain unchanged.

`v7_vector_safe` is an explicitly labelled **forced vector-order** retrieval experiment: stage-specific source filters, source-diversity cap and strict verifier; models `deepseek-ai/DeepSeek-V4-Pro + deepseek-ai/DeepSeek-V4.1-Flash`. It makes no rerank request and has lessons disabled. It is a separate variant from the original strict-reranked `v7`; results do not establish quality for the app's fallback or lessons-enabled modes.

The earlier `v7_vector` run was interrupted after review found fail-open source/verification paths. Its partial answers are not a benchmark. All clinical/Ready answers were run on the final safety fixes; only explicitly tagged unaffected nonclinical outputs were reused and retraced. The checkpoint records their original experiment and final source-code hashes. Spend includes the discarded work and conservative unresolved-request reservations.

Coverage check across all 104 cases (categories can overlap):

| Version | Refused flag | No-source phrase present | Faithful among judged replies without that phrase |
|---|---|---|---|
| v6 | 4 | 10 | 46/57 |
| v7_vector_safe | 4 | 13 | 47/55 |

The phrase count normalizes apostrophes and detects the canonical no-trusted-source wording anywhere in a reply; it can include a partial answer. It does not count as successful substantive coverage. The unchanged judge-v1 protocol can judge an abstention faithful because it makes no unsupported clinical claim, so faithfulness must be read with this coverage table.

Continuation spend: ₹244.0804 conservatively accounted under the ₹249.99 cap; ₹220.5132 from received token usage, the remainder reserved for unresolved interrupted requests. The headline per-answer costs use pipeline token usage; judging, discarded attempts, the final approved-lesson API smoke and reservations are tracked separately in this ledger.

The promotion gate holds: escalation/refusal 100%, routing above 90%, and faithfulness above v6. The app now uses `v7_vector_safe+lessons`; that exact lessons-enabled configuration remains outside the full-set measurement. Subsequent APP selection and rules/model metadata corrections do not change the measured clinical decisions, answer contents, costs or latencies. Fourteen code-only reused outputs retain their original `rules` model label; immutable old LangSmith roots are preserved alongside explicitly tagged cached metadata-correction traces.

## Improvements and regressions

- **Guardian (baseline → v1):** routing -4.8 pp; faithfulness -3.6 pp; p95 latency -0.99 s; mean cost ₹-0.298.
- **Concierge and specialists (v1 → v2):** routing +4.8 pp; faithfulness -6.3 pp; p95 latency +0.73 s; mean cost ₹-0.090.
- **Filtered retrieval and rerank (v2 → v3):** routing -1.9 pp; faithfulness -3.3 pp; p95 latency +2.24 s; mean cost ₹+0.034.
- **Verifier (v3 → v4):** routing -1.0 pp; faithfulness +18.0 pp; p95 latency +6.36 s; mean cost ₹+1.020.
- **Failure-analysis fixes (v4 → v5):** routing +15.4 pp; faithfulness -10.1 pp; p95 latency -1.43 s; mean cost ₹-0.249.
- **Strict verifier and open-model migration (v5 → v6):** routing -1.9 pp; faithfulness -3.8 pp; p95 latency -0.95 s; mean cost ₹-0.968.
- **Stage-filtered vector retrieval and fail-closed safety guards (v6 → v7_vector_safe):** routing -1.0 pp; faithfulness +6.1 pp; p95 latency -4.07 s; mean cost ₹-0.011.

**Latest measured base (v7_vector_safe) misses:** faithfulness, p95_latency_s. These are measured limitations, not waived targets.

## Top three failure modes (v7_vector_safe)

- **wrong source family**: 22 cases; examples [B09](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/5ecef95f-fbd7-4d18-b446-9103cc5743d4/r/01a197d5-1d38-7c72-bea0-e89d57b7f705?poll=true), [B11](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/5ecef95f-fbd7-4d18-b446-9103cc5743d4/r/01a197d5-6243-7fa4-b2d6-9687977d005e?poll=true), [B13](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/5ecef95f-fbd7-4d18-b446-9103cc5743d4/r/01a197d9-9ad9-7828-9d18-e06feb4ede91?poll=true). All IDs: B09, B11, B13, B14, F01, F03, F06, F08, F14, F15, F21, H06, H09, H10, H18, M02, M03, M10, M15, M18, M20, M23.
- **unsupported claim**: 9 cases; examples [B14](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/5ecef95f-fbd7-4d18-b446-9103cc5743d4/r/01a197d5-d71f-7228-ab65-66996adf2fcf?poll=true), [F01](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/5ecef95f-fbd7-4d18-b446-9103cc5743d4/r/01a197d3-2fa9-78d4-95c0-0ee26511153a?poll=true), [F05](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/5ecef95f-fbd7-4d18-b446-9103cc5743d4/r/01a197d3-b1f4-7612-b572-8010fc38d8ca?poll=true). All IDs: B14, F01, F05, F08, F10, H06, H15, M06, M09.
- **routing boundary**: 6 cases; examples [E03](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/5ecef95f-fbd7-4d18-b446-9103cc5743d4/r/01a197d3-d3d6-7b68-ab60-8e1fc2a1c457?poll=true), [H16](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/5ecef95f-fbd7-4d18-b446-9103cc5743d4/r/01a197d6-354b-728c-ba57-8135d7c8476d?poll=true), [M02](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/5ecef95f-fbd7-4d18-b446-9103cc5743d4/r/01a197d5-e9a7-7165-931f-d84cddf1dac6?poll=true). All IDs: E03, H16, M02, M03, M16, M23.

## Judge and human calibration

Prompt: [`evals/judge_prompt.md`](../evals/judge_prompt.md); outputs: `nestling-ask-improved-v7_vector_safe-503653c5_*_judge.csv`; summaries: `evals/results/phase3_judge_round1.json`. The Qwen judge remains outside the pipeline model families. Latest judge errors: 2 (B13, F09); excluded after up to three attempts.

**Human-vs-judge agreement: pending Anand's labels** (0 labelled). Fill `human_faithful` with Y/N in `evals/results/judge_calibration_v7_vector_safe_2026-11-01.csv` (20 selected cases), then run:

```powershell
uv run python -c "from evals.judge import agreement; print(agreement('evals/results/judge_calibration_v7_vector_safe_2026-11-01.csv'))"
```

## LangSmith and notebooks

- `baseline`: `nestling-ask-baseline-c7951af1`; example trace links are in its saved cases CSV.
- `v1`: `nestling-ask-improved-v1-c2cda087`; example trace links are in its saved cases CSV.
- `v2`: `nestling-ask-improved-v2-763cb206`; example trace links are in its saved cases CSV.
- `v3`: `nestling-ask-improved-v3-9e75044b`; example trace links are in its saved cases CSV.
- `v4`: `nestling-ask-improved-v4-0b33d742`; example trace links are in its saved cases CSV.
- `v5`: `nestling-ask-improved-v5-5981266f`; example trace links are in its saved cases CSV.
- `v6`: `nestling-ask-improved-v6-33609072`; example trace links are in its saved cases CSV.
- `v7_vector_safe`: `nestling-ask-improved-v7_vector_safe-503653c5`; example trace links are in its saved cases CSV.

Executed notebooks (saved execution counts, not a live rerun claim):
- `notebooks/00_setup_and_first_trace.ipynb`
- `notebooks/01_baseline_ask_agent.ipynb`
- `notebooks/02_guardian.ipynb`
- `notebooks/03_concierge_router.ipynb`
- `notebooks/04_retrieval_upgrade.ipynb`
- `notebooks/05_verifier.ipynb`
- `notebooks/06_eval_compare.ipynb`
- `notebooks/08_little_lessons.ipynb`

## Separate Little Lessons evaluation

The original six-topic v1 intent set is **draft, pending human labels**. Its historical routing results remain 39/39 and danger escalation 3/3, with zero errors; they do not measure the expanded 12-topic v2 app prompt. The original six saved storyboards have source fidelity 6/6 (100%); evaluation spend is INR1.8918 under the separate INR20 cap. LangSmith experiment: `nestling-lessons-f15c178e`. These scores never constitute human approval.

| Lesson/version | Source fidelity | Human scene review | Render seconds |
|---|---|---|---|
| bathing v1 | pass | reviewed | 21.7 |
| burping v1 | pass | reviewed | 18.4 |
| cord_care v4 | pass | reviewed | 19.1 |
| holding v3 | pass | reviewed | 20.3 |
| latching v2 | pass | reviewed | 23.8 |
| swaddling v5 | pass | reviewed | 31.6 |

The owner approved every scene of bathing v1, burping v1, latching v2 and cord-care v4 on 2026-11-01 after their source corrections; earlier approvals and verdicts remain historical. Holding v3 replaces the rejected breastfeeding-positioning instructions with registered general cradle guidance. Swaddling v5 completes the registered wrapping method and its safety checks. Raw earlier Qwen False verdicts, including swaddling v3/v4, remain preserved; v5 precision corrections passed cross-family fidelity and independent source/visual review. The owner explicitly approved every scene of holding v3 and swaddling v5 on 2026-11-01, completing the original six scene approvals. Their review-date media is verified and all six videos are published through the local approval gate.

Holding (`NHS-RWT-HOLDING`) and swaddling (`NSW-SCHN-SWADDLING`) use citation-only local research PDFs, with no Pinecone ingestion or public source-text reproduction. Build retrieval separates these from licensed indexed sources and fails closed without evidence. Narration permits 20 words, captions remain 8 words, and the renderer preserves the entire narration text or fails clearly. Independent re-review passed; current checks are 271 Python tests, 39 Node web tests, lint/build and 56 focused lesson/renderer tests. The full suite passed after the closing-card layout fix. These build-only changes do not alter the measured clinical pipeline or require a new benchmark.

Narration costs are estimates, separate from evaluation spend and the unchanged INR244.0804 quality ledger: holding INR4.92; swaddling INR12.60 cumulatively. Earlier burping/latching narration estimates are INR5.20/INR4.74; cord-care corrections total INR3.12. Bathing reused cached audio and its original narration bill is unavailable. Real render logs supply durations; bathing, holding, latching and swaddling exceed the approximate 15-20-second target because complete instructions are retained. Notebook08 was re-executed offline for that original six-lesson inventory, with no paid calls; it does not measure 12-topic intent accuracy.

Six additional before-birth videos now pass source review and cross-family fidelity: labour-room preparation, prenatal yoga preparation, relaxed breathing, bed movement, stair comfort (v2) and gentle activity for birth. The owner approved every scene of these exact versions on 2026-11-01; their review-date videos are verified and all 12 lessons are published locally. Earlier stairs v1 False is retained. These renders run about 29-33 seconds, exceeding the approximate 15-20-second target to retain complete instructions. Eight new citation-only sources use private local research PDFs, with existing MOHFW-ANC also used where relevant. The 37 added phrasings stay local; original 45 Pinecone records are unchanged. Runtime changes use only `app-v7-vector-safe-lessons-v2-prenatal`; lesson-disabled historical variants remain unchanged. Seven immutable original judge roots remain preserved alongside seven zero-inference cached metadata corrections that repair prenatal stage labels; verdicts and costs are unchanged.

Separate new-work costs are narration INR55.32/65 (estimate), Qwen INR0.3609/5 and live API QA INR1.8927/10, totaling INR57.5736 under INR80. These do not modify the historical quality or original lesson-evaluation ledgers.

## Local UX and API verification

[Saved QA summary](../evals/results/ui_qa_2026-11-01.json): 120 listed scenarios across 390x844/1440x1000 and 242 actual client navigations; final focused 50/50, no JavaScript errors or paid-route guard escapes. The reported Ask crash came from a native scrollIntoView Promise returned as effect cleanup; Kerala omitted an optional menu list; service failures were being shown as empty lessons. All three are corrected and rechecked, including explicit Retry recovery. Baseline failures remain preserved; 32 harness-only negatives were corrected and rechecked rather than relabeled.

After publication, a separate 22-check extension verified all six prenatal detail pages, Body/Ready links, stage filters and 12 advancing muted playback observations across both viewports. It added 34 client navigations without JavaScript errors or paid-route guard escapes; it is not part of the original 120-scenario matrix. Final actual HTTP smoke passed 43 checks across all 12 lessons, including ranged videos, thumbnails, stage counts and denial paths.

Browser provider forms were mocked. Nine separate real API cases passed: the original sourced Care, approved burping and zero-model-cost emergency cases, plus six new prenatal questions returning their expected approved lessons. The first three were not repeated; total live API QA spend is INR1.8927/10. This is a smoke check, not a new benchmark. Physical devices, real microphone permissions/audio, native clipboard/sharing and unlisted states remain unverified.

## Production monitoring and human work

Monitor faithfulness drops >5 percentage points over 7 days; p95 cost >25% over budget in 24 hours; latency above SLA on >5% of runs; any sampled missed escalation; Guardian trip rate >2× baseline; tool failures >5% per hour. These alerts are proposed monitoring thresholds, not an installed alerting system.

Little Lessons use their own draft dataset and report; routing intent does not approve media. Six explicitly authorized NHS bathing/burping chunks were added to the existing source namespace. Other source writes need approval. All 12 lessons have exact-version owner scene approval and verified review-date media. Draft lesson labels, judge calibration, the Loom and physical-device/native integration QA remain pending. Optional Tamil Nadu 7/11/21-plate and five-varieties-of-rice practices are now explicitly owner-authorized, independently reviewed and verified through an actual API 200 response. The owner authorized GitHub publication and merge to main for this completed release. No app deployment has been performed, and deployment still requires approval.

## Six-part Loom outline

- Show the parent use case and a sourced answer.
- Show the frozen dataset, labels and hash check.
- Open one failure trace and its source passages.
- Explain Guardian, routing, retrieval and verification changes.
- Compare the saved metrics, including regressions and failed bars.
- Close with the review gates, calibration sheet and monitoring plan.
