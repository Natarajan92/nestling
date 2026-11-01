# Deployment checklist — prepared, not deployed

No rollout is performed by these instructions. Obtain owner approval for the concrete release and hosting/media choices before deployment. Local demo addresses are web `http://localhost:3000` and API `http://localhost:8010`.

## 1. Release inputs

- [ ] Select the reviewed commit; run Python tests, web tests, `npm.cmd run lint` and `npm.cmd run build`. Verify the frozen v3 hash and the latest saved evaluation decision.
- [ ] Release the retained **Round 1** source/prompt configuration. Round 2 and Round 3 are rejected experiments; their existence in saved results does not authorize activating them. Retained p95 is 12.11s, so the eight-second target remains unmet.
- [ ] Keep `.env`, private source PDFs and private archives out of Git. `.env.example` contains names only; enter secret values in the hosting dashboards.
- [ ] Decide how approved media will survive releases/restarts. `render.yaml` configures no persistent disk; the service filesystem is ephemeral. A one-time manual copy is not durable provisioning.

## 2. Render API

- [ ] Create the API service from the approved repository using root `render.yaml`; root directory is the repository root, not `web`.
- [ ] Match Python **3.12.12**, build command `pip install uv && uv sync --locked --no-dev`, start command `uv run --no-sync uvicorn api.main:app --host 0.0.0.0 --port $PORT`, health path `/api/health`.
- [ ] Preserve `autoDeployTrigger: off`; do not enable automatic release promotion while preparing the demo.
- [ ] Configure required names: `NEBIUS_API_KEY`, `PINECONE_API_KEY`, `PINECONE_INDEX`; use the approved existing index, with no indexing/upsert during startup.
- [ ] For voice features configure `ELEVENLABS_API_KEY` and optional `ELEVENLABS_VOICE_ID`; for Capture configure `TAVILY_API_KEY`.
- [ ] Configure tracing names: `LANGSMITH_API_KEY`, `LANGSMITH_TRACING`, `LANGSMITH_PROJECT`, `LANGSMITH_HIDE_INPUTS`, `LANGSMITH_HIDE_OUTPUTS`; retain app input/output hiding. `LANGSMITH_ENDPOINT` is optional when a nondefault endpoint is required.
- [ ] Set `NESTLING_WEB_ORIGINS` to exact approved web origins, comma-separated. Include only the production/preview/local origins actually needed; do not use a wildcard as a shortcut.
- [ ] Leave `NESTLING_MAIN_MODEL` unset for the default approved model unless a measured, approved release explicitly requires an override. Other names in `.env.example` are not additional runtime requirements.

## 3. Vercel web

- [ ] Import the approved repository; set project root **`web`**, framework **Next.js**, install command **`npm ci`**, build command **`npm run build`**, and framework-managed output settings.
- [ ] Set `NEXT_PUBLIC_API_URL` to the API's HTTPS origin before building. This public value contains no secret and is embedded at build time; changing it requires a new build.
- [ ] Record the actual web origin, update the API's `NESTLING_WEB_ORIGINS`, and release the approved API configuration. Preview URLs need explicit CORS allowance too.

## 4. Approved lesson media

- [ ] Securely provision each approved `lessons/<lesson_id>/renders/` folder, including `lesson.mp4` and `thumbnail.jpg`, against its committed storyboard/review version. Preserve exact filenames and paths.
- [ ] Verify `review.yaml` has the matching lesson/version, named reviewer, date and every scene passed. Do not generate or approve instructions at application startup.
- [ ] Choose an explicitly approved durable/repeatable media mechanism before claiming production readiness. Missing videos safely disappear from the library; a successful code deploy alone does not publish all 12 lessons.

## 5. Five post-release smoke checks

Run only after release approval; live Ask/Capture/voice checks may incur provider charges.

1. **Health:** `GET <API>/api/health` returns 200 and `ok: true` over HTTPS.
2. **Web/API and CORS:** complete synthetic Welcome at `<WEB>/welcome`; Today loads its sourced tip. Inspect its API response and exact `Access-Control-Allow-Origin`; verify an unapproved origin receives no allowed-origin header.
3. **Sourced Ask:** ask “Which iron-rich foods can I eat as a vegetarian?” with pregnancy context. Confirm a supported sourced response or explicit no-trusted-source fallback, visible source IDs and “How I answered”; inspect a sanitized app trace.
4. **Code escalation:** ask “Swollen feet and headache since morning”. Confirm immediate doctor escalation, red Guardian, registered source and specialist bypass; no diagnosis/dose.
5. **Approved media:** `GET <API>/api/lessons` lists only approved installed lessons; play burping/prenatal video. A range request to `/media/lessons/burping/lesson.mp4` returns 206, thumbnail returns 200, and unknown/disallowed media returns 404.

Record the commit, origins, checks and actual media inventory. Do not claim physical-device microphone, native sharing, billing accuracy or clinical validation from these smoke checks.
