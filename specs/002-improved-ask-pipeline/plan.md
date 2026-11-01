# Implementation Plan: Improved Ask Pipeline

**Branch**: `feature/phase-3-improved` | **Date**: 2026-11-01 | **Spec**: [spec.md](spec.md)

## Summary

A LangGraph graph (`nestling/graph.py`): **Guardian** (code rules + Haiku proposals verified
in code) → **Concierge** (Haiku, few-shot) → one **specialist** (Sonnet + filtered, reranked
retrieval, or deterministic YAML for Ready/Celebrate) → **Verifier** (Sonnet, one rewrite).
Levers are switched on cumulatively so each is measured on the frozen set:

| version | adds | experiment prefix |
|---|---|---|
| v1 | Guardian in front of the baseline answerer | `nestling-ask-improved-v1` |
| v2 | + Concierge and specialists | `nestling-ask-improved-v2` |
| v3 | + source filters, life-stage query, rerank (top 24 → 6) | `nestling-ask-improved-v3` |
| v4 | + Verifier | `nestling-ask-improved-v4` |

Same target signature, metadata and evaluators as the baseline (`evals/evaluators.py`),
plus `faithfulness_judge` (Nebius Qwen3-235B, OpenAI-compatible HTTP, no new SDK).

## Technical Context

Python 3.12 · anthropic, langsmith, pinecone (rerank: `pc.inference.rerank`,
`bge-reranker-v2-m3`, inference only, no index writes) · **new**: `langgraph` (plan §5),
`pytest` (dev, Guardian rules) · Performance: p95 < 8 s target; escalations answered without
a Sonnet call · Cost: ≤ ₹1,000 for all Phase 3 runs.

## Constitution Check

I Safety: escalation and refusal decided in code; classifier can only add verified flags;
every rule cites a checked page. II Sourced: specialists cite retrieved registry IDs; Verifier
enforces it. III Deterministic: rules, checklists and playbooks in code/YAML. IV Traceable:
graph nodes are child runs; metadata adds nothing outside §9.4 (rules fired live in outputs).
V Privacy: unchanged (synthetic questions, IDs in metadata). VII Light: one new runtime
dependency named in the plan. PASS.

## Project Structure

```text
nestling/guardian.py           rules, classifier, decide(), screen()
nestling/concierge.py          route(): Haiku + few-shot
nestling/agents/__init__.py    shared RAG answerer (answer_from_sources)
nestling/agents/{care,nourish,money,ready,celebrate,journal}.py
nestling/retrieval.py          + sources_for(agent), search_reranked()
nestling/verifier.py           verify() + rewrite
nestling/graph.py              LangGraph wiring, ask(), target(), run_experiment(version)
playbooks/*.yaml               labour bag + three traditions (sourced or "family custom")
evals/judge.py                 Nebius faithfulness judge; evals/judge_prompt.md
tests/test_guardian.py         rule phrasings from source pages
notebooks/02_guardian … 06_eval_compare.ipynb
```

## Complexity Tracking

None.
