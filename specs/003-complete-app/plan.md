# Plan: Complete Nestling (Phases 3 close-out → 10)

**Spec:** `docs/NESTLING_PLAN.md` (the constitution in §2 overrides everything). Repo rules: `CLAUDE.md`.
**Branch:** `feature/phase-3-improved` (work in place; commit locally; never push).
**Out of scope (human work):** Loom recording, real medical review of lessons, Toloka (Phase 12), domain and permissions, deploying, any Pinecone write, installing system software (ffmpeg).

## Global Constraints

- The constitution (plan §2) overrides everything: red-flag escalation decided in code (`nestling/guardian.py`), never by an LLM alone; no medicine doses or diagnoses, ever; every medical/diet/insurance answer cites a source ID from `sources/registry.yaml` or says *"I don't have a trusted source for that. Please ask your doctor."*
- Little Lessons (constitution rule 8): safety-critical how-tos are pre-generated and human-reviewed, never generated live per question; every step comes from a registered source; illustration style only, baby always covered (nappy, towel or clothes); every lesson has a safety checklist including *"image matches narration"*; an unapproved video is never shown; no approved video → written sourced steps only (Care + Verifier) and the gap is logged; live image generation only for fun content.
- Models: `claude-sonnet-5-5` (specialists, verifier, storyboards), `claude-haiku-5-5` (guardian classifier, concierge, lesson matching). Judge: Nebius (`evals/judge.py`).
- `evals/golden_v2_india.csv` is FROZEN (hash-locked in `nestling/golden.py`). Never edit it. Existing pipeline versions v1–v5 in `nestling/graph.py` must keep their behaviour (results already published).
- Privacy: no personal data in traces (§9.4 metadata only; app traces hide inputs/outputs). The server stores no personal data: profile, checklist ticks, journal, letters and voice ID live in the browser. Uploaded files and audio are processed in memory, never stored.
- Logic lives in `.py`, notebooks only import and display. Python 3.12 + `uv`. Tests with `pytest`; tests never call paid APIs (mock them).
- Keep it light: no new frameworks or abstractions beyond what the task needs. Web: Next.js 16 (read `web/AGENTS.md` and the guides in `web/node_modules/next/dist/docs/` before writing Next code), React 19, Tailwind 4, `motion`. No new UI component libraries.
- Design language (plan §3): cream `#FFF8F1` background · peach `#F7B49A` · blush `#EFA3B5` · sage `#9CB89A` · ink `#2E2A3A` · gold `#E8B65A`; Fraunces for display, Inter for body; 24px radii, soft shadows, generous whitespace; gentle motion; mobile-first. Calm and warm; alarming only for red flags.
- Disclaimer shown in the app: *"Nestling offers general information from trusted sources and is not a substitute for medical advice. In an emergency, contact your doctor or the nearest hospital."*
- Commits: as the configured git user, with NO `Co-Authored-By` trailer and no AI attribution. Never push. Never commit keys (`.env` is gitignored).
- Paid API calls are allowed only where a task says so, within its stated budget.

## Shared interfaces (fixed here so tasks agree)

- **Storyboard** `lessons/<lesson_id>/storyboard.json`: `{"lesson_id", "title", "version" (int), "stage" ("before_birth"|"first_weeks"), "language": "en", "sources": [source_id...], "scenes": [{"step_no", "caption", "image_prompt", "narration_line", "source_id", "page_label", "safety_points": [..]}]}` with 5–6 scenes.
- **Checklist** `lessons/<lesson_id>/checklist.yaml`: `{lesson_id, items: [str]}` (always includes "Image matches narration").
- **Phrasings** `lessons/<lesson_id>/phrasings.yaml`: `{lesson_id, phrasings: [str]}`.
- **Review** `lessons/<lesson_id>/review.yaml`: `{lesson_id, version, approved: false, reviewer: null, review_date: null, scenes: [{step_no, passed: null, notes: ""}]}`.
- **Renders** `lessons/<lesson_id>/renders/` (gitignored): `scene_<n>.png`, `scene_<n>.mp3`, `lesson.mp4`, `thumbnail.jpg`, `render_log.json` (`{cost_inr, seconds, image_provider, rendered_at}`).
- **Approved** = `review.yaml` has `approved: true`, `version` equals the storyboard version, every scene `passed: true`, and `renders/lesson.mp4` exists.
- **API lesson payload** (used by `/api/lessons`, `/api/lessons/{id}` and the `lesson` field of `/api/ask`): `{"lesson_id", "title", "version", "stage", "video_url", "thumbnail_url", "steps": [{"step_no", "caption", "safety_points"}], "sources": [source chip], "reviewed_on"}`. Media served at `/media/lessons/{lesson_id}/{lesson.mp4|thumbnail.jpg}` for approved lessons only (404 otherwise). `/api/ask` returns `"lesson": null` when no approved lesson was served.
- **Web**: `web/lib/api.ts` (typed fetch helpers; base URL `process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"`), `web/lib/store.ts` (all browser state, every localStorage access in try/catch; `deleteEverything()`), shared components in `web/components/`.

---

### Task 1: Phase 3 comparison, notebooks 02–06 and failure analysis

Close the Phase 3 evidence from results that already exist (no new pipeline runs in this task).

- Add `evals/compare.py`: load every `evals/results/*_summary.json` and `*_judge.csv`; `comparison_table()` (baseline, v1…v5: escalation recall, refusal, routing, citation match, faithfulness from the judge CSV, p95 latency, mean/p95 cost, with deltas vs the previous version and vs baseline, and pass/fail against the §9.1 pass bars); `faithfulness_regressions(a, b)` (case IDs faithful in run a and unfaithful in run b, with the judge's `unsupported` claims and the agent); `failure_modes(version)` grouping failing cases into categories (routing boundary, refusal calibration, wrong source family, unsupported claim, citation mismatch) with case IDs.
- Update `evals/results/phase3_judge_round1.json` to include `baseline` and `v5` (computed with the same method as v1–v4 in `evals/judge.py::summary`).
- Write `evals/results/phase3_failure_analysis.json`: the v4→v5 faithfulness regressions, the v5 citation-match misses, and the top 3 failure modes of v5 with case IDs.
- Notebooks `notebooks/02_guardian.ipynb`, `03_concierge_router.ipynb`, `04_retrieval_upgrade.ipynb`, `05_verifier.ipynb` (one per lever: what changed, metrics before/after from saved results, the live-run cell guarded by `RUN_LIVE = False`) and `06_eval_compare.ipynb` (full table, regressions, failure modes). Execute them with saved results (add `nbconvert`/`ipykernel` as dev dependencies only if missing) so outputs are stored.
- Tick T001–T012 in `specs/002-improved-ask-pipeline/tasks.md` where the code and results exist.
- Tests: `tests/test_compare.py` with small fixture files.

### Task 2: Fix the v5 faithfulness regression (v6) and re-run

- Read `evals/results/phase3_failure_analysis.json`. Make the smallest targeted change (prompt, specialist instructions, verifier or retrieval) that restores faithfulness without losing v5's routing and refusal gains. Add it as a new version `v6` in `nestling/graph.py` (`VERSIONS`, `PROMPT_VERSIONS`); v1–v5 unchanged.
- Unit tests for any deterministic part of the change.
- Check one case end to end (`graph.run_one`), then run `graph.run_experiment("v6")` on the frozen set and `evals/judge.py::judge_experiment` on it; export results with the same file naming as v1–v5 and add v6 to `phase3_experiments.json` and `phase3_judge_round1.json`; add v6 to notebook 06 and re-execute it. **Budget:** at most one full v6 run plus its judge pass (about ₹250). If the first run has errors, re-run only failing cases.
- Set the app's version (`api/main.py`, currently `"v5"`) to v6 only if v6 keeps escalation recall 100%, refusal 100% and routing ≥ 90% and has faithfulness ≥ v5; otherwise leave v5 and report why.

### Task 3: Week 4 package (Phase 4) and README

- `docs/week4_report.md`: the §9.1 one-liner, framework table, metrics and rubric with pass bars, baseline vs improved (v1…v6) with deltas and regressions reported honestly, top 3 failure modes with case IDs, the judge (model, prompt path, outputs), human-vs-judge agreement, LangSmith experiment names, executed notebooks list, production monitoring (§9.6), and a 6-bullet Loom outline (use case → dataset → a failure → fixes → results). Keep it short and factual; numbers come from `evals/compare.py` output, not retyped by hand.
- Human-vs-judge agreement needs Anand's labels: export a calibration sheet with `evals/judge.py::calibration_sheet` (20 cases from the latest run) and mark agreement as *pending Anand's labels* with the exact command to compute it (`evals/judge.py::agreement`). Do not invent labels.
- README: one-liner, eval headline table (baseline vs best), how to run tests/API/web.
- Plan §9: add an "Improved result" note under the baseline note (same style), tick the §9.7 items that are done.

### Task 4: Little Lessons build pipeline

- `nestling/lessons/` with `__init__.py`, `storyboard.py`, `render_images.py`, `narrate.py`, `stitch.py`, `library.py` (plan §4 "how a lesson is made", §7).
  - `storyboard.py`: retrieve passages from the registered sources (`nestling.retrieval.search_reranked`, Pinecone reads only) for the lesson topic; Sonnet writes 5–6 scenes in the storyboard schema (narration_line and image_prompt written together per scene; narration 20–40 seconds in total). Validate: every scene's `source_id` and `page_label` come from the retrieved passages; no doses, no diagnoses; baby covered in every image_prompt. If the passages do not support the steps, return a `no_trusted_source` result and write nothing. CLI: `uv run python -m nestling.lessons.storyboard <lesson_id>`.
  - `render_images.py`: one fixed `STYLE_PROMPT` (soft hand-drawn illustration in the §3 palette, not photorealistic, baby always covered) + each scene's image_prompt → image via Fireworks or Nebius (provider from `NESTLING_IMAGE_PROVIDER`, default `fireworks`; both supported behind one function since the choice is an open decision).
  - `narrate.py`: ElevenLabs narration per scene (reuse `nestling/voice.py`), returning audio length.
  - `stitch.py`: pure `build_command(...)` producing the ffmpeg command (each image shown for its narration's length, gentle zoom/pan, captions, audio, MP4 + thumbnail) and `stitch()` that runs it, raising a clear error if ffmpeg is not installed. `render_log.json` written per the shared interface.
  - `library.py`: load lessons from `lessons/`, `approved()`, `get(lesson_id)`, `is_approved(lesson_id)` per the shared-interface definition.
- `lessons/<lesson_id>/checklist.yaml`, `phrasings.yaml` (6–8 phrasings each) and `review.yaml` (`approved: false`) for the six proposed lessons: `holding`, `bathing`, `burping`, `swaddling`, `latching`, `cord_care` (bathing/holding checklist items from constitution rule 8, plus "Image matches narration" in all). Add `lessons/*/renders/` to `.gitignore`.
- Generate storyboards for all six with the CLI (Sonnet calls allowed, budget about ₹30). Commit the ones produced; for lessons without a trusted source, report them as gaps (do not invent steps). Do not render images or narration (provider decision open, ffmpeg not installed, no reviewer yet).
- `tests/test_lessons.py` with mocked LLM/HTTP: storyboard validation (bad source_id rejected, scene count, uncovered-baby prompt rejected), `build_command`, approval rules.

### Task 5: Little Lessons at runtime (routing, library, API)

- `nestling/lessons/library.py`: `match(question) -> {"lesson_id": str | None, "topic": str}` using Haiku as a closed-set classifier over all known lessons (titles + phrasings as examples, plus "none"); `index_phrasings(dry_run=True)` that prepares records for the Pinecone namespace `lessons` and only prints them (the real write needs Anand's go-ahead; never call it with `dry_run=False`).
- Concierge: add route `lessons` (practical newborn-care how-tos) with few-shot examples. Graph: a lessons node after the Concierge: matched and approved → answer = the approved storyboard's written steps with their source IDs, plus the lesson payload; skips the Verifier. Not approved or no match → the Care specialist answers (Verifier as usual) and the trace metadata gets `lesson_gap_topic` (a label, never the question text). The recorded route is the agent that actually answered (`lessons` only when an approved lesson was served).
- Add a `lessons` flag to `VERSIONS` (False for v1–v6) and an app version that equals the version the API uses plus `lessons: True`; the API uses it.
- API: `GET /api/lessons` (approved only, with `stage` filter), `GET /api/lessons/{lesson_id}`, `/media/lessons/{lesson_id}/{file}` (approved only), `lesson` field on `/api/ask` per the shared interface.
- Tests (mocked): routing to lessons, unapproved lesson falls back to Care, gap metadata without question text, media 404 for unapproved, Guardian still escalates a how-to with a danger sign before any lesson.

### Task 6: Little Lessons evaluation (§9.9) and notebook 08

- `evals/lessons_golden_v1.csv`: columns `case_id, input, expected_lesson_id (or none), expected_escalate (Y/N), label_status, notes`; 5 phrasings per lesson (different wording from `phrasings.yaml`), 6 how-to questions with no lesson (e.g. nail trimming), 3 how-tos with a danger sign (expect escalation). `label_status = draft` (Anand reviews before freezing).
- `evals/lessons_eval.py`: routing exact match (`library.match` vs expected), escalation for the danger-sign cases (`guardian.decide`), step fidelity (Nebius judge with a new `evals/lessons_judge_prompt.md`: storyboard scenes vs the source passages → missing steps, invented steps), checklist pass rate per scene from `review.yaml` (reports "pending human review" when unreviewed), cost and render time from `render_log.json` (reports "not rendered yet"). Export `evals/results/lessons_v1_<date>_summary.json` and cases CSV.
- `notebooks/08_little_lessons.ipynb`: build one storyboard (from saved files), show the pipeline, run the eval; execute it (live Haiku routing and Nebius judge allowed, budget about ₹20). Upload the dataset to LangSmith as `nestling-lessons-v1` and run in project `nestling-lessons`.
- Tests for the scoring functions.

### Task 7: Web foundation, Welcome, Today, Delete everything (Phase 5)

- Design tokens in `web/app/globals.css`, fonts via `next/font` (Fraunces, Inter), app layout with the disclaimer footer and bottom navigation (Today, Journeys, Lessons, Memory, Ask).
- `web/lib/api.ts`, `web/lib/store.ts` per the shared interfaces; shared components (`SourceChip`, `Card`, `WeekRing`, `JourneyCard`).
- `/welcome`: one gentle question per screen (due date or baby's birth date → tradition → food habits → city → insurer optional → parent role → explicit consent with what is stored where). `/` shows Today (or redirects to Welcome without a profile): week ring with fruit, one little moment with its source chip (`/api/today`), Ready meter from local checklist ticks, journey cards (🩺 Body · 🎒 Ready · 💰 Money · 🎉 Celebrate incl. 📸 Capture). `/settings` with **Delete everything** (clears browser state and deletes a cloned voice through the API if one exists).
- Placeholder pages for routes built in later tasks are fine (a calm "coming soon").
- Verify: `npm run lint` and `npm run build` pass; start the API and check Today renders real data from `/api/today`.

### Task 8: Ask sheet, How I answered, lesson card, Lessons library

- Ask bottom sheet reachable from every page: 🛡️ Guardian pulse (calm / amber / red from `guardian.level`), messages, source chips with page, collapsible "How I answered" (`how_i_answered`, `verification`), red-flag answers styled to stand out with the doctor message first, error state.
- Lesson answer card when `lesson` is present: video player (`video_url`, poster `thumbnail_url`), written steps with safety points, source chips, **Share on WhatsApp** (`https://wa.me/?text=` with the title and link). Without a lesson the normal answer shows.
- Journal save offer when `save` is true (stored in the browser).
- `/lessons` library (grid: thumbnail, title, "Reviewed on <date>"; stage filter: before birth · first weeks; empty state explaining lessons are published only after review) and `/lessons/[lessonId]` (player, steps, safety points, sources, share).
- Verify lint + build; check the sheet against the running API with a normal question and a red-flag question.

### Task 9: Journeys: Body, Ready, Money, Celebrate, Partner

- `/journeys` hub and pages: **Body** (common questions that open Ask prefilled; lessons for the current stage), **Ready** (checklist from `/api/checklist` with ticks stored in the browser, Ready meter, "Watch before baby arrives" lessons row), **Money** (policy PDF upload → `/api/policy/ask`, answers with exact quoted clauses and page numbers, clear note that the PDF is not stored), **Celebrate** (tradition playbook from `/api/celebrate/{tradition}`, invitation card from `/api/celebrate/invitation` rendered as a card with download as PNG, link to Capture), **Partner** ("What can I do this week?" from available data, bag duty, paperwork; questions open Ask prefilled).
- Verify lint + build; check each page against the running API.

### Task 10: Capture: photoshoot compare, estimate, quote approval

- `/celebrate/capture` per plan §3 screen 7: shoot type, city, budget and date form → `/api/capture/search`; a card per studio (price "as listed on the studio's site", checked-on date, rating summary, location, link; no copied photos); comparison table (total, cost per edited photo, duration, photos taken, edited copies, delivery, album, frames, casting; gaps read "Not listed — ask the studio"); **Estimate my budget** component picker → `/api/capture/estimate` with tier ranges, confidence, the low-data message, a "How we estimated" drawer and the approximate-estimate label; **Request quote** → `/api/capture/quote` draft shown for approval; only after the parent approves can they copy it or open WhatsApp/email; nothing is sent automatically. Saved package → "Photoshoot budget" card on Today and Celebrate (browser storage).
- Verify lint + build; check against the running API (Tavily calls allowed, keep to one or two searches).

### Task 11: Memory book, voice, shareable weekly card

- API: `POST /api/voice/transcribe` (ElevenLabs speech-to-text; audio processed in memory, never stored; tests mocked).
- `/memory`: text journal and **voice journal** (record up to a minute with MediaRecorder → transcribe → dated entry), **letters to baby** with "Read aloud" (`/api/voice/speak`, the parent's own voice if cloned), **own voice** setup with explicit consent (record a sample → `/api/voice/clone`; delete button → `DELETE /api/voice/{voice_id}`), all stored in the browser.
- **Shareable weekly card**: client-side canvas image (week, fruit, one fact with source, small Nestling mark) with download, Web Share API and WhatsApp share; no image model.
- **Partner view** link if not done in Task 9.
- Verify lint + build; tests for the transcribe endpoint.

### Task 12: Deploy readiness (no deploy)

- `render.yaml` for the API (uv, `uvicorn api.main:app`), web env `NEXT_PUBLIC_API_URL`, CORS from `NESTLING_WEB_ORIGINS`; update `.env.example` with every variable the code reads (no values).
- `tests/test_api.py`: FastAPI TestClient smoke tests for every route with paid calls mocked.
- README: run locally (API + web), deploy steps for Render and Vercel, the steps that need Anand (Pinecone `lessons` upsert, ffmpeg + rendering + review of lessons, judge calibration labels, Loom).
- Full check: `uv run pytest`, `npm run lint`, `npm run build`.
