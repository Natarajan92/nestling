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

Deployment and pushing require the owner's approval; neither is performed by these instructions.

- **Render API:** use `render.yaml`, Python 3.12.12, build `pip install uv && uv sync --locked --no-dev`, start `uv run --no-sync uvicorn api.main:app --host 0.0.0.0 --port $PORT`. Health check: `/api/health`. Automatic deploy triggers are off. Enter required secrets in Render and set `NESTLING_WEB_ORIGINS` to the Vercel origin.
- **Vercel web:** project root `web`, install/build using the lockfile; set `NEXT_PUBLIC_API_URL` to the Render API origin before building. Check API health, CORS, a sourced Ask answer, code-owned red-flag escalation, and approved lesson playback after release.
- **Lesson media:** renders are gitignored. Securely copy approved render folders to the API host while preserving storyboard/review versions; do not render or generate instructions on startup. Missing media means the library safely stays empty.

## Remaining owner work

The `lessons` namespace upsert is complete (45 phrasing records), and six explicitly authorized NHS bathing/burping source chunks were added. Further source writes need approval. On 2026-11-01 the owner approved every scene of bathing v1, burping v1, latching v2 and cord-care v4; their reviewed videos are available locally. Earlier latching v1 and cord-care v2 approvals remain historical after source corrections. Holding remains rejected; swaddling remains a source gap. Keep unapproved content hidden. Fill the report's 20-case judge calibration sheet, review the draft lesson-intent labels, record the Loom, and approve any push or deployment. Live eval commands cost money: saved notebooks make no paid calls by default.
