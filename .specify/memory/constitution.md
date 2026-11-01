# Nestling Constitution

## Core Principles

### I. Safety First (NON-NEGOTIABLE)

- Red-flag symptoms MUST be detected by code-owned rules (`nestling/guardian.py`).
- The LLM MAY classify text, but MUST NOT decide escalation alone.
- On a red flag, Nestling MUST answer: *"Please contact your doctor or go to the hospital
  now,"* plus the source.
- Nestling MUST NOT give a diagnosis or medicine dosing, ever.

Rationale: a missed danger sign in pregnancy can cost a life; escalation has to be
deterministic and testable.

### II. Every Answer Is Sourced

- Medical, diet and insurance answers MUST cite a registered source from
  `sources/registry.yaml` (title, section or page, link).
- With no source, Nestling MUST say: *"I don't have a trusted source for that. Please ask
  your doctor."*
- Gaps MUST be flagged, never invented.

### III. Deterministic Where It Matters

- Code MUST own the week calculation, checklists, red-flag rules and insurance clause lookup.
- The LLM explains and personalizes; it MUST NOT be the source of these facts.

### IV. Traceable

- Every answer MUST store its route, rules fired, sources, model and prompt version in
  LangSmith, with the metadata schema in plan §9.4.
- Users see a gentle "How I answered"; judges see the full trace.

### V. Privacy

- Pregnancy data is sensitive health data (in the spirit of India's DPDP Act).
- Nestling MUST ask for explicit consent, collect the minimum, and offer a
  "Delete everything" button.
- Traces MUST contain no personal data.

### VI. Warmth

- Responses MUST be calm and kind, never alarming except when safety requires it.
- Language MUST be inclusive of single parents, partners and all family shapes.

### VII. Light Engineering

- One spec per journey; about 30–40 eval cases per agent; ship small, and post about it.
- New frameworks, documents or abstractions MUST NOT be added unless a phase needs them.

Rationale: the demo and the story come first; rigor serves them, not the reverse.

## Technology & Model Constraints

- Python 3.12 with `uv`. Notebooks import from the `nestling/` package; logic lives in `.py`
  files, not notebook cells.
- Models: `claude-sonnet-5-5` for specialists and the Verifier; `claude-haiku-5-5` for the
  Guardian classifier and the Concierge.
- Tavily (and any live web lookup) is for non-medical content only.
- Keys MUST NOT be committed: use `.env` (gitignored) and `.env.example`.

## Development Workflow & Quality Gates

- Spec Kit lite: constitution → one spec per phase → a one-page plan → at most 15 tasks per
  phase → implement.
- The active golden set (`evals/golden_v2_india.csv`) MUST be frozen before the baseline run
  and never edited afterwards; new cases go in a new version.
- Verify ONE LangSmith trace end to end before running a full eval.
- Week 4 pass bars: escalation recall 100%, faithfulness ≥90%, routing ≥90%, refusal 100%,
  p95 latency < 8s, cost < ₹2 per answer.
- Regressions MUST be reported honestly alongside improvements.

## Governance

- This constitution overrides every other practice, plan or prompt in the repo.
- Amendments require an update to this file and to plan §2, with a version bump:
  MAJOR for removing or redefining a principle, MINOR for adding one or materially expanding
  guidance, PATCH for wording.
- Every spec, plan and PR MUST be checked against Principles I–V before merge.
- Runtime guidance for Claude Code lives in `CLAUDE.md`.

**Version**: 1.0.1 | **Ratified**: 2026-11-01 | **Last Amended**: 2026-11-01
