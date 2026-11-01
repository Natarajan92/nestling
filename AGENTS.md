# Nestling: rules for coding agents

Start here: read `docs/HANDOFF.md` (current state, blockers, next steps), then `docs/NESTLING_PLAN.md` (the constitution in §2 overrides everything) and `specs/003-complete-app/plan.md` (task briefs and Global Constraints).

- Python 3.12 + uv. Notebooks import from the `nestling/` package; logic lives in .py, not in notebook cells.
- Models (no Anthropic API at runtime): Nebius open models through `nestling/llm.py`. MAIN `deepseek-ai/DeepSeek-V4-Pro` (specialists, verifier, policy Q&A, storyboards), FAST `deepseek-ai/DeepSeek-V4.1-Flash` (guardian classifier, concierge, Capture extraction, lesson matching). Judge: `Qwen/Qwen3-235B-A22B-Instruct-2507` on Nebius — keep the pipeline out of the Qwen family. Claude stays only in `nestling/baseline.py` (Phase 2 record).
- Red-flag escalation is decided in code (`nestling/guardian.py`). Never let an LLM decide it alone.
- Every medical/diet/insurance answer must cite a source ID from `sources/registry.yaml`, or say it has no trusted source. Every Little Lessons step must come from a registered source; web search is for non-medical lookups only.
- Never output medicine doses or diagnoses.
- Every LangSmith trace carries the metadata in plan §9.4. No personal data in traces. The server stores no personal data; browser keys use the `nestling:` prefix.
- The sole active Ask golden set `evals/golden_v3.csv` is FROZEN (2026-11-02; 62 owner-selected/reviewed cases; hash-locked in `nestling/golden.py`). Never edit it; new cases go in a new version. Old Ask input CSVs were deleted at the owner's request; saved v2 results remain historical. Use `evals/v3_run.py` and its separate approved INR350 ledger, never old checkpoints/budgets.
- Pinecone writes need the owner's go-ahead (approved so far: the `lessons` namespace only).
- Little Lessons are never shown unless `lessons/<id>/review.yaml` is approved by a human for the current storyboard version.
- Keep it light: no new frameworks, docs or abstractions unless a task needs them.
- Never commit keys (`.env` is gitignored; update `.env.example`). Commit as the configured git user with no AI attribution. Never push or deploy without the owner's approval.
- Web: Next.js 16 has breaking changes — read `web/AGENTS.md` and `web/node_modules/next/dist/docs/` before writing Next code.
