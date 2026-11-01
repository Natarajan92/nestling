# Tasks: Improved Ask Pipeline

## Phase 1: Setup
- [x] T001 Add `langgraph` and dev `pytest` with `uv add`; point .specify/feature.json at this spec

## Phase 2: US1 Guardian (P1) 🎯
- [x] T002 [US1] nestling/guardian.py: red-flag rules with verified source pages, unsafe kinds, negation, general-question check, Haiku classifier with verbatim-quote verification, `decide()`/`screen()`
- [x] T003 [US1] tests/test_guardian.py: positive, negative, negation and general-question phrasings written from the source pages; classifier-quote rejection
- [x] T004 [US1] nestling/graph.py: LangGraph with guardian node and the baseline answerer (v1), `target()` stamping §9.4 metadata, `run_experiment(version)`; one-case check on K01

## Phase 3: US2 Concierge, specialists, retrieval (P2)
- [x] T005 [P] [US2] nestling/concierge.py: Haiku router, nine routes, own few-shot examples
- [x] T006 [P] [US2] nestling/retrieval.py: `sources_for(agent)`, `search_reranked(query, source_ids, top_k=6, candidates=24)`
- [x] T007 [US2] nestling/agents/: shared `answer_from_sources`; care, nourish, money (no-policy handling), ready (labour_bag.yaml), celebrate (playbooks), journal (permission), plus out_of_scope/clarify replies
- [x] T008 [P] [US2] playbooks/labour_bag.yaml and the three tradition playbooks (each item cites a source ID or is marked family custom)

## Phase 4: US3 Verifier, judge, comparison (P3)
- [x] T009 [US3] nestling/verifier.py: claim check against cited passages, one rewrite, else the no-trusted-source line
- [x] T010 [P] [US3] evals/judge.py + evals/judge_prompt.md: Nebius faithfulness judge; `judge_experiment()` attaches feedback; calibration sheet export
- [x] T011 [US3] Run v1…v4 on the frozen set (notebooks 02–05, one per lever) and export results
- [x] T012 [US3] notebooks/06_eval_compare.ipynb: baseline vs v1…v4 table with deltas and regressions; judge on baseline and v4

## Phase 5: Polish
- [ ] T013 Update README eval table, plan §9 notes and commit
