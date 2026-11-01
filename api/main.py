"""Nestling API (FastAPI): the web app's backend.

Privacy by design (constitution V): the server keeps no personal data. The profile, checklist
ticks, journal and letters live in the parent's browser and are sent with each request that
needs them; "Delete everything" clears the browser. Uploaded policies and voice samples are
processed in memory and never stored. App traces go to the LangSmith project `nestling-app`
with inputs and outputs hidden, so only the §9.4 metadata (route, rules, sources, cost) is kept.

    uv run uvicorn api.main:app --reload --port 8000
"""

import os

os.environ["LANGSMITH_HIDE_INPUTS"] = "true"  # app privacy applies even when the shell says false
os.environ["LANGSMITH_HIDE_OUTPUTS"] = "true"

from dotenv import find_dotenv, load_dotenv  # noqa: E402

load_dotenv(find_dotenv(usecwd=True))

from datetime import date  # noqa: E402
from functools import cache  # noqa: E402
from typing import Literal  # noqa: E402

from fastapi import FastAPI, HTTPException, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse, Response  # noqa: E402
from langsmith import Client, get_current_run_tree, traceable, tracing_context  # noqa: E402
from pydantic import BaseModel  # noqa: E402
from starlette.concurrency import run_in_threadpool  # noqa: E402

from api.uploads import AUDIO_TYPES, MAX_AUDIO_BYTES, MAX_POLICY_BYTES, memory_form, read_file  # noqa: E402
from nestling import graph, profile  # noqa: E402
from nestling.agents import celebrate as celebrate_agent  # noqa: E402
from nestling.agents import ready as ready_agent  # noqa: E402
from nestling.capture import estimate as capture_estimate  # noqa: E402
from nestling.lessons import LESSONS, library  # noqa: E402
from nestling.retrieval import load_registry  # noqa: E402
from nestling.schemas.studio_package import StudioPackage  # noqa: E402
from nestling.tracing import trace_metadata  # noqa: E402

APP_PROJECT = "nestling-app"
DISCLAIMER = ("Nestling offers general information from trusted sources and is not a substitute for medical advice. "
              "In an emergency, contact your doctor or the nearest hospital.")

app = FastAPI(title="Nestling API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=[s.strip() for s in os.getenv("NESTLING_WEB_ORIGINS", "http://localhost:3000").split(",") if s.strip()],
                   allow_methods=["*"], allow_headers=["*"])


def _redact_app_error(fields: dict) -> dict:
    # LangSmith hides inputs/outputs independently of exceptions. Its anonymizer
    # receives error strings wrapped in this dict for both create and update.
    return {key: "pipeline_error" if key == "error" and value else value for key, value in fields.items()}


@cache
def app_trace_client() -> Client:
    """A separate export policy; never change the cached evaluation client."""
    return Client(hide_inputs=True, hide_outputs=True, anonymizer=_redact_app_error)


@app.middleware("http")
async def private_app_traces(request: Request, call_next):
    # ContextVars propagate through FastAPI's thread pool and LangGraph's nested
    # calls. Parent=False also prevents an ambient eval run selecting its client.
    with tracing_context(client=app_trace_client(), parent=False, project_name=APP_PROJECT,
                         metadata=trace_metadata()):
        try:
            return await call_next(request)
        except Exception:
            # Provider errors can echo private prompts/documents. The sanitized
            # nested trace retains the failure; the response/log path gets none.
            return JSONResponse(status_code=502, content={"detail": "Request unavailable. Please try again."})


class ProfileIn(BaseModel):
    due_date: date | None = None
    birth_date: date | None = None
    tradition: str | None = None
    diet: str | None = None
    city: str | None = None
    insurer: str | None = None
    parent_role: str = "mother"

    def model(self) -> profile.PregnancyProfile:
        return profile.PregnancyProfile.from_dict(self.model_dump())


def _source_chip(source_id: str, page: str | None = None) -> dict:
    s = load_registry().get(source_id, {})
    return {"id": source_id, "title": s.get("title"), "publisher": s.get("publisher"), "year": s.get("year"),
            "url": s.get("url") or s.get("pdf"), "page": page}


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "disclaimer": DISCLAIMER}


@app.get("/api/sources")
def sources() -> list[dict]:
    """The trusted library, for source chips (public fields only)."""
    return [_source_chip(sid) for sid, s in load_registry().items() if s.get("file") or s.get("url")]


@app.post("/api/today")
def today(p: ProfileIn) -> dict:
    """Week ring, baby size, today's sourced tip, and which journey cards to show."""
    st = profile.stage(p.model())
    tip = profile.tip_for(st)
    cards = ["body", "ready", "money", "celebrate"]
    return {
        "stage": st,
        "tip": {**tip, "source_chip": _source_chip(tip["source"], tip["page"])} if tip else None,
        "cards": cards,
        "tradition_card": bool(p.tradition and p.tradition != "other" and st.get("life_stage") == "pregnancy"),
        "disclaimer": DISCLAIMER,
    }


class AskIn(BaseModel):
    message: str
    profile: ProfileIn = ProfileIn()
    can_save: bool = False


@traceable(name="nestling_app_ask", run_type="chain")
def _app_ask(message: str, context: dict, can_save: bool) -> dict:
    out = graph.ask(message, context, version=graph.APP_VERSION, can_save=can_save)
    run = get_current_run_tree()
    if run is not None:  # §9.4 metadata; labels and numbers only, no personal data
        run.add_metadata(trace_metadata(
            pipeline_version=graph.APP_VERSION, prompt_version=graph.PROMPT_VERSIONS[graph.APP_VERSION], model=out["model"],
            predicted_escalate=out["escalate"], predicted_route=out["route"], refused=out["refused"],
            sources_cited=out["sources_cited"], latency_ms=out["latency_ms"], tokens_in=out["tokens_in"],
            tokens_out=out["tokens_out"], cost_inr=out["cost_inr"], error="pipeline_error" if out["error"] else None,
            lesson_gap_topic=out.get("lesson_gap_topic") if out.get("lesson_gap_topic") in {*LESSONS, "newborn_care"} else None,
            retrieval_mode=out.get("retrieval_mode"),
            retrieval_fallback="vector_order" if out.get("retrieval_fallback") == "vector_order" else None))
    return out


@app.post("/api/ask")
def ask(body: AskIn) -> dict:
    """Ask Nestling: Guardian -> Concierge -> specialist -> Verifier, with "How I answered"."""
    if not body.message.strip():
        raise HTTPException(400, "Empty message")
    p = body.profile.model()
    st = profile.stage(p)
    context = {"week": st.get("week"), "diet": p.diet, "tradition": p.tradition, "parent_role": p.parent_role,
               "life_stage": st.get("life_stage")}
    out = _app_ask(body.message[:2000], context, body.can_save, langsmith_extra={"project_name": APP_PROJECT})
    pages: dict[str, list[str]] = {}
    for psg in out.get("passages", []):
        if psg["source_id"] in out["sources_cited"] and psg.get("page_label"):
            pages.setdefault(psg["source_id"], []).append(str(psg["page_label"]))
    chips = [_source_chip(sid, ", ".join(dict.fromkeys(pages.get(sid, []))) or None) for sid in out["sources_cited"]]
    level = "red" if out["escalate"] else "amber" if out["unsafe"] else "calm"
    return {
        "answer": out["answer"], "escalate": out["escalate"], "refused": out["refused"], "route": out["route"],
        "guardian": {"level": level, "rules_fired": out["rules_fired"], "unsafe": out["unsafe"]},
        "sources": chips, "how_i_answered": out["steps"], "verification": out["verification"],
        "save": bool(out.get("agent") == "journal" and body.can_save), "error": bool(out["error"]),
        "lesson": out.get("lesson"),
        "retrieval_fallback": out.get("retrieval_fallback"),
    }


@app.get("/api/lessons")
def lessons(stage: Literal["before_birth", "first_weeks"] | None = None) -> list[dict]:
    """The reviewed library only; absent rendered content stays absent."""
    return [item for lesson in library.approved() if (item := library.payload(lesson["lesson_id"]))
            and (stage is None or item["stage"] == stage)]


@app.get("/api/lessons/{lesson_id}")
def lesson_detail(lesson_id: str) -> dict:
    item = library.payload(lesson_id)
    if item is None:
        raise HTTPException(404, "Lesson unavailable")
    return item


@app.get("/media/lessons/{lesson_id}/{filename}")
def lesson_media(lesson_id: str, filename: str) -> FileResponse:
    if filename not in {"lesson.mp4", "thumbnail.jpg"} or library.payload(lesson_id) is None:
        raise HTTPException(404, "Lesson unavailable")
    path = library.get(lesson_id)["folder"] / "renders" / filename
    if not path.is_file():
        raise HTTPException(404, "Media unavailable")
    return FileResponse(path, media_type="video/mp4" if filename == "lesson.mp4" else "image/jpeg",
                        headers={"Cache-Control": "no-store"})


@app.get("/api/checklist")
def checklist() -> dict:
    """The labour bag checklist (code-owned), each item with a stable id and its source chip."""
    data = ready_agent.checklist()
    sections = []
    for s_i, section in enumerate(data["sections"] + [{"name": "After birth", "items": data["after_birth"]}]):
        items = []
        for i_i, item in enumerate(section["items"]):
            chip = _source_chip(item["source"], item.get("page")) if item["source"] != "common_practice" else None
            items.append({"id": f"s{s_i}i{i_i}", "item": item["item"], "source": chip})
        sections.append({"name": section["name"], "items": items})
    return {"title": data["title"], "when": data["when"], "sections": sections}


@app.get("/api/celebrate/{tradition}")
def celebrate(tradition: str) -> dict:
    if tradition not in celebrate_agent.FILES:
        raise HTTPException(404, "Unknown tradition")
    return celebrate_agent.playbook(tradition)


class InvitationIn(BaseModel):
    tradition: str
    host_names: str
    mother_name: str | None = None
    date_text: str
    time_text: str | None = None
    venue: str


@app.post("/api/celebrate/invitation")
def invitation(body: InvitationIn) -> dict:
    """Invitation card text from a template (no LLM, no data stored)."""
    if body.tradition not in celebrate_agent.FILES:
        raise HTTPException(404, "Unknown tradition")
    book = celebrate_agent.playbook(body.tradition)
    ceremony = book["also_called"][0]
    for_whom = f" for {body.mother_name}" if body.mother_name else ""
    when = body.date_text + (f", {body.time_text}" if body.time_text else "")
    return {"title": f"You're invited to our {ceremony}", "ceremony": ceremony,
            "body": (f"With joy and blessings, {body.host_names} invite you to the {ceremony}{for_whom}.\n\n"
                     f"{when}\n{body.venue}\n\nYour presence and blessings will make the day complete."),
            "tradition": book["tradition"]}


# --- Money: questions about the parent's own policy (exact clauses, Phase 10) ---------------

@app.post("/api/policy/ask")
async def policy_ask(request: Request) -> dict:
    """Answer from the uploaded policy PDF with exact quotes and page numbers. Not stored."""
    from nestling.agents import policy

    async with memory_form(request, MAX_POLICY_BYTES) as form:
        question = form.get("question")
        if not isinstance(question, str) or not question.strip():
            raise HTTPException(422, "Question is required")
        pdf, _ = await read_file(form, "file", MAX_POLICY_BYTES, {"application/pdf", "application/octet-stream"})
        return await run_in_threadpool(policy.ask_policy, question[:1000], pdf, langsmith_extra={"project_name": APP_PROJECT})


# --- Voice: letters to baby read aloud (Phase 9) --------------------------------------------

class SpeakIn(BaseModel):
    text: str
    voice_id: str | None = None  # the parent's own cloned voice, only with explicit consent


@app.post("/api/voice/speak")
def speak(body: SpeakIn) -> Response:
    from nestling import voice

    audio = voice.speak(body.text[:2500], body.voice_id)
    return Response(content=audio, media_type="audio/mpeg")


@app.post("/api/voice/clone")
async def clone(request: Request) -> dict:
    """Create the parent's own voice from their sample. Own voice only, explicit consent."""
    from nestling import voice

    async with memory_form(request, MAX_AUDIO_BYTES) as form:
        if form.get("consent") != "true":
            raise HTTPException(400, "Voice cloning needs your explicit consent")
        name = form.get("name", "My voice")
        if not isinstance(name, str):
            raise HTTPException(422, "Invalid voice name")
        sample, mime = await read_file(form, "sample", MAX_AUDIO_BYTES, AUDIO_TYPES)
        extension = {"audio/webm": "webm", "audio/ogg": "ogg", "audio/mp4": "mp4", "audio/mpeg": "mp3", "audio/wav": "wav", "audio/x-wav": "wav"}[mime]
        return {"voice_id": await run_in_threadpool(voice.clone, name[:60], sample, f"sample.{extension}")}


@app.post("/api/voice/transcribe")
async def transcribe(request: Request) -> dict:
    """A journal recording in memory; transcript persistence belongs to the browser."""
    from nestling import voice

    async with memory_form(request, MAX_AUDIO_BYTES) as form:
        audio, mime = await read_file(form, "file", MAX_AUDIO_BYTES, AUDIO_TYPES)
        try:
            text = await run_in_threadpool(voice.transcribe, audio, mime)
        except Exception:
            raise HTTPException(502, "Transcription unavailable. Please try again.") from None
    return {"text": text}


@app.delete("/api/voice/{voice_id}")
def delete_voice(voice_id: str) -> dict:
    from nestling import voice

    voice.delete(voice_id)
    return {"deleted": voice_id}


# --- Capture: photoshoot planner (Phase 8) --------------------------------------------------

class CaptureSearchIn(BaseModel):
    city: str = "Bengaluru"
    shoot_type: str = "maternity"


@app.post("/api/capture/search")
def capture_search(body: CaptureSearchIn) -> dict:
    from nestling.capture.search import SHOOT_QUERIES, find_packages

    if body.shoot_type not in SHOOT_QUERIES:
        raise HTTPException(400, "Unknown shoot type")
    packages = find_packages(body.city[:60], body.shoot_type, langsmith_extra={"project_name": APP_PROJECT})
    rows = []
    for p in packages:
        rows.append({**p.model_dump(mode="json"),
                     "total_cost": capture_estimate.total_cost(p),
                     "cost_per_edited_photo": capture_estimate.cost_per_edited_photo(p)})
    return {"packages": rows, "checked_on": date.today().isoformat(), "note": "Prices as listed on each studio's site."}


class EstimateIn(BaseModel):
    packages: list[StudioPackage]
    album: bool = False
    frames: int = 0
    casting: bool = False


@app.post("/api/capture/estimate")
def capture_estimate_route(body: EstimateIn) -> dict:
    return capture_estimate.estimate_cost(body.packages, album=body.album, frames=body.frames, casting=body.casting)


class QuoteIn(BaseModel):
    studio: str
    shoot_type: str
    picks: dict
    date_text: str | None = None
    city: str | None = None


@app.post("/api/capture/quote")
def capture_quote(body: QuoteIn) -> dict:
    """A draft only. Nestling never sends it; the parent copies or opens it themselves after approving."""
    return {"draft": capture_estimate.quote_request(body.studio, body.shoot_type, body.picks, body.date_text, body.city),
            "sent": False}
