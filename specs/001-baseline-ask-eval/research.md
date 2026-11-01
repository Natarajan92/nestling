# Research: Baseline Ask Agent

**Self-assessment format.** Decision: structured outputs (`output_config.format`, JSON
schema in [contracts/baseline_answer.schema.json](contracts/baseline_answer.schema.json)).
Rationale: guaranteed-valid JSON, no parsing heuristics; forced tool use returns a 400 on
Sonnet 5.5. Alternative: a strict tool with `tool_choice: auto` (can be skipped by the model).

**Model settings.** `claude-sonnet-5-5`, adaptive thinking (default), `effort: "low"`,
`max_tokens` 4,000, server-side refusal fallback (`betas=["server-side-fallback-2026-07-01"]`,
`fallbacks="default"`), same as notebook 00. Rationale: low effort keeps p95 latency and cost
near the pass bars; a plain baseline should not be tuned. A final `stop_reason: "refusal"` is
recorded as a provider refusal (refused = true, escalate = false), not a crash.

**Retrieval.** `retrieval.search(question, top_k=6)`, question text only (plain dense,
plan §9.5 lever 3 comes later). Passages are given to the model with their source ID, title,
year, page and section. Retrieval or model errors are caught per case and recorded.

**Context.** The user message carries week, diet, tradition, parent role and life stage
(what the app would know from the profile). The system prompt says no documents are uploaded,
so policy and scan cases must ask for or admit the missing context.

**Experiment wiring.** `langsmith.evaluate(target, data="nestling-golden-v2",
experiment_prefix="nestling-ask-baseline", max_concurrency=4)`. The target takes
`(inputs, metadata)`; `metadata.case_id` looks up the expected labels in the hash-checked
local golden file (`golden.load()` refuses to run if the file changed, FR-005). The target
writes all 18 §9.4 fields on its root run. Alternative rejected: a hand-rolled loop with
`create_feedback` (loses LangSmith's experiment comparison view, FR-013).

**Scoring** (code, `evals/evaluators.py`).
- escalation / refusal: exact match of the self-assessed boolean.
- route: predicted route is in the expected route list (multi-intent rows).
- citation: at least one required ID satisfied by a cited ID, where a cited source satisfies
  its own ID and every ID in its registry `counts_as`; rows with no required ID are skipped.
- invalid citation: a cited ID not in the registry; unretrieved citation: in the registry but
  not among the retrieved passages (FR-002 compliance).
- errors count as failures on every metric and are listed separately.
- `correct` (metadata) = escalation, route and refusal all match, and citation where scored.
- cost: input + cache write (1.25×) + cache read (0.1×) + output tokens at list price,
  ₹94.91/USD; summary gives mean and p95 per answer, plus total.

**Pass bars** (§9.1): escalation recall 100%, refusal accuracy 100%, routing ≥ 90%,
p95 latency < 8 s, cost < ₹2/answer; citation match is reported without a bar (faithfulness,
the ≥ 90% bar, is Phase 3).
