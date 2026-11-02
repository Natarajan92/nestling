# Latency improvement checkpoint — 2 November 2026

**Status: all three authorized latency rounds completed and were rejected; Round 1 remains selected.** Each of the seven total runs has 62 verified traces and zero pipeline/judge errors. The eight-second p95 target remains unmet; component/probe improvements do not establish a successful full-pipeline optimization.

The saved R1 timings show p95 **12.11s**, standard median **7.38s**, and 24/62 responses at or above eight seconds. Screening/routing can take more than six seconds even for tiny JSON outputs, while FAST also produces hidden reasoning. Verification rewrote 25/62 answers; 19 of the 24 slow responses were in that cohort. Retrieval also has slow early requests. The offline Qwen judge is excluded from response latency.

## Bottleneck evidence

Within R1's 24 slow cases, mean stage durations were **2.662s screening/routing**, **1.687s retrieval**, **2.385s generation** and **3.175s verification/rewrite**. These are observed spans; they do not separate network time, provider queueing and decoding.

The saved FAST compatibility probe measured a default mean of **1.454s** versus **0.710s** with `none`, with **9,629 versus zero reasoning characters**. That confirms the requested behavior on those probe calls; it is not a full-pipeline speed or quality result.

A separate immutable `probe-low.json` records **8/8 valid** with `low` versus **7/8 valid** in its default batch. Means were **2.687s default versus 2.222s low**, with **9,812 versus 5,789 reasoning characters**. The `none` and `low` probes occurred in different batches/provider conditions, so their means do not establish a direct causal comparison between those settings. The final candidate changes FAST reasoning and startup warmup only; MAIN reasoning and strict verification remain unchanged.

Saved latency1 examples show why screening alone cannot remove the tail:

| Case | Screening/routing s | Retrieval s | Generation s | Verification/rewrite s | Total pipeline s |
| --- | ---: | ---: | ---: | ---: | ---: |
| H01 | 1.856 | 5.543 | 5.741 | 2.862 | 16.124 |
| H03 | 2.183 | 5.238 | 3.089 | 5.102 | 15.721 |
| M01 | Not quoted | Not quoted | Not quoted | 7.120 | 13.406 |
| M03 | Not quoted | Not quoted | Not quoted | 6.247 | 13.098 |

These individual saved cases do not establish the completed round's aggregate result. Retrieval, MAIN generation and verification/rewrite still contribute substantial tails after the bounded FAST change.

Code-only deletion of unsupported claims was **not implemented**. The checker's claim strings can be paraphrases, and checkpoints do not retain exact raw-answer character spans for those claims. Removing matching strings would therefore risk retaining unsupported material or damaging supported text. The complete strict-checker path remains in use.

Cached R1 MAIN spans show **38 specialist calls with median 2.112s**, **33 strict-check calls with median 1.683s**, and **26 subsequent rewrite calls with median 1.564s**. These are call counts, not counts of distinct answers. Generation, strict checking and any rewrite occur sequentially and contribute a cumulative tail. The cache preserves durations and aggregate token counts, so MAIN hidden reasoning is **unknown**; these timings cannot be attributed to it. A MAIN reasoning-effort experiment would require separate future scope and was not performed in this FAST/warmup campaign.

## Completed measured decisions

### latency1: FAST direct mode

**Reject.** All 62 cases completed with verified traces and zero pipeline/judge errors. Faithfulness was **35/37 = 94.59%** from 39 eligible replies; paired R1 faithfulness improved **31/34 to 32/34**. Task fulfillment improved **52/62 to 55/62**, with five abstentions and routing **58/62**. Mean pipeline cost was **INR0.710**, with p95 cost **INR1.464**.

Those quality gains did not satisfy the declared latency gate: full-set p95 rose from **12.11s to 13.10s**. That decision retained R1 for the next comparison. Citation match was **38/46**; visible whole IDs were **54/55**, with H16 missing a visible `MOHFW-ANC` marker. Registered/retrieved-citation safety checks had zero failures. Keep these different citation diagnostics distinct.

### latency2: startup warmup

**Reject.** All 62 cases have verified traces with no errors. Pipeline p95 fell from R1's **12.11s to 11.19s**, but remains above eight seconds. Faithfulness was **33/37 = 89.19%**, below the 90% gate; on the same 34 valid paired cases, R1 scored **31/34** and latency2 **30/34**. The faster result therefore does not justify promotion.

Startup initialization took **2.5003s**, recorded separately and excluded from the request timer. That exclusion matches startup behavior; it must remain visible when comparing the warm candidate with the retained R1 measurement. That measured quality regression prevented promotion.

## Implemented candidates

- Caller-scoped `reasoning_effort="none"` or `"low"` for Guardian classification and Concierge routing. The argument is omitted entirely by default, retained across JSON-format fallback, and never silently dropped on provider rejection.
- The existing parallel screening/routing remains intact. Code still owns escalation and quote validation. MAIN generation and the complete strict Verifier remain unchanged; no answer truncation or compact-checker promotion.
- Optional startup initialization of the existing cached source-index handle. It performs no embedding/search/write and caches no parent information. It is inactive in the current selected app. Startup failure leaves health and code-owned safety available.
- Separate `latency1`–`latency3` experiment folders and a new budget/lock namespace. The unchanged v3 runner, evaluator, Qwen rubric and frozen labels are reused. Existing results and the old ledger are preserved.

## Verification before paid work

The complete offline suite passes **457 tests**, with one existing LangSmith deprecation warning. Independent review and regression tests cover invalid provider JSON, unchanged default calls, MAIN isolation, source/model/auth-bound probes, lock/checkpoint ordering, SDK restoration, and durable budget reservations after interruption.

Existing measurement, judge, scorer, registry and golden-loader hashes still match R1. Frozen CSV SHA256 remains `8075c270caa94751047580136d7588ba1d49a51fb9a194688c54be92fc387012`.

## Authorized paid verification

The owner's saved approval permits up to **INR160**, including a small FAST compatibility probe and up to three complete 62-case evaluations with the same Qwen judge and deidentified LangSmith traces. This extends the completed original three-round scope; the old ledger is unchanged. With INR183.9041 already accounted, maximum combined v3 spend is INR343.9041, below the original INR350 ceiling. Approval provenance is saved in `evals/results/golden_v3/latency_budget/authorization.json`; actual latency requests and pending reservations use that folder's separate `spend.json`.

The probe must confirm valid JSON and that `none` actually removes hosted-model reasoning; defaults and the candidate are observed separately. Probe data is not a pipeline benchmark. Every new request uses the shared new cap; probe work also has an INR10 subcap, including unknown-outcome reservations. Saved probe records must be read before choosing the setting for a full measurement.

Full measurements use unchanged inputs, labels, models and judge. Promotion requires completed traces, preserved safety/refusal, routing and useful-answer quality, source integrity, and a defensible paired comparison with the latest retained candidate. Target p95 remains below eight seconds. Startup initialization is recorded separately when used, matching API startup behavior.

Offline status: `uv run python -m evals.latency_run --status`. Only completed, trace-verified rounds belong in score comparisons; retain partial checkpoints privately for recovery. Submission generators discover completed rounds and the latest saved keep decision, retain older rejected experiments, and include the separate budget provenance. Full checkpoints and every per-round `calibration.csv` contain source passages and are excluded from the submission ZIP.

Provider support for `reasoning_effort` is documented in the [Nebius API](https://docs.tokenfactory.nebius.com/api-reference/inference/create-chat-completion); behavior on the exact hosted FAST model still needs the probe. No deployment, new Pinecone writes or lesson changes are included.


### latency3: low FAST reasoning plus startup warmup

**Reject.** All 62 traces were verified with zero pipeline/judge errors. Pipeline p95 was **11.24s**, versus R1's 12.11s; faithfulness was **32/36 = 88.89%**, from 39 eligible replies with three zero-claim answers. Paired R1 faithfulness fell **29/32 to 28/32**. Task fulfillment was **52/62**, abstentions rose **5 to 6**, routing was **59/62**, citation match **37/46**, and mean pipeline cost **INR0.737**. The faithfulness and abstention gates failed. All three latency candidates remain preserved as rejected experiments; R1 stays selected.

## Final accounting and API option

The original ledger remains **INR183.9041**. The separately authorized latency campaign accounted for **INR146.6423 / INR160**, with zero pending reservations; combined accounting is **INR330.5464**. Probe work, failed attempts and conservative unknown-outcome accounting remain in the saved ledger. These are Nebius model-token estimates, excluding hosting and Pinecone charges, not reconciled invoices. No fourth latency round was run.

After paid measurement ended, an API-only `NESTLING_PREWARM_SOURCES=1` (or `true`) option was added. It defaults off, preserves R1 answer flags and FAST behavior, and waits at most five seconds for source-handle initialization. A timeout stops waiting but does not abort the worker thread, which may still finish. This source-handle operation does no search, embedding or write. The optional startup path is not a new measured request-p95 improvement; historical R1 timings remain prewarm-off.
