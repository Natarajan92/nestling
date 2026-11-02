# Latency improvement checkpoint — 2 November 2026

**Status: implemented and reviewed offline; hosted-model measurement awaits owner budget approval.** The selected application is still Round 1. No speed improvement is claimed yet.

The saved R1 timings show p95 **12.11s**, standard median **7.38s**, and 24/62 responses at or above eight seconds. Screening/routing can take more than six seconds even for tiny JSON outputs because FAST still produces hidden reasoning. Verification rewrote 25/62 answers; 19 of the 24 slow responses were in that cohort. Retrieval also has slow early requests. The offline Qwen judge is excluded from response latency.

## Implemented candidates

- Caller-scoped `reasoning_effort="none"` or `"low"` for Guardian classification and Concierge routing. The argument is omitted entirely by default, retained across JSON-format fallback, and never silently dropped on provider rejection.
- The existing parallel screening/routing remains intact. Code still owns escalation and quote validation. MAIN generation and the complete strict Verifier remain unchanged; no answer truncation or compact-checker promotion.
- Optional startup initialization of the existing cached source-index handle. It performs no embedding/search/write and caches no parent information. It is inactive in the current selected app. Startup failure leaves health and code-owned safety available.
- Separate `latency1`–`latency3` experiment folders and a new budget/lock namespace. The unchanged v3 runner, evaluator, Qwen rubric and frozen labels are reused. Existing results and the old ledger are preserved.

## Verification before paid work

The complete offline suite passes **457 tests**, with one existing LangSmith deprecation warning. Independent review and regression tests cover invalid provider JSON, unchanged default calls, MAIN isolation, source/model/auth-bound probes, lock/checkpoint ordering, SDK restoration, and durable budget reservations after interruption.

Existing measurement, judge, scorer, registry and golden-loader hashes still match R1. Frozen CSV SHA256 remains `8075c270caa94751047580136d7588ba1d49a51fb9a194688c54be92fc387012`.

## Proposed paid verification

Owner approval requested: up to **₹160**, including a small FAST compatibility probe and up to three complete 62-case evaluations with the same Qwen judge and deidentified LangSmith traces. This extends the exhausted three-round scope; the old ledger is unchanged. With ₹183.9041 already accounted, maximum combined v3 spend would be ₹343.9041, below the original ₹350 ceiling.

The probe must confirm valid JSON and that `none` actually removes hosted-model reasoning; defaults and the candidate are observed separately. Probe data is not a pipeline benchmark. Every new request uses the shared new cap; probe work also has a ₹10 subcap, including unknown-outcome reservations. No approval file is created until the owner approves.

Full measurements use unchanged inputs, labels, models and judge. Promotion requires completed traces, preserved safety/refusal, routing and useful-answer quality, source integrity, and a defensible paired comparison with the latest retained candidate. Target p95 remains below eight seconds. Startup initialization is recorded separately when used, matching API startup behavior.

Offline status: `uv run python -m evals.latency_run --status`. Paid commands remain blocked until `evals/results/golden_v3/latency_budget/authorization.json` contains the owner's actual approval.

Provider support for `reasoning_effort` is documented in the [Nebius API](https://docs.tokenfactory.nebius.com/api-reference/inference/create-chat-completion); behavior on the exact hosted FAST model still needs the probe. No deployment, new Pinecone writes or lesson changes are included.
