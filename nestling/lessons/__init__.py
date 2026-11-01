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

# Reviewed newborn care and prenatal preparation. `see_how` is hand-curated (never model-written).
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
    "labour_room_readiness": {"title": "Preparing together for the labour room", "stage": "before_birth", "see_how": None,
                              "sources": ["MOHFW-ANC", "NHS-WALES-BIRTH-PARTNER"],
                              "queries": ["preparing together for labour and birth; birth companion support", "birth preferences and hospital preparation"]},
    "prenatal_yoga_preparation": {"title": "Preparing for a prenatal yoga class", "stage": "before_birth",
                                 "see_how": {"label": "NHS prenatal yoga class and safety information",
                                             "url": "https://www.nhs.uk/live-well/exercise/pilates-and-yoga/prenatal-and-postnatal-exercise/", "publisher": "NHS"},
                                 "sources": ["NHS-PRENATAL-YOGA", "NHS-NNUH-PREGNANCY-PHYSIO", "NHS-RB-PREGNANCY-BODY"],
                                 "queries": ["preparing for a qualified prenatal yoga class", "pregnancy exercise suitability equipment and stopping for pain"]},
    "pregnancy_breathing": {"title": "Practising relaxed breathing before birth", "stage": "before_birth", "see_how": None,
                            "sources": ["NHS-UHNM-ANTENATAL"],
                            "queries": ["antenatal breathing and relaxation practice lower ribcage", "slow nasal inhalation and oral exhalation during pregnancy practice"]},
    "pregnancy_bed_movement": {"title": "Getting into and out of bed", "stage": "before_birth", "see_how": None,
                               "sources": ["NHS-RB-PREGNANCY-BODY", "NHS-NNUH-PREGNANCY-PHYSIO"],
                               "queries": ["pregnancy roll shoulders hips knees together getting out of bed", "side resting and reversing movement to enter bed during pregnancy"]},
    "pregnancy_stair_comfort": {"title": "When stairs feel uncomfortable in pregnancy", "stage": "before_birth", "see_how": None,
                                "sources": ["NHS-PREGNANCY-PELVIC-PAIN", "HSE-PREGNANCY-PGP-ACTIVITIES"],
                                "queries": ["pregnancy stair discomfort seek midwife physiotherapist advice", "pelvic pain pace activities reduce repeated stairs bannister support"]},
    "preparing_body_for_birth": {"title": "Gentle activity to prepare for birth", "stage": "before_birth", "see_how": None,
                                 "sources": ["NHS-PREGNANCY-EXERCISE"],
                                 "queries": ["gentle activity gradual start prepare for birth", "pregnancy exercise talk test comfort hydration stop unwell"]},
}


def icon_names() -> list[str]:
    """Names of the vendored Phosphor icons (assets/icons/<name>.svg)."""
    return sorted(p.stem for p in (ASSETS / "icons").glob("*.svg"))
