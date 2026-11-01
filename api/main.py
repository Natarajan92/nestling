"""Nestling API (FastAPI): the web app's backend.

Privacy by design (constitution V): the server keeps no personal data. The profile, checklist
ticks, journal and letters live in the parent's browser and are sent with each request that
needs them; "Delete everything" clears the browser. Uploaded policies and voice samples are
processed in memory and never stored. App traces go to the LangSmith project `nestling-app`
with inputs and outputs hidden, so only the §9.4 metadata (route, rules, sources, cost) is kept.

    uv run uvicorn api.main:app --reload --port 8000
"""

import os

os.environ.setdefault("LANGSMITH_HIDE_INPUTS", "true")  # before langsmith is imported anywhere
os.environ.setdefault("LANGSMITH_HIDE_OUTPUTS", "true")

from dotenv import find_dotenv, load_dotenv  # noqa: E402

load_dotenv(find_dotenv(usecwd=True))

from datetime import date  # noqa: E402

from fastapi import FastAPI, File, Form, HTTPException, UploadFile  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import Response  # noqa: E402
from langsmith import get_current_run_tree, traceable  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from nestling import graph, profile  # noqa: E402
from nestling.agents import celebrate as celebrate_agent  # noqa: E402
from nestling.agents import ready as ready_agent  # noqa: E402
from nestling.capture import estimate as capture_estimate  # noqa: E402
from nestling.retrieval import load_registry  # noqa: E402
from nestling.schemas.studio_package import StudioPackage  # noqa: E402
from nestling.tracing import trace_metadata  # noqa: E402

APP_PROJECT = "nestling-app"
DISCLAIMER = ("Nestling offers general information from trusted sources and is not a substitute for medical advice. "
              "In an emergency, contact your doctor or the nearest hospital.")

app = FastAPI(title="Nestling API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("NESTLING_WEB_ORIGINS", "http://localhost:3000").split(","),
                   allow_methods=["*"], allow_headers=["*"])


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
    out = graph.ask(message, context, version="v6", can_save=can_save)
    run = get_current_run_tree()
    if run is not None:  # §9.4 metadata; labels and numbers only, no personal data
        run.add_metadata(trace_metadata(
            pipeline_version="v6", prompt_version=graph.PROMPT_VERSION, model=out["model"],
            predicted_escalate=out["escalate"], predicted_route=out["route"], refused=out["refused"],
            sources_cited=out["sources_cited"], latency_ms=out["latency_ms"], tokens_in=out["tokens_in"],
            tokens_out=out["tokens_out"], cost_inr=out["cost_inr"], error=out["error"]))
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
    }


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
async def policy_ask(question: str = Form(...), file: UploadFile = File(...)) -> dict:
    """Answer from the uploaded policy PDF with exact quotes and page numbers. Not stored."""
    from nestling.agents import policy

    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(400, "Please upload the policy as a PDF")
    pdf = await file.read()
    if len(pdf) > 20 * 1024 * 1024:
        raise HTTPException(413, "PDF too large (20 MB max)")
    return policy.ask_policy(question[:1000], pdf, langsmith_extra={"project_name": APP_PROJECT})


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
async def clone(consent: bool = Form(...), name: str = Form("My voice"), sample: UploadFile = File(...)) -> dict:
    """Create the parent's own voice from their sample. Own voice only, explicit consent."""
    from nestling import voice

    if not consent:
        raise HTTPException(400, "Voice cloning needs your explicit consent")
    return {"voice_id": voice.clone(name[:60], await sample.read(), sample.filename or "sample.mp3")}


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
