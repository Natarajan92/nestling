"""API contracts with external model, retrieval, search and voice calls mocked."""

import os
import subprocess
import sys

os.environ["LANGSMITH_TRACING"] = "false"

import pytest
import requests
from fastapi.testclient import TestClient
from starlette import formparsers

from api import main
from nestling import graph, voice
from nestling.agents import policy
from nestling.capture import search
from nestling.lessons import library
from nestling.schemas.studio_package import StudioPackage
from test_lessons_runtime import lesson_root  # noqa: F401


@pytest.fixture
def client():
    return TestClient(main.app)


def answer(**over):
    return {"answer": "Trusted answer", "escalate": False, "refused": False, "route": "care", "sources_cited": ["WHO-POSTNATAL"],
            "unsafe": [], "rules_fired": [], "steps": ["Guardian checked"], "verification": None, "error": None,
            "model": "rules", "latency_ms": 1, "tokens_in": 0, "tokens_out": 0, "cost_inr": 0,
            "agent": "care", "lesson": None, **over}


def test_static_routes_and_input_validation(client):
    assert client.get("/api/health").json()["ok"] is True
    assert "not a substitute" in client.get("/api/health").json()["disclaimer"]
    assert any(s["id"] == "WHO-POSTNATAL" for s in client.get("/api/sources").json())
    assert client.post("/api/today", json={}).status_code == 200
    checklist = client.get("/api/checklist").json()
    assert checklist["sections"][0]["items"][0]["id"] == "s0i0"
    assert client.get("/api/celebrate/tamil_nadu").status_code == 200
    assert client.get("/api/celebrate/unknown").status_code == 404
    assert client.post("/api/ask", json={"message": " "}).status_code == 400
    assert client.post("/api/today", json={"birth_date": "bad"}).status_code == 422


def test_invitation_is_template_text(client):
    response = client.post("/api/celebrate/invitation", json={"tradition": "tamil_nadu", "host_names": "Family", "date_text": "Sunday", "venue": "Home"})
    assert response.status_code == 200 and "Family" in response.json()["body"] and "Sunday" in response.json()["body"]


@pytest.mark.parametrize("tradition", ["tamil_nadu", "kerala", "karnataka"])
def test_all_celebration_playbooks_have_the_public_list_fields(client, tradition):
    result = client.get(f"/api/celebrate/{tradition}")
    assert result.status_code == 200
    for field in ("rituals", "checklist", "menu_ideas"):
        assert isinstance(result.json()[field], list)


def test_ask_selects_app_version_and_shared_lesson_payload(client, monkeypatch, lesson_root):
    def fake(message, context, version, can_save):
        assert version == "v7_vector_safe+lessons" and can_save is False
        assert "city" not in context and "insurer" not in context
        return answer(route="lessons", agent="lessons", lesson=library.payload("cord_care"))
    monkeypatch.setattr(graph, "ask", fake)
    response = client.post("/api/ask", json={"message": "how to clean the cord", "profile": {"city": "private", "insurer": "private"}})
    assert response.status_code == 200
    assert response.json()["lesson"] == client.get("/api/lessons/cord_care").json()


def test_ask_without_lesson_returns_null(client, monkeypatch):
    monkeypatch.setattr(graph, "ask", lambda *a, **kw: answer())
    assert client.post("/api/ask", json={"message": "question"}).json()["lesson"] is None


def test_gap_metadata_contains_labels_and_sanitized_error_only(monkeypatch):
    recorded = []
    class Run:
        def add_metadata(self, metadata): recorded.append(metadata)
    monkeypatch.setattr(main, "get_current_run_tree", lambda: Run())
    monkeypatch.setattr(graph, "ask", lambda *a, **kw: answer(lesson_gap_topic="holding", error="RuntimeError: private question"))
    main._app_ask("private question", {}, False)
    assert recorded[0]["lesson_gap_topic"] == "holding"
    assert "private question" not in str(recorded)


def test_lessons_list_detail_stage_and_media_gate(client, lesson_root):
    assert [x["lesson_id"] for x in client.get("/api/lessons").json()] == ["cord_care"]
    assert client.get("/api/lessons?stage=before_birth").json() == []
    assert client.get("/api/lessons?stage=first_weeks").json()[0]["version"] == 2
    assert client.get("/api/lessons?stage=anything").status_code == 422
    assert client.get("/media/lessons/cord_care/lesson.mp4").content == b"video"
    assert client.get("/media/lessons/cord_care/thumbnail.jpg").content == b"image"
    assert client.get("/media/lessons/cord_care/storyboard.json").status_code == 404
    review = lesson_root / "cord_care" / "review.yaml"
    review.write_text(review.read_text().replace("approved: true", "approved: false"))
    assert client.get("/api/lessons").json() == []
    assert client.get("/api/lessons/cord_care").status_code == 404
    assert client.get("/media/lessons/cord_care/lesson.mp4").status_code == 404
    assert client.get("/api/lessons/missing").status_code == 404


def test_policy_uses_bounded_memory_upload(client, monkeypatch):
    monkeypatch.setattr(policy, "ask_policy", lambda q, pdf, **kw: {"answer": q, "quotes": [], "bytes": len(pdf)})
    response = client.post("/api/policy/ask", data={"question": "policy cover"}, files={"file": ("policy.pdf", b"pdf", "application/pdf")})
    assert response.status_code == 200 and response.json()["bytes"] == 3
    assert client.post("/api/policy/ask", data={"question": "q"}, files={"file": ("x", b"x", "text/plain")}).status_code == 400


def test_voice_routes_with_explicit_consent(client, monkeypatch):
    monkeypatch.setattr(voice, "speak", lambda text, vid: b"mp3")
    monkeypatch.setattr(voice, "clone", lambda name, sample, filename: "clone-id")
    monkeypatch.setattr(voice, "delete", lambda vid: None)
    response = client.post("/api/voice/speak", json={"text": "Dear baby", "voice_id": "clone-id"})
    assert response.content == b"mp3" and response.headers["content-type"] == "audio/mpeg"
    file = {"sample": ("recording.webm", b"audio", "audio/webm")}
    assert client.post("/api/voice/clone", data={"consent": "false"}, files=file).status_code == 400
    assert client.post("/api/voice/clone", data={"consent": "true"}, files=file).json() == {"voice_id": "clone-id"}
    assert client.delete("/api/voice/clone-id").json() == {"deleted": "clone-id"}


def test_transcribe_is_multipart_memory_only_and_sanitizes_provider_errors(client, monkeypatch):
    def reject_rollover(*a, **kw):
        pytest.fail("audio spilled to disk")
    monkeypatch.setattr(formparsers.SpooledTemporaryFile, "rollover", reject_rollover)
    monkeypatch.setattr(voice, "transcribe", lambda audio, mime: f"{len(audio)} bytes")
    response = client.post("/api/voice/transcribe", files={"file": ("private-name.webm", b"a" * (2 * 1024 * 1024), "audio/webm")})
    assert response.status_code == 200 and response.json() == {"text": "2097152 bytes"}
    monkeypatch.setattr(voice, "transcribe", lambda *a: (_ for _ in ()).throw(requests.Timeout("private-name and content")))
    response = client.post("/api/voice/transcribe", files={"file": ("p.webm", b"audio", "audio/webm")})
    assert response.status_code == 502 and "private" not in response.text


@pytest.mark.parametrize("mime,data,status", [("text/plain", b"bad", 400), ("audio/webm", b"", 400),
                                              ("audio/webm", b"x" * (8 * 1024 * 1024 + 1), 413)])
def test_transcribe_rejects_bad_or_large_audio(client, monkeypatch, mime, data, status):
    monkeypatch.setattr(voice, "transcribe", lambda *a: pytest.fail("invalid upload reached provider"))
    assert client.post("/api/voice/transcribe", files={"file": ("x.webm", data, mime)}).status_code == status


def test_capture_routes_preserve_sources_and_never_send_quote(client, monkeypatch):
    package = StudioPackage(studio_name="Studio", shoot_type="maternity", price_inr=10000, edited_photos=10,
                            source_url="https://example.com/package", checked_on="2026-11-01")
    monkeypatch.setattr(search, "find_packages", lambda *a, **kw: [package])
    response = client.post("/api/capture/search", json={"city": "Bengaluru"})
    row = response.json()["packages"][0]
    assert row["total_cost"] == 10000 and row["cost_per_edited_photo"] == 1000
    assert row["source_url"] == "https://example.com/package"
    assert client.post("/api/capture/search", json={"shoot_type": "bad"}).status_code == 400
    estimate = client.post("/api/capture/estimate", json={"packages": [package.model_dump(mode="json")]})
    assert estimate.status_code == 200 and estimate.json()["tiers"]["All studios"]["estimate"] is None
    quote = client.post("/api/capture/quote", json={"studio": "Studio", "shoot_type": "maternity", "picks": {"album": True}}).json()
    assert quote["sent"] is False and "printed album" in quote["draft"]


def test_app_import_enforces_trace_privacy_even_with_false_shell_flags():
    script = ("import os; import api.main; "
              "assert os.environ['LANGSMITH_HIDE_INPUTS'] == 'true'; "
              "assert os.environ['LANGSMITH_HIDE_OUTPUTS'] == 'true'")
    result = subprocess.run([sys.executable, "-c", script], env={**os.environ, "LANGSMITH_TRACING": "false",
                             "LANGSMITH_HIDE_INPUTS": "false", "LANGSMITH_HIDE_OUTPUTS": "false"},
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr


def test_streamed_oversized_audio_is_rejected_before_disk_rollover(client, monkeypatch):
    monkeypatch.setattr(formparsers.SpooledTemporaryFile, "rollover", lambda *a: pytest.fail("upload rolled to disk"))
    monkeypatch.setattr(voice, "transcribe", lambda *a: pytest.fail("oversized stream reached provider"))
    def body():
        yield b'--test\r\nContent-Disposition: form-data; name="file"; filename="x.webm"\r\nContent-Type: audio/webm\r\n\r\n'
        for _ in range(10):
            yield b"x" * (1024 * 1024)
        yield b"\r\n--test--\r\n"
    response = client.post("/api/voice/transcribe", headers={"Content-Type": "multipart/form-data; boundary=test"}, content=body())
    assert response.status_code == 413


def test_missing_audio_and_malformed_multipart_reject_without_provider(client, monkeypatch):
    monkeypatch.setattr(voice, "transcribe", lambda *a: pytest.fail("invalid upload reached provider"))
    assert client.post("/api/voice/transcribe", json={"file": "not audio"}).status_code == 400
    assert client.post("/api/voice/transcribe", files={"sample": ("x.webm", b"audio", "audio/webm")}).status_code == 422
    assert client.post("/api/voice/transcribe", headers={"Content-Type": "multipart/form-data"}, content=b"bad").status_code == 400
