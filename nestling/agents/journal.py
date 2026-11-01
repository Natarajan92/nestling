"""Journal: voice and text entries -> mood, notes and profile updates (Sonnet + ElevenLabs).

Nothing is saved without the parent's explicit permission (constitution V). In the Ask
pipeline (and the evaluation) there is no permission, so Journal explains how to turn
saving on; the web app saves entries once the parent has opted in.
"""

ASK_PERMISSION = (
    "I'd love to keep that for you. To protect your privacy I only save notes after you say yes: "
    'turn on "Save my journal" in Settings, then share it again and I\'ll add it to your memory book.'
)
SAVED = "Saved to your memory book. 💛"


def answer(question: str, context: dict, mode: str = "reranked", can_save: bool = False) -> dict:
    return {"answer": SAVED if can_save else ASK_PERMISSION, "sources_cited": [], "hits": [], "usage": [],
            "agent": "journal", "save": bool(can_save)}
