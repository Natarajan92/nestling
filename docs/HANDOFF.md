# Nestling: handoff checkpoint (2026-11-01)

Branch `feature/phase-3-improved`. The owner authorized GitHub publication and merge to main for this completed release. No app deployment has been performed. Constitution: `docs/NESTLING_PLAN.md` §2; requirements: `specs/003-complete-app/plan.md`.

## Development status

| Task | State |
|---|---|
| 1–2: comparison, notebooks, Nebius migration | Complete; historical measurements preserved. |
| 3: report and README | Complete from final measured results. Human calibration labels remain blank. |
| 4: lesson build pipeline | Complete. Owner approved every scene of bathing v1, burping v1, latching v2, cord-care v4, holding v3 and swaddling v5 on 2026-11-01. All six pass source fidelity and are published through the local approval gate. The six prenatal lessons also have exact-version owner approval and verified review-date media; all 12 are published through the local approval gate. |
| 5: lesson runtime | Complete: routing, Care fallback, approval/media gate and API. App-only v2 prompt covers 12 topics; 37 new phrasings remain local, original 45 Pinecone records unchanged. |
| 6: lesson evaluation | Historical original-six-topic v1 routing 39/39 and escalation 3/3 unchanged; draft labels. No 12-topic intent accuracy claim. Six new prenatal fidelity checks pass; earlier stairs v1 False is preserved. |
| 7–8: foundation, Welcome, Today, Settings, Ask, Lessons | Implemented/reviewed, including accessibility and deletion fixes. |
| 9: Journeys | All five, including stage/week-aware Partner, implemented. Owner-authorized optional Tamil Nadu plate/rice practices reviewed; actual API returned 200. |
| 10: Capture | Compare, estimate, approved quote draft and saved budget implemented. Actual search returned three packages with source URLs/check date. |
| 11: Memory and voice | Journal, letters, transcription, own-voice consent/deletion and weekly cards implemented. |
| 12: deploy readiness | Render config, env template, CORS, memory-only uploads, route tests and instructions implemented; no deploy. |
| 13: quality round | Complete: default DeepSeek, guarded staged-vector retrieval, 104 cases and judge pass. GLM experiments remain explicitly incomplete/rejected. Faithfulness/latency targets still fail. |

Independent backend/web reviews, whole-branch review and scoped re-reviews passed after fixes. Application corrections are in local commits `443543f`, `0fea4fe`, `9a141eb` and `307b369`; eval/source/report completion is recorded in subsequent local commits. GitHub publication and merge are authorized for this release; no app deployment.

## Verification and runtime

- Final controller checks: **271 Python tests**, **39 Node web tests**, lint and production build passed. Actual-SDK privacy tests and scoped corrections were independently reviewed. Current lesson/renderer checks passed 56 focused tests and independent review; the full suite passed after the closing-card layout fix. One existing deprecation warning remains.
- Final actual HTTP smoke passed **43 checks** for all 12 exact lesson versions, review dates/source chips, ranged MP4 responses (206), JPEG thumbnails (200), stage filters (6+6) and 404 for unknown/disallowed media. Earlier 25/33-check runs remain historical. Nine unmocked API QA cases passed, and the earlier actual Capture search returned three sourced studio packages.
- Headless Chrome QA passed 120 listed scenarios across 390x844/1440x1000 with 242 same-document client navigations, including the six original lesson detail pages; new prenatal detail pages are outside this matrix. A separate publication extension passed 22 checks/34 further client navigations: Body 6/Ready 12 links, filters, all six new detail pages and 12 advancing muted playback observations across both viewports, with no JavaScript error or guard escape. The final focused 50/50 run had no JavaScript errors or paid-route guard escapes. Ask Promise-cleanup, Kerala optional-menu and outage/Retry defects are fixed. Paid browser endpoints were mocked; the separate real API check passed 9/9 (registered-source Care, approved burping, code escalation and all six expected prenatal lesson IDs). See `evals/results/ui_qa_2026-11-01.json`. Physical devices, real microphone/native clipboard/sharing remain unverified.
- App uses `v7_vector_safe+lessons`, default MAIN DeepSeek-V4-Pro, FAST DeepSeek-V4.1-Flash. Its app-only prompt is `app-v7-vector-safe-lessons-v2-prenatal`; lesson-disabled historical versions are unchanged. It derives from the measured guarded vector base plus reviewed lessons; the exact lessons-enabled mode is not a full-set benchmark.
- App-only rerank-outage fallback records vector order explicitly. Historical variants remain strict; `v7_vector_safe` measures staged vector retrieval/final source guards with lessons disabled.
- Code escalation fixes preserve all frozen 104 Guardian decisions. Invalid verifier data and uncited clinical answers fail closed, including rewrites/empty retrieval. Policy partial-invalid quotes fail closed. App traces sanitize inputs, outputs and exceptions through a request-scoped client; Capture workers inherit it. Rule metadata is filtered/deduplicated to code-owned IDs. Browser deletion clears Ask and invalidates late clone/deletion responses; provider deletion 404 is idempotent.

Windows: use `npm.cmd` if scripts are blocked. Python sandbox tests need a writable `uv --cache-dir`, `run --no-sync pytest -p no:cacheprovider` and fresh `--basetemp`.

## Evaluation and budget checkpoint

Latest measured base `v7_vector_safe`: escalation/refusal **100%**, routing **94.23%**, citation **61.64%**, faithfulness **57/66 = 86.36%**, p95 **10.46s**, mean/p95 cost **INR0.743/INR1.508**. All104 pipeline cases succeeded; two persistent judge errors (F09/B13) remain excluded and counted separately. Faithfulness90% and latency8s targets still fail. Promotion follows the explicit plan gate: safety/refusal/routing hold and faithfulness beats historical v6's80.3%; even counting both judge errors false yields83.82%.

Owner approved up to INR226.16 additional for the full-set run; conservative shared cap INR249.99. Never reset `evals/results/phase3_v7_vector_spend.json` or discard unresolved reservations. Pre-fix vector run stopped at34 cases; GLM-safe stopped at60 because its verifier exhausted3000 output tokens with empty content. These are incomplete/failed model validations, not full results.

Final continuation ledger: **INR244.0804** accounted under249.99, comprising received-token cost220.5132 plus unresolved reservations23.5673. It includes discarded attempts, judging and the final approved-lesson API smoke. The default-model checkpoint reuses only19 unchanged Guardian/Concierge outputs; no clinical/Ready/Celebrate/Journal reuse across MAIN models. Fourteen zero-token rule outputs keep model=rules; immutable prior roots are retained alongside tagged metadata-correction replays. No model calls remain active.

The owner restored LangSmith capacity; a metadata-only trace was read back, cached H10 was replayed without another inference, and all104 latest case roots were verified before export. Current holding v3/swaddling v5 judge roots were also read back with complete metadata, no errors and hidden inputs/outputs. The quality ledger is unchanged and the frozen 104-case golden hash still verifies. Original measured source hashes remain intact. Later app selection/rule metadata changes are explicitly documented as post-measurement changes, not a silent rewrite of the experiment.

Owner separately approved <=INR20 Little Lessons live evaluation and synthetic dataset/traces upload. Current cumulative evaluation spend is INR1.8918; the 39 routing results are unchanged and all six original saved storyboards pass cross-family fidelity checks. See `lessons_v1_spend.json`; human labels stay pending. Holding narration is estimated at INR4.92 and swaddling at INR12.60 cumulatively, tracked separately from both the lesson evaluation and unchanged INR244.0804 quality ledger. Provider narration billing is unavailable.

Prenatal judge trace labels now distinguish before-birth content from newborn care. Seven immutable original LangSmith roots remain preserved; seven zero-inference cached metadata-correction roots were read back with the proper prenatal labels. Fidelity verdicts and costs are unchanged.

New prenatal work uses separate ledgers: narration estimate INR55.32/65, Qwen fidelity INR0.3609/5 and nine real API checks INR1.8927/10; combined INR57.5736 under the owner's INR80 cap. The INR244.0804 quality ledger and original INR1.8918 lesson-evaluation ledger are unchanged. No new Pinecone writes were made.

## Lesson/release approvals

Old latching v1 and cord-care v2 approvals are historical. Source checking found a lower-lip/chin substitution and imprecise cord-care citations. The owner explicitly approved all scenes in corrected/current bathing1, burping1, latching2 and cord-care4. Their review-date videos were restitched using cached audio, verified with ffprobe, and published through the approval gate. General holding v3 and complete swaddling v5 now pass source checks and cross-family fidelity evaluation; the owner explicitly approved every scene of these exact versions on 2026-11-01. Their review-date cards were refreshed using cached audio, both final videos were verified, and the six original lessons are published through the local approval gate. Holding is 20.3s; swaddling is 31.6s. Raw earlier verdicts, including swaddling v3/v4 False results, remain preserved; v5's precision fixes passed independent source/visual review. `evals/results/lessons_review_pack_2026-11-01.json` preserves approval-time/final hashes and human reviews. Never infer future approval from a model score.

The six new before-birth lessons cover labour-room preparation, prenatal yoga preparation, relaxed breathing, bed movement, stair comfort and gentle activity for birth. All current source/fidelity checks pass; stairs is v2 and its earlier False verdict remains preserved. All six exact-version scene approvals are recorded, their review-date videos are verified, and all 12 lessons are published through the local approval gate. The approval-date refresh reused cached audio with no additional provider calls. Eight new registered sources have ingest_allowed:false and private research PDFs; existing MOHFW-ANC remains a registered source where used.

Authorized Pinecone writes completed:45 `lessons` phrasing records; one-time six source chunks (NHS-BABY-BATHING3, NHS-BABY-BURPING3), existing index, no deletes. All other source writes need approval. Holding uses registered NHS-RWT-HOLDING general cradle guidance; swaddling uses NSW-SCHN-SWADDLING. Both are citation-only, ingest_allowed:false: private local research PDFs supply build evidence, never Pinecone. No breastfeeding instruction is generalized. Narration permits 20 words and captions 8; the renderer preserves full narration text within its strip or fails clearly. These build-only changes do not require or imply a new clinical benchmark.

Remaining work: draft lesson-label review;20-case judge calibration; physical-device/native integration QA; Loom; approval for further source writes or app deployment. Fresh deployment has no gitignored renders and safely serves an empty library until reviewed media is copied. Current quality targets still need improvement before claiming a full rubric pass.

The owner explicitly authorized optional Tamil Nadu 7/11/21-plate and five-varieties-of-rice practices in `playbooks/seemantham_tamilnadu.yaml`; implementation was independently reviewed and the actual Celebrate API returned 200. Recovery ledger/reports are in `.superpowers/sdd/plan/` (gitignored); do not restart completed tasks or delete evidence while work remains.
