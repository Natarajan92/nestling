"""ElevenLabs contracts, all HTTP mocked."""

import pytest
import requests

from nestling import voice


def test_transcribe_uses_in_memory_multipart_and_returns_only_text(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    def post(url, **kw):
        assert url == "https://api.elevenlabs.io/v1/speech-to-text"
        assert kw["files"]["file"] == ("recording.webm", b"audio", "audio/webm")
        assert kw["data"]["model_id"] == "scribe_v2" and kw["timeout"] == 120
        class Response:
            def raise_for_status(self): pass
            def json(self): return {"text": "A memory", "words": [{"speaker_id": "x"}]}
        return Response()
    monkeypatch.setattr(voice.requests, "post", post)
    assert voice.transcribe(b"audio", "audio/webm") == "A memory"


def test_transcribe_propagates_provider_failure(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    monkeypatch.setattr(voice.requests, "post", lambda *a, **kw: (_ for _ in ()).throw(requests.Timeout("private data")))
    with pytest.raises(requests.Timeout):
        voice.transcribe(b"audio", "audio/webm")
