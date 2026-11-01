"""Little Lessons: short sourced how-to step-card videos for new parents.

Build time only (except library.py): storyboard from registered sources -> step cards -> narration -> MP4.
Nothing is generated live per question, and no image model is used (plan §2 rule 8, §4).
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
LESSONS_DIR = ROOT / "lessons"
ASSETS = ROOT / "assets"

SEE_HOW_NHS = {
    "label": "How should I bath my baby?",
    "url": "https://www.nhs.uk/best-start-in-life/baby/baby-basics/caring-for-your-baby/bathing-your-baby/",
    "publisher": "NHS",
}
SEE_HOW_GHMP = {
    "label": "Breastfeeding Attachment (Hindi)",
    "url": "https://globalhealthmedia.org/video/breastfeeding-attachment-hindi/",
    "publisher": "Global Health Media Project",
}

# The six first lessons. `queries` search the registered sources; `see_how` is hand-curated (never model-written).
LESSONS: dict[str, dict] = {
    "holding": {"title": "Holding your newborn", "stage": "first_weeks", "see_how": None,
                "sources": ["NHS-RWT-HOLDING"],
                "queries": ["how to hold and carry a newborn baby, support head and neck",
                            "lifting and cradling a newborn, support head neck shoulders back and bottom"]},
    "bathing": {"title": "Bathing your newborn", "stage": "first_weeks", "see_how": SEE_HOW_NHS,
                "sources": ["WHO-POSTNATAL", "MOHFW-IYCF", "MOHFW-MAA", "NHS-BABY-BATHING"],
                "queries": ["bathing a newborn baby: when, how, water, drying and keeping warm",
                            "delay the first bath, wipe and dry the baby, keep the baby warm"]},
    "burping": {"title": "Burping your baby", "stage": "first_weeks", "see_how": None,
                "sources": ["WHO-POSTNATAL", "MOHFW-IYCF", "MOHFW-MAA", "NHS-BABY-BURPING"],
                "queries": ["how to burp a baby after a feed, hold upright, pat the back",
                            "bringing up wind after breastfeeding, baby position after feeding"]},
    "swaddling": {"title": "Swaddling safely", "stage": "first_weeks", "see_how": None,
                  "sources": ["NSW-SCHN-SWADDLING"],
                  "queries": ["how to wrap or swaddle a newborn baby safely in a cloth",
                              "keeping the newborn warm, wrapping, safe sleep position on the back"]},
    "latching": {"title": "A good breastfeeding latch", "stage": "first_weeks", "see_how": SEE_HOW_GHMP,
                 "sources": ["MOHFW-IYCF", "MOHFW-MAA", "WHO-POSTNATAL"],
                 "queries": ["good attachment and positioning for breastfeeding, baby's mouth wide open, chin touching breast",
                             "how to help the baby latch on, signs of good attachment, positions for breastfeeding"]},
    "cord_care": {"title": "Caring for the umbilical cord", "stage": "first_weeks", "see_how": None,
                  "sources": ["WHO-POSTNATAL", "MOHFW-IYCF", "MOHFW-MAA"],
                  "queries": ["umbilical cord care of the newborn, keep clean and dry",
                              "cord stump care, do not apply anything, signs to see a health worker"]},
}


def icon_names() -> list[str]:
    """Names of the vendored Phosphor icons (assets/icons/<name>.svg)."""
    return sorted(p.stem for p in (ASSETS / "icons").glob("*.svg"))
