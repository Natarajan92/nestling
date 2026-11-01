# Nestling
From bump to baby. Every answer, sourced.

A calm companion for first-time parents in India. Medical, diet and insurance answers cite registered sources; code owns danger-sign escalation. Little Lessons appear only after the current storyboard has a human scene review and approved media.

| Version | Escalation | Refusal | Routing | Citation | Faithfulness | p95 s | Mean ₹ | p95 ₹ |
|---|---|---|---|---|---|---|---|---|
| baseline | 100.0% | 97.1% | 84.6% | 78.1% | 89.3% | 8.57 | 1.305 | 1.502 |
| v7_vector_safe | 100.0% | 100.0% | 94.2% | 61.6% | 86.4% | 10.46 | 0.743 | 1.508 |

The measured forced-vector base is `v7_vector_safe` (DeepSeek on Nebius): faithfulness 86.4%, up from v6's 80.3%, and p95 latency 10.46s, down from 14.53s. It still misses the 90% faithfulness and 8s latency targets; 2 judge errors are counted separately. Baseline is a historical Claude measurement. The app uses `v7_vector_safe+lessons`, adding human-reviewed lesson routing to this measured base; the exact lessons-enabled configuration has not been measured on the full golden set. Original strict-reranked v7 and the incomplete GLM attempts are not full-set results.

See the [short Week 4 report](docs/week4_report.md), [evaluation comparison](notebooks/06_eval_compare.ipynb), [Little Lessons notebook](notebooks/08_little_lessons.ipynb), [plan](docs/NESTLING_PLAN.md), and [source registry](sources/registry.yaml).

## Run locally

Use Python 3.12, uv, and Node.js 20.9 or newer. Copy `.env.example` to `.env` and fill the keys locally; never commit values.

```powershell
uv sync --locked
uv run uvicorn api.main:app --reload
```

In another terminal:

```powershell
cd web
npm ci
$env:NEXT_PUBLIC_API_URL = "http://localhost:8000"
npm run dev
```

Tests and production build:

```powershell
uv run pytest
cd web
npm run lint
npm run build
```

In a restricted Windows sandbox use a fresh pytest `--basetemp`, `-p no:cacheprovider`, and a writable `uv --cache-dir` with `run --no-sync`.

The API needs `NEBIUS_API_KEY`, `PINECONE_API_KEY`, and `PINECONE_INDEX` (the existing `nestling-sources` index). Voice uses `ELEVENLABS_API_KEY` and optionally `ELEVENLABS_VOICE_ID`; Capture uses `TAVILY_API_KEY`. LangSmith uses its key, tracing/project/endpoint settings; app trace inputs and outputs are hidden. Set `NESTLING_WEB_ORIGINS` to actual allowed web origins. Profile, journal, checklist and saved packages stay in browser keys prefixed `nestling:`; uploaded PDFs and audio are processed in memory.

## Deploy readiness

The owner authorized GitHub publication and merge to main for this completed release. No app deployment has been performed, and deployment still requires approval.

- **Render API:** use `render.yaml`, Python 3.12.12, build `pip install uv && uv sync --locked --no-dev`, start `uv run --no-sync uvicorn api.main:app --host 0.0.0.0 --port $PORT`. Health check: `/api/health`. Automatic deploy triggers are off. Enter required secrets in Render and set `NESTLING_WEB_ORIGINS` to the Vercel origin.
- **Vercel web:** project root `web`, install/build using the lockfile; set `NEXT_PUBLIC_API_URL` to the Render API origin before building. Check API health, CORS, a sourced Ask answer, code-owned red-flag escalation, and approved lesson playback after release.
- **Lesson media:** renders are gitignored. Securely copy approved render folders to the API host while preserving storyboard/review versions; do not render or generate instructions on startup. Missing media means the library safely stays empty.

## Remaining owner work

All 12 current videos are available locally after explicit owner approval of every exact-version scene on 2026-11-01. The original six and six prenatal videos pass source fidelity; earlier reviews and failed verdicts remain historical. Builds permit 20-word narration and 8-word captions, preserving full burned-in narration text or failing clearly.

The new before-birth videos cover labour-room preparation, prenatal yoga preparation, relaxed breathing, bed movement, stair comfort (v2) and gentle activity for birth. Eight new sources are citation-only local research PDFs; 37 new phrasings stay local. The original 45 Pinecone phrasing records and six authorized NHS bathing/burping source chunks are unchanged; further writes need approval. Historical 39-case intent results cover the original six-topic prompt, not the expanded 12-topic app prompt.

[Headless browser QA](evals/results/ui_qa_2026-11-01.json) covers 120 listed mobile/desktop scenarios and 242 client navigations; the Ask crash, Kerala menu crash and misleading outage states were fixed. A separate 22-check publication extension verified all six new videos playing in both viewports, stage filters and Body/Ready links; final HTTP smoke passed 43 checks for all 12 lessons. Nine real API checks also passed: the original Care/lesson/emergency cases plus all six prenatal lesson routes. Physical devices, real microphone/native sharing, judge calibration, draft intent labels, Loom and app deployment approval remain pending. GitHub publication/merge is authorized for this release. Saved notebooks make no paid calls; explicit live evaluations cost money.
