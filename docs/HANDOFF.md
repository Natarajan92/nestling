# Nestling: handoff checkpoint (2026-11-01)

Branch `feature/phase-3-improved`, local work only. Nothing pushed or deployed. Constitution: `docs/NESTLING_PLAN.md` §2; requirements: `specs/003-complete-app/plan.md`.

## Development status

| Task | State |
|---|---|
| 1–2: comparison, notebooks, Nebius migration | Complete; historical measurements preserved. |
| 3: report and README | Complete from final measured results. Human calibration labels remain blank. |
| 4: lesson build pipeline | Built/reviewed. Owner approved every scene in bathing v1, burping v1, latching v2 and cord-care v4 on 2026-11-01. Holding v2 rejected; swaddling has no supported storyboard. |
| 5: lesson runtime | Complete: routing, Care fallback, approval/media gate, API, 45 Pinecone phrasing records. |
| 6: lesson evaluation | Live routing 39/39, danger escalation 3/3; draft labels. Corrected storyboards receive separate fidelity verdicts; prior results retained. |
| 7–8: foundation, Welcome, Today, Settings, Ask, Lessons | Implemented/reviewed, including accessibility and deletion fixes. |
| 9: Journeys | All five, including stage/week-aware Partner, implemented. |
| 10: Capture | Compare, estimate, approved quote draft and saved budget implemented. Actual search returned three packages with source URLs/check date. |
| 11: Memory and voice | Journal, letters, transcription, own-voice consent/deletion and weekly cards implemented. |
| 12: deploy readiness | Render config, env template, CORS, memory-only uploads, route tests and instructions implemented; no deploy. |
| 13: quality round | Complete: default DeepSeek, guarded staged-vector retrieval, 104 cases and judge pass. GLM experiments remain explicitly incomplete/rejected. Faithfulness/latency targets still fail. |

Independent backend/web reviews, whole-branch review and scoped re-reviews passed after fixes. Application corrections are in local commits `443543f`, `0fea4fe`, `9a141eb` and `307b369`; eval/source/report completion is recorded in subsequent local commits. Nothing pushed or deployed.

## Verification and runtime

- Final controller checks: **251 Python tests**, **25 Node web tests**, lint and production build passed. Actual-SDK privacy tests and scoped corrections were independently reviewed.
- Actual API smoke passed **33 checks**, including all four approved videos/thumbnails and 404 for holding/swaddling. A real metered burping API request used the promoted app, returned the approved lesson and registered source, and skipped Verifier correctly. One real Capture search returned three studio packages.
- Browser inventory empty; in-app browser unavailable. Microphone, mobile playback, clipboard, native sharing and interactive visual QA remain unverified.
- App uses `v7_vector_safe+lessons`, default MAIN DeepSeek-V4-Pro, FAST DeepSeek-V4.1-Flash. It derives from the measured guarded vector base plus reviewed lessons; the exact lessons-enabled mode is not a full-set benchmark.
- App-only rerank-outage fallback records vector order explicitly. Historical variants remain strict; `v7_vector_safe` measures staged vector retrieval/final source guards with lessons disabled.
- Code escalation fixes preserve all frozen 104 Guardian decisions. Invalid verifier data and uncited clinical answers fail closed, including rewrites/empty retrieval. Policy partial-invalid quotes fail closed. App traces sanitize inputs, outputs and exceptions through a request-scoped client; Capture workers inherit it. Rule metadata is filtered/deduplicated to code-owned IDs. Browser deletion clears Ask and invalidates late clone/deletion responses; provider deletion 404 is idempotent.

Windows: use `npm.cmd` if scripts are blocked. Python sandbox tests need a writable `uv --cache-dir`, `run --no-sync pytest -p no:cacheprovider` and fresh `--basetemp`.

## Evaluation and budget checkpoint

Latest measured base `v7_vector_safe`: escalation/refusal **100%**, routing **94.23%**, citation **61.64%**, faithfulness **57/66 = 86.36%**, p95 **10.46s**, mean/p95 cost **INR0.743/INR1.508**. All104 pipeline cases succeeded; two persistent judge errors (F09/B13) remain excluded and counted separately. Faithfulness90% and latency8s targets still fail. Promotion follows the explicit plan gate: safety/refusal/routing hold and faithfulness beats historical v6's80.3%; even counting both judge errors false yields83.82%.

Owner approved up to INR226.16 additional for the full-set run; conservative shared cap INR249.99. Never reset `evals/results/phase3_v7_vector_spend.json` or discard unresolved reservations. Pre-fix vector run stopped at34 cases; GLM-safe stopped at60 because its verifier exhausted3000 output tokens with empty content. These are incomplete/failed model validations, not full results.

Final continuation ledger: **INR244.0804** accounted under249.99, comprising received-token cost220.5132 plus unresolved reservations23.5673. It includes discarded attempts, judging and the final approved-lesson API smoke. The default-model checkpoint reuses only19 unchanged Guardian/Concierge outputs; no clinical/Ready/Celebrate/Journal reuse across MAIN models. Fourteen zero-token rule outputs keep model=rules; immutable prior roots are retained alongside tagged metadata-correction replays. No model calls remain active.

The owner restored LangSmith capacity; a metadata-only trace was read back, cached H10 was replayed without another inference, and all104 latest case roots were verified before export. Original measured source hashes remain intact. Later app selection/rule metadata changes are explicitly documented as post-measurement changes, not a silent rewrite of the experiment.

Owner separately approved <=INR20 Little Lessons live evaluation and synthetic dataset/traces upload. See `lessons_v1_spend.json`; human labels stay pending. Narration costs are estimates when provider billing is unavailable.

## Lesson/release approvals

Old latching v1 and cord-care v2 approvals are historical. Source checking found a lower-lip/chin substitution and imprecise cord-care citations. The owner explicitly approved all scenes in corrected/current bathing1, burping1, latching2 and cord-care4. All four source checks pass; review-date videos were restitched using cached audio, verified with ffprobe, and published through the approval gate. Holding remains rejected and swaddling unpublished. `evals/results/lessons_review_pack_2026-11-01.json` preserves approval-time/final hashes and human reviews. Never infer future approval from a model score.

Authorized Pinecone writes completed:45 `lessons` phrasing records; one-time six source chunks (NHS-BABY-BATHING3, NHS-BABY-BURPING3), existing index, no deletes. All other source writes need approval. Holding needs a registered general-handling source explicitly supporting head/neck/shoulders; swaddling lacks practical source support. Do not invent steps or broaden breastfeeding guidance.

Remaining work: source and review holding/swaddling; draft lesson-label review;20-case judge calibration; browser QA; Loom; approval for further source writes, push or deployment. Fresh deployment has no gitignored renders and safely serves an empty library until reviewed media is copied. Current quality targets still need improvement before claiming a full rubric pass.

Concurrent owner edit in `playbooks/seemantham_tamilnadu.yaml` adds regional plate/rice practices. Preserve it outside agent commits. Recovery ledger/reports are in `.superpowers/sdd/plan/` (gitignored); do not restart completed tasks or delete evidence while work remains.
