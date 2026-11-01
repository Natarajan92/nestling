# Engineering notes

Operational companion to the [README](../README.md), [v3 report](v3_evaluation_report.md), [demo script](loom_script.md) and [deployment checklist](deploy_checklist.md).

## Safety and privacy

Code in `nestling/guardian.py` owns escalation. A classifier can propose a quoted signal; code validates it, and an LLM cannot remove a matched danger sign. Directly matched emergency cases bypass models. No medicine doses or diagnoses are allowed. Medical, diet and insurance answers must cite registered sources or explicitly say a trusted source is unavailable.

The server stores no parent profile, journal, policy or voice recording. Profile, checklist, journal, letters and saved packages live in browser keys prefixed `nestling:`. Uploaded policy/audio bytes are processed in memory. “Delete everything” clears browser data and requests deletion of a cloned voice when present. Provider processing is distinct from local storage; obtain consent before voice cloning.

App LangSmith traces use a request-scoped client with hidden inputs/outputs and sanitized exceptions. Metadata contains closed IDs, routes, rules, sources, timing, usage and errors. Owner-authorized evaluation traces contain synthetic/benchmark case evidence; do not reuse that export policy for personal app requests.

## Runtime, sources and lessons

Python 3.12 + uv; Next.js 16 web. Local demo: API **8010**, web **3000**. Set `NEXT_PUBLIC_API_URL` explicitly to the API before starting/building web; source defaults must not select another running backend accidentally.

The app's selected version is `graph.APP_VERSION`; its prompt/model/flags and per-round code hashes are the measurement authority. MAIN is Nebius `deepseek-ai/DeepSeek-V4-Pro`; FAST is `deepseek-ai/DeepSeek-V4.1-Flash`. The separate judge is Nebius `Qwen/Qwen3-235B-A22B-Instruct-2507`; keep Qwen out of the pipeline family. No Anthropic API is used by the current app.

Sources live in `sources/registry.yaml`. Registration is not permission to ingest: citation-only sources have `ingest_allowed: false`. Private PDFs remain gitignored. Use source/page evidence; a registered ID alone does not establish that a clinical claim is supported. Further Pinecone writes require owner approval; source reads do not authorize indexing.

The 12 locally approved lessons comprise six newborn topics and six prenatal topics. Approval is exact-version and scene-based: matching storyboard/review lesson ID and version, reviewer/date, all scenes passed, and installed MP4. Source-fidelity checks support review but never replace it. Renders are gitignored; a clean clone can correctly show an empty library until approved media is provisioned.

The library serves existing written scenes/video, never newly generated safety instructions per request. Missing/unapproved lesson matches fall back to sourced Care. Cards use original code-drawn icons; no generated or photographic baby images. Narration/caption limits are 20/8 words; complete approved narration is preserved or rendering fails.

## V3 measurement and budget

`evals/golden_v3.csv` is the only active Ask set: 62 owner-attested own questions and owner-reviewed expectations, frozen by normalized SHA256. The latest authorship attestation is not independently verified. Do not change questions or expected labels during iteration; changes need a new version.

All 62 cases remain the regression and promotion gate. The 40-case submission view is a deterministic stratified presentation, not another active dataset or unseen benchmark. Compare paired judgments on the same case IDs and report zero-claim replies, abstentions, judge errors, task fulfillment, false escalations and citation diagnostics alongside headline rates.

`evals/v3_run.py` owns a new shared **INR 350** cap across baseline, judging and improvement rounds. `evals/results/golden_v3/spend.json` records request accounting and unresolved reservations. Resume retains completed outputs; errors do not authorize resetting the ledger. Plans, checkpoints, provenance and decisions must remain attached to the measured round.

Final accounting is **INR 183.9041 / 350**, with no pending reservations. Baseline and all three rounds completed 62 cases with verified traces and no pipeline errors. **Round 1 is retained**: faithfulness 32/35 valid, task completion 52/62, p95 12.11 seconds, mean pipeline cost INR 0.719. Round 2 (90-word prompt) and Round 3 (compact verifier) were rejected; preserve their measurements and restore the retained source/prompt configuration. Use paired comparisons to assess improvement, since eligible faithfulness denominators change.

Provider price evidence is saved in `evals/results/golden_v3/pricing.json`; report INR conversion is a fixed **94.91** comparison estimate, not a statement of current FX or a reconciled provider invoice. Pipeline answer cost excludes offline judging and discarded attempts; the shared ledger accounts for those separately.

Human calibration remains **0/20** until a person labels saved actual answers in `evals/results/golden_v3/human_review.csv`; Loom remains pending. Expected-label review, source-fidelity judging and lesson approval do not fill these labels. Use the saved local review context; keep source excerpts private and compute agreement only from entered human decisions.

Known constraints include previously exposed questions, remaining source-verification markers, B11 requiring USER-POLICY without an uploaded PDF, and E09 allowing either route while its behavior asks for both topics. Preserve these limitations and current failures. Selected Round 1 meets the valid-judgment faithfulness threshold but still misses the eight-second latency target; it is not an all-pass or clinical-validation claim.

## Verification and publication

Final checks: **373 Python tests and 39 web tests passed**, along with ESLint and the production build. [Current QA evidence](../evals/results/golden_v3/qa/summary.json) records commands/status; [media smoke](../evals/results/golden_v3/qa/media_smoke.json) confirms all 12 approved videos and thumbnails are served locally. These checks do not certify physical devices or public hosting.

**Open development dependency advisory:** [GHSA-g3hv-75wg-m249](https://github.com/isaacs/minimatch/security/advisories/GHSA-g3hv-75wg-m249) affects the minimatch lint dependency chain. Production-only `npm audit --omit=dev` reports zero vulnerabilities; full audit still reports this advisory across development dependencies. Compatible upstream ESLint/TypeScript ESLint dependencies have no automatic fix; forcing minimatch 11 over callable 3.x breaks callers. Keep the alert open, use trusted repository glob patterns, and update when compatible fixes land. This is a bounded dependency check, not a comprehensive security certification.

[Saved UI QA](../evals/results/ui_qa_2026-11-01.json) records browser/mobile-width coverage and a separate prenatal extension. It does not certify physical devices, real microphone permissions, native sharing or clipboard. Test counts and live costs belong to their dated evidence; do not present an old count as a new run.

Old Ask result files and retired generators were privately archived and removed from the publication tree at the owner's request. Private archives and their closed budgets must stay ignored; the current v3 ledger remains part of the saved evidence. GitHub history cleanup must operate on a verified backup and use explicit refs/leases; closed PR refs and cached commit/diff pages can retain earlier objects despite rewritten branch history. Do not promise complete remote erasure from a normal force-push.

No deployment is implied by repository publication, test success or this checklist. Keep secrets in local/host configuration, keep automatic rollout off, and obtain approval for the concrete deployment and media persistence plan.
