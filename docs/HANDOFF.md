# Nestling: handoff checkpoint (2026-11-01)

Branch `feature/phase-3-improved` (local commits only, **nothing pushed**). Spec: `docs/NESTLING_PLAN.md` (the constitution in §2 overrides everything). Build plan with all tasks: `specs/003-complete-app/plan.md`. Working rules: `CLAUDE.md` / `AGENTS.md`.

Detailed task log (local, gitignored): `.superpowers/sdd/plan/progress.md` (every decision, review finding and deferred minor), with per-task briefs, reports and review diffs in the same folder.

## 1. Where things stand

| # | Task (plan file) | State | Commits |
|---|---|---|---|
| 1 | Phase 3 comparison, notebooks 02–06, failure analysis | ✅ done, reviewed | c03cc0d |
| 2 | All runtime LLM calls moved to Nebius open models; v6 + code-enforced citations; v6 run + judge | ✅ done, reviewed | 5341e97, 55bdaea, 5bde3b7 |
| 3 | Week 4 report (`docs/week4_report.md`) + README | ⏳ not started (waits for Task 13's v7 result) | — |
| 4 | Little Lessons build pipeline (step-card videos) | ✅ built; scoped re-review passed; owner approved cord_care v2 and latching v1; holding v2 needs correction; three source gaps remain | 99762fc, 97576aa, 38a623f, 7eb40cc |
| 5 | Little Lessons runtime (lessons route, library match, API, Pinecone `lessons` upsert) | ⏳ not started (waits for Task 13; touches graph.py/concierge) | — |
| 6 | Little Lessons eval (`lessons_golden_v1`, §9.9) + notebook 08 | ⏳ not started (after 5) | — |
| 7 | Web foundation: tokens, shell, Welcome, Today, Settings/Delete everything | ✅ done, reviewed | 392b2fc |
| 8 | Web: Ask sheet, How I answered, lesson card, Lessons library | ✅ done, reviewed (red-flag UX, contract and privacy checks pass) | eab213e |
| 9 | Web: Journeys (Body, Ready, Money, Celebrate, Partner) | ⏳ | — |
| 10 | Web: Capture (compare, estimate, quote approval) | ⏳ | — |
| 11 | Web: Memory book, voice journal/letters/own voice, shareable weekly card, `/api/voice/transcribe` | ⏳ | — |
| 12 | Deploy readiness (render.yaml, env, API smoke tests, README) — no deploy | ⏳ | — |
| 13 | v7 quality round (life-stage source routing + model bake-off) | 🟡 code + bake-off done; **blocked** (see §2) | 1fd1dad |
| — | Final whole-branch review (most capable model), one fix wave | ⏳ after all tasks | — |

Tests: 122 passing (31 lesson tests), reverified after the owner's lesson reviews on 2026-11-01. In the Windows sandbox, use a fresh `--basetemp`, `-p no:cacheprovider` and a writable `uv --cache-dir` with `run --no-sync pytest` to avoid permissions on existing caches. Web: `cd web && npm run lint && npm run build`.

## 2. Evaluation results so far (frozen set `golden_v2_india`, 104 cases)

| Version | Models | Escalation | Refusal | Routing | Citation | Faithfulness | p95 s | ₹/answer |
|---|---|---|---|---|---|---|---|---|
| baseline | Claude Sonnet | 100% | 97.1% | 84.6% | 78.1% | 89.3% | 8.57 | 1.31 |
| v4 | Claude | 100% | 99.0% | 81.7% | 67.1% | 94.1% | 16.91 | 1.97 |
| v5 | Claude | 100% | 100% | 97.1% | 75.3% | 84.1% | 15.48 | 1.72 |
| v6 (app today) | DeepSeek-V4-Pro + V4.1-Flash (Nebius) | 100% | 100% | 95.2% | 57.5% | 80.3% ❌ | 14.53 ❌ | 0.75 |

Pass bars (§9.1): escalation 100%, refusal 100%, routing ≥90%, faithfulness ≥90%, p95 < 8 s, cost < ₹2. v1–v5 were measured on Claude (recorded history; re-runs now use the Nebius models). Experiments: `evals/results/phase3_experiments.json`; judge results: `evals/results/phase3_judge_round1.json`; notebook `notebooks/06_eval_compare.ipynb`.

**Task 13 bake-off** (v7 flags = v6 + life-stage source routing, 20 hard cases = v6 failures + 5 controls, Qwen judge; `evals/results/phase3_v7_diagnosis.json`):

| MAIN model | Faithfulness | Citation | Routing | Errors | Cost (20 cases) |
|---|---|---|---|---|---|
| DeepSeek-V4-Pro | 73.7% | 47.1% | 100% | 0 | ₹22.93 |
| GLM-5.3 | 94.1% | 76.5% | 85% | 3 (rerank 429) | ₹36.63 |
| Kimi-K3 | 78.9% | 82.4% | 95% | 1 (rerank 429) | ₹132.18 |

GLM-5.3 needs a large `max_tokens` (empty output at 300, fine at 3000). Model override: `NESTLING_MAIN_MODEL`. Tooling: `evals/bakeoff.py`.

## 3. In flight when the session ended

- **Task 4 fix round 1 reviewed** (97576aa, 38a623f, 7eb40cc; scoped range 99762fc..7eb40cc): no blocking code findings. Changed storyboards bump the persisted version and clear the review; identical content preserves the review. Holding and cord_care boards/reviews consistently use version 2. The rendered holding, cord_care and latching cards were visually checked: cord_care step 1 uses sun, holding step 4 uses shield-check, and the current title icons differ from the steps. Full suite at the review checkpoint: 122 passed.
- **Owner lesson review (2026-11-01):** Anand approved cord_care v2 and latching v1 in chat; recorded with all four scenes passed in their review.yaml files. Their closing cards and MP4s now show the review date (cached audio, no paid calls). The local library gate returns exactly these two lessons as approved; runtime/API integration is still Task 5. Holding v2 was rejected: the owner requires explicit support for the newborn's head, neck and shoulders. Step 4 is marked failed with the correction request; other scenes remain unscored. The current general-holding lesson was drawn from breastfeeding-positioning guidance and needs a better registered source, a rewrite, a new version/render and human re-review. Bathing, burping and swaddling still have no storyboards or videos, only YAML scaffolds; no invented steps.
- Task 8 was reviewed and approved; normal answers and a real lesson payload were not seen live (rerank quota, Task 5 not built) — check both once those are unblocked.

## 4. Blockers and decisions waiting for the owner

1. **Pinecone rerank monthly quota exhausted** (`bge-reranker-v2-m3`, 429). This blocks the full v7 run **and** makes normal app answers fail (red-flag answers still work: they are decided in code). Options: raise/upgrade the Pinecone plan; or add a fallback to vector order when rerank fails (app only — eval runs should fail loudly, not degrade silently); or switch rerank to Fireworks `qwen3-reranker-8b` (changes retrieval, so re-measure).
2. **v7 full run budget.** Task 13 already spent ₹191.74 (budget was ₹150; Kimi was costly). A full v7 run: GLM-5.3 ≈ ₹190, DeepSeek + life-stage routing ≈ ₹100–120. The API moves to v7 only if escalation 100%, refusal 100%, routing ≥ 90% hold and faithfulness beats v6.
3. **Little Lessons source gaps: general holding, bathing, burping, swaddling.** Bathing, burping and swaddling have no registered source with sufficient practical steps (WHO-POSTNATAL covers only the timing of the first bath); holding needs general handling guidance rather than the current breastfeeding-positioning passages. The owner asked to look at how Indian families do this (Instagram, YouTube, Keenable, Toloka). Constitution rule 8 requires every lesson step to come from a registered trusted source, and web search is for non-medical lookups only. Suggested path to confirm with the owner:
   - Steps: register an Indian government source that covers these practices, e.g. the NHM ASHA training modules / Home Based Newborn Care guidelines (newborn bathing, wrapping/keeping warm, burping after feeds, cord care); NHM's copyright policy allows reproduction with prominent source acknowledgement. Alternatively NHS Best Start in Life pages (Open Government Licence v3; credit "Information from the NHS website" + date). Either needs a new registry entry and an ingest into the Pinecone `sources` namespace — a write that needs the owner's go-ahead (only the `lessons` namespace is approved).
   - Indian context: use web research (Keenable/Tavily, YouTube, Instagram) only for framing — the words Indian parents use, common home practices, and myths to gently correct (e.g. putting oil, ash or other substances on the cord) — never as the source of a step.
   - Toloka fits Phase 12: Indian parents rating the finished lessons.
4. **Human work:** re-review holding after the correction and review bathing, burping and swaddling once sourced and rendered (cord_care v2 and latching v1 already approved); label the 20-case judge calibration sheet (Task 3 exports it); review `lessons_golden_v1` draft labels (Task 6); record the Loom; approve push and deploy.

## 5. Decisions already made (owner)

- No Anthropic API at runtime; Nebius (or Fireworks) wherever possible. MAIN `deepseek-ai/DeepSeek-V4-Pro`, FAST `deepseek-ai/DeepSeek-V4.1-Flash` via `nestling/llm.py`; judge `Qwen/Qwen3-235B-A22B-Instruct-2507` on Nebius (keep the pipeline out of the Qwen family so the judge stays cross-family). `nestling/baseline.py` keeps Claude only as the Phase 2 record.
- Embeddings and rerank stay on Pinecone-hosted models (`llama-text-embed-v2`, `bge-reranker-v2-m3`).
- Pinecone writes: approved only for the `lessons` namespace (Task 5's `index_phrasings`); everything else needs a go-ahead.
- Little Lessons visuals: no image model (Nebius has none; Fireworks FLUX is not serverless). Each lesson is a ~15–20 s vertical step-card video drawn in code (`nestling/lessons/cards.py`, Fraunces/Inter OFL fonts and Phosphor MIT icons vendored in `assets/`), narrated with ElevenLabs, stitched with ffmpeg (Gyan.FFmpeg 9.0.2 via winget). Trusted external videos appear only as "See how it's done" link-outs (`see_how`): bathing → NHS, latching → Global Health Media Project (Hindi). Embedding those videos needs written permission.
- Every lesson stays `approved: false` until a human reviews it; unapproved lessons are never shown.
- LangSmith trace limit was raised by the owner (traces work again).
- Committed docs describe the product only.

## 6. Rulings taken during the build (check these)

1. Worked in place on `feature/phase-3-improved` (no worktree).
2. The previously uncommitted work was committed as three commits (Phase 3 / later-phase scaffold / plan) before the build started.
3. The lessons route sits behind a `lessons` version flag; the recorded route is the agent that actually answered, so published v1–v6 results and frozen-set scoring stay comparable.
4. No deploy, no push, no lesson media approval without the owner.
5. `lessons_golden_v1` is drafted with `label_status = draft` until the owner reviews it.
6. Human-vs-judge agreement stays "pending labels"; labels are never invented.
7. The pipeline uses DeepSeek (not Qwen) so the existing Qwen judge needs no re-judging of v1–v5.
8. No per-version provider switch: v1–v5 are recorded history.
9. `enforce_citations` applies to all versions (owner asked for robust citations app-wide).
10. Policy quotes need ≥ 4 words and ≥ 20 characters to count as verified ("covered" taken from "not covered" can't verify).
11. Task 8 was built against the shared lesson payload before Task 5 exists (empty states for `lesson: null` and `/api/lessons` 404).
12. Task 13 runs before Task 5 and Task 3 so the report shows the best version.

## 7. Known follow-ups for the final review (deferred minors)

- compare.py: notebook deltas vs a version not shown; `load_summary` error message; test gaps (citation_misses, write_artifacts).
- llm.py: exceptions without `status_code` are treated as schema rejections (should re-raise); `jsonschema` imported but not declared in pyproject.
- Citations: `_BARE` can delete ordinary hyphenated words followed by "p. N"; "(e.g., WHO-ANC, p. 34)" gets doubled parentheses; one test assert may hold a hidden control character.
- Web (Task 7): `deleteVoice` treats 404 as failure; "Change my answers" restarts Welcome blank; checklist failure shows "0 of 0"; WeekRing ignores reduced motion; fetch has no timeout.
- Web (Task 8): step strip shows the icon name as text (render the vendored Phosphor SVGs instead); with a lesson present, answer chips fall back to nothing if `lesson.sources` is empty (fall back to `res.sources`); Ask sheet has no focus trap/restore or scroll lock; lesson detail prints raw ISO `reviewed_on`; `reviewedOn` exported from a page file; layout indentation.
- Lessons: narration text isn't checked against the cited page (only the evidence quote is); videos run 17–20 s; hygiene steps without safety points show no Safety pill.
- Lessons (scoped re-review): `cards.py:341` falls back to `sparkle` if a valid five-scene board uses all five title candidates, repeating a step icon (current lessons do not trigger this); choose an additional unused vendored icon. Replace holding step 3's stop-like `hand-palm` icon during the required holding rewrite (§3/§4).

## 8. Next steps (in order)

1. Owner decisions in §4 (rerank quota, v7 budget, gap sources).
2. Task 13: full v7 run + judge → app version decision → notebook 06.
3. Task 5 → Task 6 (lessons runtime and eval; run `index_phrasings` dry run, then the approved upsert).
4. Task 3 (Week 4 report from `evals/compare.py` numbers).
5. Tasks 9, 10, 11, 12 (web journeys, Capture, Memory book, deploy readiness).
6. Final whole-branch review, one fix wave, then push/PR with the owner's approval.

Each task: implement → review against its brief in `specs/003-complete-app/plan.md` and the Global Constraints there → fix → re-review. Commit as the configured git user, no AI attribution, never push without approval.
