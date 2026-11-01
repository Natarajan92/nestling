"""Voice: letters to baby read aloud, optionally in the parent's own voice (ElevenLabs).

Own voice only, with explicit consent: a clone is created from a sample the parent records
themselves, its ID is kept only in the parent's browser, and "Delete everything" deletes it
at ElevenLabs. Nothing is stored on Nestling's server.
"""

import os
from functools import cache

import requests

API = "https://api.elevenlabs.io/v1"
MODEL = "eleven_multilingual_v2"


def _headers() -> dict:
    return {"xi-api-key": os.environ["ELEVENLABS_API_KEY"]}


@cache
def default_voice() -> str:
    """A calm premade voice: ELEVENLABS_VOICE_ID if set, else the first premade voice on the account."""
    if os.getenv("ELEVENLABS_VOICE_ID"):
        return os.environ["ELEVENLABS_VOICE_ID"]
    voices = requests.get(f"{API}/voices", headers=_headers(), timeout=30).json()["voices"]
    premade = [v for v in voices if v.get("category") == "premade"] or voices
    return premade[0]["voice_id"]


def speak(text: str, voice_id: str | None = None, speed: float | None = None) -> bytes:
    """MP3 audio of the text (speed 0.7-1.2 changes the pace; omitted = the voice's natural pace)."""
    body = {"text": text, "model_id": MODEL}
    if speed:
        body["voice_settings"] = {"speed": speed}
    r = requests.post(f"{API}/text-to-speech/{voice_id or default_voice()}", headers=_headers(), timeout=120,
                      params={"output_format": "mp3_44100_128"}, json=body)
    r.raise_for_status()
    return r.content


def clone(name: str, sample: bytes, filename: str) -> str:
    """Instant voice clone from the parent's own recording. Returns the voice ID."""
    r = requests.post(f"{API}/voices/add", headers=_headers(), timeout=120, data={"name": f"Nestling: {name}"},
                      files={"files": (filename, sample)})
    r.raise_for_status()
    return r.json()["voice_id"]


def delete(voice_id: str) -> None:
    requests.delete(f"{API}/voices/{voice_id}", headers=_headers(), timeout=30).raise_for_status()
