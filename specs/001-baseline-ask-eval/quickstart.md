# Quickstart: validate the baseline

Prerequisites: `.env` with `ANTHROPIC_API_KEY`, `LANGSMITH_*`, `PINECONE_API_KEY`,
`PINECONE_INDEX=nestling-sources`; `uv sync`; dataset `nestling-golden-v2` exists
(`uv run python -m nestling.golden upload` is idempotent).

1. **Frozen check**: `uv run python -m nestling.golden` → `golden_v2_india: 104 cases, sha256 ok`.
2. **One case** (FR-011): `uv run python -m nestling.baseline K01` prints the answer, the
   self-assessment, the scores and the trace URL. Open the trace: a `retrieval` child, a
   Claude child, and all 18 §9.4 keys in the root run's metadata.
3. **Full run**: run `notebooks/01_baseline_ask_agent.ipynb` top to bottom (or
   `uv run python -m nestling.baseline all`). Expected: 104 rows, ≥ 98% without error,
   under 30 minutes and ₹250.
4. **Outputs**: `evals/results/baseline_<date>_cases.csv` (104 rows) and
   `baseline_<date>_summary.json` (six measures with pass bars, every missed escalation and
   wrong refusal with a trace URL). The experiment `nestling-ask-baseline-…` appears under the
   dataset in LangSmith, ready for the Phase 3 comparison.
