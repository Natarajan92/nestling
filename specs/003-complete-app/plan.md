> Current evaluation supersedes the original task briefs below: frozen `evals/golden_v3.csv` (62 cases), `evals.v3_run`, and `docs/week4_report.md`. Retired Ask artifacts are no longer active. Owner authorization in the session governs publication.

# Plan: Complete Nestling (Phases 3 close-out → 10)

**Spec:** `docs/NESTLING_PLAN.md` (the constitution in §2 overrides everything). Repo rules: `CLAUDE.md`.
**Branch:** `feature/phase-3-improved` (work in place; commit locally; never push).
**Out of scope (human work):** Loom recording, real medical review of lessons, Toloka (Phase 12), domain and permissions, deploying, Pinecone writes other than the approved `lessons` namespace upsert.

## Global Constraints

- The constitution (plan §2) overrides everything: red-flag escalation decided in code (`nestling/guardian.py`), never by an LLM alone; no medicine doses or diagnoses, ever; every medical/diet/insurance answer cites a source ID from `sources/registry.yaml` or says *"I don't have a trusted source for that. Please ask your doctor."*
- Little Lessons (constitution rule 8): safety-critical how-tos are pre-generated and human-reviewed, never generated live per question; every step comes from a registered source; illustration style only, baby always covered (nappy, towel or clothes); every lesson has a safety checklist including *"image matches narration"*; an unapproved video is never shown; no approved video → written sourced steps only (Care + Verifier) and the gap is logged; live image generation only for fun content.
- Models (owner decision 2026-11-01: no Anthropic API at runtime; Nebius or Fireworks wherever possible): `MAIN = deepseek-ai/DeepSeek-V4-Pro` on Nebius (specialists, verifier, storyboards, policy Q&A, journal) and `FAST = deepseek-ai/DeepSeek-V4.1-Flash` on Nebius (guardian classifier, concierge, lesson matching, Capture extraction), both through one shared OpenAI-compatible client in `nestling/llm.py` (traced with `langsmith.wrappers.wrap_openai`). The judge stays `Qwen/Qwen3-235B-A22B-Instruct-2507` on Nebius (`evals/judge.py`, judge-v1): a different model family from the pipeline, so all faithfulness numbers stay comparable. Embeddings and rerank stay on Pinecone's hosted models (`llama-text-embed-v2`, `bge-reranker-v2-m3`).
- `evals/golden_v3.csv` is FROZEN (hash-locked in `nestling/golden.py`). Never edit it. Existing pipeline versions v1–v5 in `nestling/graph.py` must keep their behaviour (results already published).
- Privacy: no personal data in traces (§9.4 metadata only; app traces hide inputs/outputs). The server stores no personal data: profile, checklist ticks, journal, letters and voice ID live in the browser. Uploaded files and audio are processed in memory, never stored.
- Logic lives in `.py`, notebooks only import and display. Python 3.12 + `uv`. Tests with `pytest`; tests never call paid APIs (mock them).
- Keep it light: no new frameworks or abstractions beyond what the task needs. Web: Next.js 16 (read `web/AGENTS.md` and the guides in `web/node_modules/next/dist/docs/` before writing Next code), React 19, Tailwind 4, `motion`. No new UI component libraries.
- Design language (plan §3): cream `#FFF8F1` background · peach `#F7B49A` · blush `#EFA3B5` · sage `#9CB89A` · ink `#2E2A3A` · gold `#E8B65A`; Fraunces for display, Inter for body; 24px radii, soft shadows, generous whitespace; gentle motion; mobile-first. Calm and warm; alarming only for red flags.
- Disclaimer shown in the app: *"Nestling offers general information from trusted sources and is not a substitute for medical advice. In an emergency, contact your doctor or the nearest hospital."*
- Commits: as the configured git user, with NO `Co-Authored-By` trailer and no AI attribution. Never push. Never commit keys (`.env` is gitignored).
- Paid API calls are allowed only where a task says so, within its stated budget.

## Shared interfaces (fixed here so tasks agree)

- **Storyboard** `lessons/<lesson_id>/storyboard.json`: `{"lesson_id", "title", "version" (int), "stage" ("before_birth"|"first_weeks"), "language": "en", "sources": [source_id...], "see_how": null | {"label", "url", "publisher"}, "scenes": [{"step_no", "caption" (≤ 8 words), "narration_line", "icon" (name from the vendored icon set), "source_id", "page_label", "safety_points": [..]}]}` with 4–5 step scenes. `see_how` is a hand-curated link to a trusted external video (never filled by a model).
- **Checklist** `lessons/<lesson_id>/checklist.yaml`: `{lesson_id, items: [str]}` (always includes "Card and icon match the narration").
- **Phrasings** `lessons/<lesson_id>/phrasings.yaml`: `{lesson_id, phrasings: [str]}`.
- **Review** `lessons/<lesson_id>/review.yaml`: `{lesson_id, version, approved: false, reviewer: null, review_date: null, scenes: [{step_no, passed: null, notes: ""}]}`.
- **Renders** `lessons/<lesson_id>/renders/` (gitignored): `card_<n>.png` (title, steps, closing), `card_<n>.mp3`, `lesson.mp4`, `thumbnail.jpg`, `render_log.json` (`{cost_inr, seconds, rendered_at}`).
- **Approved** = `review.yaml` has `approved: true`, `version` equals the storyboard version, every scene `passed: true`, and `renders/lesson.mp4` exists.
- **API lesson payload** (used by `/api/lessons`, `/api/lessons/{id}` and the `lesson` field of `/api/ask`): `{"lesson_id", "title", "version", "stage", "video_url", "thumbnail_url", "steps": [{"step_no", "caption", "narration_line", "icon", "safety_points"}], "sources": [source chip], "see_how": null | {"label", "url", "publisher"}, "reviewed_on"}`. Media served at `/media/lessons/{lesson_id}/{lesson.mp4|thumbnail.jpg}` for approved lessons only (404 otherwise). `/api/ask` returns `"lesson": null` when no approved lesson was served.
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

### Task 2: Move every runtime LLM call to Nebius open models, with the faithfulness fix (v6), and re-run

- **Shared client** `nestling/llm.py`: `MAIN`, `FAST` model IDs (see Global Constraints), one cached OpenAI-compatible client for Nebius (`NEBIUS_API_KEY`, base URL `https://api.tokenfactory.nebius.com/v1/`, as in `evals/judge.py`) wrapped with `wrap_openai`; a `chat_json(model, system, user, schema, max_tokens)` helper returning `(parsed_or_None, usage, raw_text)` with JSON-schema structured output (fall back to JSON mode + validation if a model rejects `json_schema`; check this live with one tiny call per model), and usage in the existing `{"model", "tokens_in", "tokens_out", ...}` shape. Add `openai` as a dependency if missing.
- **Replace every Anthropic call** with it: `nestling/agents/__init__.py` (`sonnet_json` → MAIN), `nestling/verifier.py` (MAIN), `nestling/guardian.py` classifier (FAST; keep the verbatim-quote verification in code), `nestling/concierge.py` (FAST), `nestling/agents/journal.py` and any other specialist call (MAIN), `nestling/capture/search.py` extraction (FAST), and `nestling/agents/policy.py` (MAIN): Claude's PDF citations go away, so read the PDF pages in memory with `pypdf`, give the model page-numbered text, require exact quoted clauses with page numbers, and verify every quote appears verbatim on its page in code (drop any that don't; if none survive, say no clause was found). `nestling/baseline.py` stays as the Phase 2 record (used only by baseline/v1 experiments). Remove Anthropic prompt-caching code paths from the runtime; keep `anthropic` installed only for `baseline.py`.
- **Costs:** add the Nebius per-token prices for MAIN and FAST to `nestling/tracing.py` (`PRICE_USD_PER_MTOK`) from Nebius's public pricing page (note the date and URL in a comment); `graph.run_info` and the `model` field report the open models.
- **Faithfulness fix:** keep the uncommitted strict-verifier change already in the working tree (`verifier-v3`, `verify(..., strict=...)`, `tests/test_verifier.py`) — it targets the v4→v5 regressions in `evals/results/phase3_failure_analysis.json`. `v6` = v5 levers + strict verifier + open models; `PROMPT_VERSIONS["v6"]` as already added. v1–v5 results stay as recorded (they were measured on Claude); say so in `graph.py`'s docstring.
- Mocked unit tests for `llm.chat_json` (schema path and fallback), the policy quote verification, and that no runtime module imports `anthropic` except `baseline.py`. Existing tests keep passing.
- **Docs:** update the models line in `CLAUDE.md`, and the model mentions in `docs/NESTLING_PLAN.md` §4 agent table and §5 tool stack (Claude API row → Nebius open models; judge stays Qwen on Nebius).
- **Run:** check one red-flag case and one Care case end to end (`graph.run_one`), then `graph.run_experiment("v6")` on the frozen set and `evals/judge.py::judge_experiment` on it; export with the same file naming as v1–v5, add v6 to `phase3_experiments.json` and `phase3_judge_round1.json`, add v6 to notebook 06 and re-execute it. **Budget:** one full v6 run plus its judge pass (≤ ₹250). If errors occur, re-run only failing cases.
- **App version:** the API (`api/main.py`, currently `"v5"`) must not call Anthropic, so it moves to v6. Report v6 against the pass bars honestly, including any regression versus v5.

### Task 3: Week 4 package (Phase 4) and README

- `docs/week4_report.md`: the §9.1 one-liner, framework table, metrics and rubric with pass bars, baseline vs improved (v1…v6) with deltas and regressions reported honestly, top 3 failure modes with case IDs, the judge (model, prompt path, outputs), human-vs-judge agreement, LangSmith experiment names, executed notebooks list, production monitoring (§9.6), and a 6-bullet Loom outline (use case → dataset → a failure → fixes → results). Keep it short and factual; numbers come from `evals/compare.py` output, not retyped by hand.
- Human-vs-judge agreement needs Anand's labels: export a calibration sheet with `evals/judge.py::calibration_sheet` (20 cases from the latest run) and mark agreement as *pending Anand's labels* with the exact command to compute it (`evals/judge.py::agreement`). Do not invent labels.
- README: one-liner, eval headline table (baseline vs best), how to run tests/API/web.
- Plan §9: add an "Improved result" note under the baseline note (same style), tick the §9.7 items that are done.

### Task 4: Little Lessons build pipeline (step-card videos)

Owner decision 2026-11-01: no image model. Each lesson is an attractive ~15-second **step-card video** built in code from the sourced storyboard; where a trusted external video exists, the lesson also carries a "See how it's done" link-out (`see_how`).

- `nestling/lessons/` with `__init__.py`, `storyboard.py`, `cards.py`, `narrate.py`, `stitch.py`, `library.py`, and a `render.py` CLI (`uv run python -m nestling.lessons.render <lesson_id>`: cards → narration → stitch → `render_log.json`).
  - `storyboard.py`: retrieve passages from the registered sources (`nestling.retrieval.search_reranked`, Pinecone reads only) for the lesson topic; MAIN (`nestling/llm.py`) writes 4–5 step scenes in the storyboard schema (caption ≤ 8 words, one narration line per step, an `icon` chosen from the vendored icon list, `source_id` + `page_label`, safety points). Validate in code: every `source_id`/`page_label` pair comes from the retrieved passages; icon names exist; no doses, no diagnoses. If the passages do not support the steps, return `no_trusted_source` and write nothing. CLI: `uv run python -m nestling.lessons.storyboard <lesson_id>`.
  - `cards.py`: draw the title card, one card per step and a closing card (sources + "Reviewed on <date>" or "Pending review") as 1080×1920 (9:16) images in the §3 palette: per-step background tone, large Fraunces step number, Inter step line, one big icon on a soft blob shape, a gold "Safety" pill with the step's first safety point, progress dots, small Nestling wordmark. Calm, warm, polished — it must look good enough to share. Vendor only what is used: Fraunces and Inter font files (SIL OFL, licence files included) under `assets/fonts/`, and the needed Phosphor icons (MIT, licence included) under `assets/icons/`. Rendering approach is the builder's call (e.g. SVG rasterised with ffmpeg/librsvg or a small rasteriser, or Pillow) as long as fonts and icons render crisply; no new framework. Look at the rendered PNGs yourself before moving on.
  - `narrate.py`: ElevenLabs narration per card (reuse `nestling/voice.py`), returning each clip's length.
  - `stitch.py`: pure `build_command(...)` producing the ffmpeg command — each card shown for its narration's length plus a short pause (min ~2 s), slow zoom, soft slide/fade transitions, narration captions burned in, total about 12–20 s, H.264 + AAC MP4 with faststart, `thumbnail.jpg` from the title card — and `stitch()` that runs it with a clear error if ffmpeg is missing (Gyan.FFmpeg 9.0.2 is installed via winget; it may live under `%LOCALAPPDATA%\Microsoft\WinGet\Links`). No music.
  - `library.py`: load lessons from `lessons/`, `approved()`, `get(lesson_id)`, `is_approved(lesson_id)` per the shared-interface definition.
- `lessons/<lesson_id>/checklist.yaml`, `phrasings.yaml` (6–8 phrasings each) and `review.yaml` (`approved: false`) for the six lessons: `holding`, `bathing`, `burping`, `swaddling`, `latching`, `cord_care` (bathing/holding checklist items from constitution rule 8, plus "Card and icon match the narration" in all). `see_how` (hand-curated, link-out only, never embedded): bathing → NHS "How should I bath my baby?" `https://www.nhs.uk/best-start-in-life/baby/baby-basics/caring-for-your-baby/bathing-your-baby/`; latching → Global Health Media Project "Breastfeeding Attachment" `https://globalhealthmedia.org/video/breastfeeding-attachment-hindi/` (Hindi); others null. Add `lessons/*/renders/` to `.gitignore`.
- Generate storyboards for all six (MAIN calls, budget about ₹30) and render every lesson that has a storyboard (ElevenLabs narration allowed, a few rupees per lesson). Commit storyboards and YAML files (not renders); report lessons without a trusted source as gaps (do not invent steps). Renders stay unapproved until a human reviews them.
- **Docs:** update `docs/NESTLING_PLAN.md` to match — constitution rule 8 visuals line (step cards with icons; no generated or photographic images of babies), §4 "how a lesson is made" and the build-time flow, §5 (no image model for lessons; ElevenLabs narration; ffmpeg), §7 (`cards.py`, `render.py`, `assets/`), §15 (image-model decision resolved: step-card videos, no image model; trusted link-outs where they exist). Product facts only.
- `tests/test_lessons.py` with mocked LLM/HTTP: storyboard validation (bad source/page rejected, unknown icon rejected, step count), card rendering produces 1080×1920 images, `build_command`, approval rules.

### Task 5: Little Lessons at runtime (routing, library, API)

- `nestling/lessons/library.py`: `match(question) -> {"lesson_id": str | None, "topic": str}` using FAST (`nestling/llm.py`) as a closed-set classifier over all known lessons (titles + phrasings as examples, plus "none"); `index_phrasings(dry_run=True)` that prepares records for the Pinecone namespace `lessons` in the existing index (integrated embedding, same record fields style as `nestling/retrieval.py`); with `dry_run=False` it upserts them (owner approved 2026-11-01): run it once for the six lessons after the dry run looks right.
- Concierge: add route `lessons` (practical newborn-care how-tos) with few-shot examples. Graph: a lessons node after the Concierge: matched and approved → answer = the approved storyboard's written steps with their source IDs, plus the lesson payload; skips the Verifier. Not approved or no match → the Care specialist answers (Verifier as usual) and the trace metadata gets `lesson_gap_topic` (a label, never the question text). The recorded route is the agent that actually answered (`lessons` only when an approved lesson was served).
- Add a `lessons` flag to `VERSIONS` (False for v1–v6) and an app version that equals the version the API uses plus `lessons: True`; the API uses it.
- API: `GET /api/lessons` (approved only, with `stage` filter), `GET /api/lessons/{lesson_id}`, `/media/lessons/{lesson_id}/{file}` (approved only), `lesson` field on `/api/ask` per the shared interface.
- Tests (mocked): routing to lessons, unapproved lesson falls back to Care, gap metadata without question text, media 404 for unapproved, Guardian still escalates a how-to with a danger sign before any lesson.

### Task 6: Little Lessons evaluation (§9.9) and notebook 08

- `evals/lessons_golden_v1.csv`: columns `case_id, input, expected_lesson_id (or none), expected_escalate (Y/N), label_status, notes`; 5 phrasings per lesson (different wording from `phrasings.yaml`), 6 how-to questions with no lesson (e.g. nail trimming), 3 how-tos with a danger sign (expect escalation). `label_status = draft` (Anand reviews before freezing).
- `evals/lessons_eval.py`: routing exact match (`library.match` vs expected), escalation for the danger-sign cases (`guardian.decide`), step fidelity (Nebius judge with a new `evals/lessons_judge_prompt.md`: storyboard scenes vs the source passages → missing steps, invented steps), checklist pass rate per scene from `review.yaml` (reports "pending human review" when unreviewed), cost and render time from `render_log.json` (reports "not rendered yet"). Export `evals/results/lessons_v1_<date>_summary.json` and cases CSV.
- `notebooks/08_little_lessons.ipynb`: build one storyboard (from saved files), show the pipeline, run the eval; execute it (live FAST routing and Nebius judge allowed, budget about ₹20; cost and render time come from the real render_log.json files). Upload the dataset to LangSmith as `nestling-lessons-v1` and run in project `nestling-lessons`.
- Tests for the scoring functions.

### Task 7: Web foundation, Welcome, Today, Delete everything (Phase 5)

- Design tokens in `web/app/globals.css`, fonts via `next/font` (Fraunces, Inter), app layout with the disclaimer footer and bottom navigation (Today, Journeys, Lessons, Memory, Ask).
- `web/lib/api.ts`, `web/lib/store.ts` per the shared interfaces; shared components (`SourceChip`, `Card`, `WeekRing`, `JourneyCard`).
- `/welcome`: one gentle question per screen (due date or baby's birth date → tradition → food habits → city → insurer optional → parent role → explicit consent with what is stored where). `/` shows Today (or redirects to Welcome without a profile): week ring with fruit, one little moment with its source chip (`/api/today`), Ready meter from local checklist ticks, journey cards (🩺 Body · 🎒 Ready · 💰 Money · 🎉 Celebrate incl. 📸 Capture). `/settings` with **Delete everything** (clears browser state and deletes a cloned voice through the API if one exists).
- Placeholder pages for routes built in later tasks are fine (a calm "coming soon").
- Verify: `npm run lint` and `npm run build` pass; start the API and check Today renders real data from `/api/today`.

### Task 8: Ask sheet, How I answered, lesson card, Lessons library

- Ask bottom sheet reachable from every page: 🛡️ Guardian pulse (calm / amber / red from `guardian.level`), messages, source chips with page, collapsible "How I answered" (`how_i_answered`, `verification`), red-flag answers styled to stand out with the doctor message first, error state.
- Lesson answer card when `lesson` is present: vertical video player (`video_url`, poster `thumbnail_url`), a swipeable strip of the step cards (caption, icon, safety points), source chips, a "See how it's done" link when `see_how` is set (opens the external page in a new tab), **Share on WhatsApp** (`https://wa.me/?text=` with the title and link). Without a lesson the normal answer shows.
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

### Task 13: v7 quality round on the open models (owner decision 2026-11-01)

v6 (DeepSeek on Nebius) holds safety and halves cost but fails faithfulness (80.3% vs the 90% bar) and citation match fell to 57.5% (wrong source family 18 → 28). One measured improvement round, run in parallel with the app work.

- Diagnose from the committed v6 results with `evals/compare.py` (`failure_modes("v6")`, `faithfulness_regressions("v5", "v6")`); write `evals/results/phase3_v7_diagnosis.json`.
- **Lever A — life-stage source routing:** pick each specialist's retrieval sources by the parent's life stage (pregnancy → antenatal sources; postpartum/newborn → WHO-POSTNATAL, MOHFW-IYCF, MOHFW-MAA, INDIA-UIP …) using the existing `context["life_stage"]`/week, in code (`nestling/retrieval.py::sources_for` and the agents), with unit tests. Registry sources only.
- **Lever B — MAIN model bake-off:** on a fixed 20-case subset of the frozen set (the v6 faithfulness/citation failures plus 5 passing controls; list the case IDs in the diagnosis file), compare DeepSeek-V4-Pro (current), `moonshotai/Kimi-K3` and `zai-org/GLM-5.3` on Nebius — never a Qwen model (the judge's family) — judged by the existing Qwen judge. Pick by faithfulness, then citation match, then cost; record the table.
- `v7` = v6 + the levers that helped (new `VERSIONS`/`PROMPT_VERSIONS` entries; v1–v6 unchanged). Full run on the frozen set + judge, exports, `phase3_experiments.json`, `phase3_judge_round1.json`, notebook 06 re-executed.
- The API moves to v7 only if escalation 100%, refusal 100%, routing ≥ 90% hold and faithfulness beats v6; otherwise it stays on v6. Report honestly either way.
- Budget ≤ ₹150 for the whole task (subset bake-off + one full run + judging).
- Parallel work note: another implementer owns `nestling/lessons/`, `assets/`, `lessons/`, `docs/NESTLING_PLAN.md`, `.gitignore` and `web/`; do not touch them; commit by explicit paths.
