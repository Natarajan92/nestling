"""Find photo studios and extract their listed packages (Capture).

Tavily search (non-medical lookups only, constitution) returns studio pages with their text;
The FAST model extracts a `StudioPackage` from the page text only. No images are downloaded or
re-published, and nothing behind a login is read. Prices shown only inside images stay
None ("Not listed — ask the studio").
"""

import json
import os
import urllib.request
from datetime import date

from langsmith import traceable
from langsmith.utils import ContextThreadPoolExecutor

from nestling.llm import FAST, chat_json
from nestling.capture.estimate import parse_inr
from nestling.schemas.studio_package import Album, Casting, Extra, Frame, StudioPackage

TAVILY_URL = "https://api.tavily.com/search"
SHOOT_QUERIES = {
    "maternity": "maternity photoshoot packages price",
    "baby_shower": "baby shower seemantham photography packages price",
    "newborn": "newborn baby photoshoot packages price",
    "casting": "baby hand and foot casting price",
}

EXTRACT_PROMPT = """You extract a photo studio's package from the text of its web page, for a parent comparing studios.
Copy only what the page says. If a value is not written on the page, leave it null (or an empty string for text fields); never estimate or guess.
price_inr is the package price in rupees as a whole number; if the page says GST is extra, still give the listed number and put the exact wording in price_text.
If the page lists several packages, extract the one that best matches the requested shoot type (prefer the mid-priced one).
If the page is not a studio's own package or price page, set studio_name to "NOT_A_STUDIO_PAGE"."""


@traceable(name="tavily_search", run_type="tool")
def search_studios(city: str, shoot_type: str, max_results: int = 8) -> list[dict]:
    """Tavily results with page text: [{"url", "title", "content", "raw_content"}]."""
    body = {"query": f"{SHOOT_QUERIES[shoot_type]} {city}", "search_depth": "advanced", "max_results": max_results,
            "include_raw_content": True, "include_images": False}
    request = urllib.request.Request(TAVILY_URL, data=json.dumps(body).encode(), method="POST", headers={
        "Authorization": f"Bearer {os.environ['TAVILY_API_KEY']}", "Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response).get("results", [])


def _nullable(kind: str) -> dict:
    return {"type": [kind, "null"]}


# Flat on purpose: the nested StudioPackage schema is too complex for structured outputs, and
# code (not the LLM) assembles the final StudioPackage.
EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "studio_name": {"type": "string"}, "package_name": {"type": "string"},
        "price_text": _nullable("string"), "price_inr": _nullable("integer"),
        "inclusions": {"type": "array", "items": {"type": "string"}},
        "extras": {"type": "array", "items": {"type": "object", "properties": {"name": {"type": "string"}, "price_inr": _nullable("integer")},
                                              "required": ["name", "price_inr"], "additionalProperties": False}},
        "duration_hours": _nullable("number"), "photos_taken": _nullable("integer"), "edited_photos": _nullable("integer"),
        "delivery_days": _nullable("integer"), "album_offered": _nullable("boolean"), "album_price_inr": _nullable("integer"),
        "album_type": {"type": "string"}, "album_pages": _nullable("integer"), "frames_count": _nullable("integer"),
        "frames_sizes": {"type": "string"}, "casting_offered": _nullable("boolean"), "casting_price_inr": _nullable("integer"),
        "rating_summary": {"type": "string"}, "location": {"type": "string"},
    },
    "required": ["studio_name", "package_name", "price_text", "price_inr", "inclusions", "extras", "duration_hours", "photos_taken",
                 "edited_photos", "delivery_days", "album_offered", "album_price_inr", "album_type", "album_pages", "frames_count",
                 "frames_sizes", "casting_offered", "casting_price_inr", "rating_summary", "location"],
    "additionalProperties": False,
}


def to_package(data: dict, url: str, shoot_type: str, city: str) -> StudioPackage:
    """Assemble a StudioPackage in code. Code owns the source URL, the date and INR normalisation."""
    data = {k: (None if v == "" else v) for k, v in data.items()}  # "" means not listed
    price, assumptions = data.get("price_inr"), []
    if data.get("price_text"):
        parsed, assumptions = parse_inr(data["price_text"])
        price = parsed if parsed is not None else price
    frames = [Frame(size=data.get("frames_sizes"), count=data["frames_count"])] if data.get("frames_count") else []
    return StudioPackage(
        studio_name=data["studio_name"], package_name=data.get("package_name"), shoot_type=shoot_type, city=city,
        price_inr=price, price_text=data.get("price_text"), price_assumptions=assumptions,
        inclusions=data.get("inclusions") or [], extras=[Extra(**e) for e in data.get("extras") or []],
        duration_hours=data.get("duration_hours"), photos_taken=data.get("photos_taken"), edited_photos=data.get("edited_photos"),
        delivery_days=data.get("delivery_days"),
        album=Album(offered=data.get("album_offered"), price_inr=data.get("album_price_inr"), type=data.get("album_type"), pages=data.get("album_pages")),
        frames=frames, casting=Casting(offered=data.get("casting_offered"), price_inr=data.get("casting_price_inr")),
        rating_summary=data.get("rating_summary"), location=data.get("location"), contact_url=url, source_url=url,
        checked_on=date.today(),
    )


@traceable(name="extract_package", run_type="chain")
def extract_package(page: dict, shoot_type: str, city: str) -> StudioPackage | None:
    """One StudioPackage from one page's text, or None if the page is not a studio package page."""
    text = (page.get("raw_content") or page.get("content") or "")[:12000]
    if len(text) < 200:
        return None
    user = f"Shoot type: {shoot_type}. City: {city}. Page URL: {page['url']} Page title: {page.get('title')}" + "\n\nPage text:\n" + text
    data, _, _ = chat_json(FAST, EXTRACT_PROMPT, user, EXTRACT_SCHEMA, max_tokens=3000)
    if data is None:
        return None
    if data["studio_name"] == "NOT_A_STUDIO_PAGE":
        return None
    return to_package(data, page["url"], shoot_type, city)


@traceable(name="capture_search", run_type="chain")
def find_packages(city: str, shoot_type: str, max_results: int = 8) -> list[StudioPackage]:
    """Search, then extract packages in parallel; pages that are not studio pages are dropped."""
    pages = search_studios(city, shoot_type, max_results)
    with ContextThreadPoolExecutor(max_workers=4) as pool:
        packages = list(pool.map(lambda p: _safe_extract(p, shoot_type, city), pages))
    return [p for p in packages if p is not None]


def _safe_extract(page: dict, shoot_type: str, city: str) -> StudioPackage | None:
    try:
        return extract_package(page, shoot_type, city)
    except Exception:
        return None
