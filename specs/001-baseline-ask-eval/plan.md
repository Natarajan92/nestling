# Implementation Plan: Baseline Ask Agent and Week 4 Evaluation

**Branch**: `feature/phase-2-baseline` | **Date**: 2026-11-01 | **Spec**: [spec.md](spec.md)

## Summary

One `claude-sonnet-5-5` call answers each golden question from the top passages of plain
dense retrieval (`nestling.retrieval.search`), and returns JSON (structured outputs) with
the answer plus a self-assessment: `escalate`, `route`, `refused`, `sources_cited`. No
Guardian, Concierge or Verifier. `langsmith.evaluate` runs it on the frozen dataset
`nestling-golden-v2` (experiment prefix `nestling-ask-baseline`); code evaluators score
escalation, route, refusal, citation, latency and cost; a summary with pass bars and the
failure list is exported to `evals/results/`. Details: [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.12 (uv) · **Primary Dependencies**: anthropic 2.3, langsmith
0.14, pinecone 10.2 (all already in `pyproject.toml`; nothing new) · **Storage**: CSV/JSON
files in `evals/results/` · **Testing**: one-case end-to-end check (FR-011) plus offline
checks of the scoring functions in the notebook · **Target Platform**: local notebook ·
**Project Type**: library (`nestling/`) + notebook · **Performance Goals**: full run ≤ 30 min
(concurrency 4) · **Constraints**: ≤ ₹250 per full run; no personal data in traces ·
**Scale/Scope**: 104 cases, 19 sources, 2,115 chunks.

## Constitution Check

| Principle | Status |
|---|---|
| I Safety | The baseline is *measured* on escalation; it is never shipped to users. The prompt forbids doses and diagnoses (FR-004). Code-owned escalation arrives in Phase 3 (Guardian). PASS (evaluation-only exception is the point of the baseline). |
| II Sourced | Answers cite registry IDs from retrieved passages only; invalid citations are counted. PASS |
| III Deterministic | Scoring is code; no LLM judge in this phase. PASS |
| IV Traceable | Every case: one trace with retrieval and LLM child runs and all 18 §9.4 fields. PASS |
| V Privacy | Golden questions are synthetic; metadata holds labels, IDs and numbers only. PASS |
| VII Light | No new dependency; two new modules (`nestling/baseline.py`, `evals/evaluators.py` filled in). PASS |

Post-design re-check: unchanged, PASS.

## Project Structure

```text
specs/001-baseline-ask-eval/  plan.md · research.md · data-model.md · quickstart.md · contracts/baseline_answer.schema.json
nestling/baseline.py          prompt, answer schema, ask(), target() for evaluate
nestling/tracing.py           (existing) metadata helpers; cost now counts cache tokens
evals/__init__.py             makes evals importable from the notebook
evals/evaluators.py           per-case scoring, LangSmith evaluators, summary, export
evals/results/                baseline_<date>_cases.csv + baseline_<date>_summary.json
notebooks/01_baseline_ask_agent.ipynb   one-case check → full run → scorecard
```

**Structure Decision**: single Python package plus notebook (plan §7). `evals` is added to
the hatch packages so the notebook can import it.

## Complexity Tracking

None.
