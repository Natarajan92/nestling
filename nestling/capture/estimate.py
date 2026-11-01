"""estimate_cost(): tier ranges + confidence, code only (plan §4, Capture).

The LLM never does this arithmetic. For a city and shoot type the listed packages are grouped
into Budget / Mid / Premium tiers by price. For each component the parent picks (base shoot,
album, frames, casting, add-ons) the low, high and median of comparable listed prices are
summed into a range per tier. Always a range, never a single number; confidence comes from
the number of studios behind it.
"""

import re
from statistics import median

from nestling.schemas.studio_package import StudioPackage

LABEL = "Approximate estimate to help you plan. Final prices come from the studio's quote."
NOT_ENOUGH = "Not enough data for a reliable estimate — request quotes."
GST_RATE = 0.18
TIERS = ("Budget", "Mid", "Premium")


def parse_inr(text: str) -> tuple[int | None, list[str]]:
    """'₹30k + 18% GST' -> (35400, ['18% GST added to ₹30,000']). Returns (None, []) if no price."""
    t = text.lower().replace(",", "").replace("₹", " ").replace("rs.", " ").replace("rs", " ").replace("inr", " ")
    m = re.search(r"(\d+(?:\.\d+)?)\s*(k|thousand|l|lakh|lac)?\b", t)
    if not m:
        return None, []
    amount = float(m.group(1)) * {"k": 1_000, "thousand": 1_000, "l": 100_000, "lakh": 100_000, "lac": 100_000}.get(m.group(2) or "", 1)
    assumptions = []
    gst = re.search(r"\+\s*(\d+(?:\.\d+)?)\s*%\s*gst", t)
    if gst:
        rate = float(gst.group(1)) / 100
        assumptions.append(f"{gst.group(1)}% GST added to ₹{int(amount):,}")
        amount *= 1 + rate
    elif re.search(r"\+\s*gst|gst extra|plus gst|excl\w*\.? (of )?gst|\+\s*taxes", t) and not re.search(r"incl\w*\.? (of )?(gst|tax)", t):
        assumptions.append(f"{int(GST_RATE * 100)}% GST assumed on ₹{int(amount):,} (page says GST is extra)")
        amount *= 1 + GST_RATE
    return round(amount), assumptions


def _extra_price(pkg: StudioPackage, name: str) -> int | None:
    for e in pkg.extras:
        if name in e.name.lower() and e.price_inr is not None:
            return e.price_inr
    return None


def _frame_price(pkg: StudioPackage, count: int) -> int | None:
    """Use the listed bundle counts and prices; never price an unknown frame as free."""
    remaining, total = count, 0
    for frame in pkg.frames:
        if frame.price_inr is not None and frame.count is not None and 0 < frame.count <= remaining:
            remaining -= frame.count
            total += frame.price_inr
        if remaining == 0:
            return total
    return None


def total_cost(pkg: StudioPackage, album: bool = False, frames: int = 0, casting: bool = False) -> int | None:
    """Listed price plus the extras the parent picked. None if a needed price is not listed."""
    if pkg.price_inr is None:
        return None
    total = pkg.price_inr
    if album:
        if not pkg.album.offered and pkg.album.price_inr is None and _extra_price(pkg, "album") is None:
            return None
        total += pkg.album.price_inr or _extra_price(pkg, "album") or 0  # None with offered = included
    if frames:
        price = _frame_price(pkg, frames)
        if price is None:
            return None
        total += price
    if casting:
        if pkg.casting.price_inr is None:
            return None
        total += pkg.casting.price_inr
    return total


def cost_per_edited_photo(pkg: StudioPackage, **picks) -> int | None:
    total = total_cost(pkg, **picks)
    if total is None or not pkg.edited_photos:
        return None
    return round(total / pkg.edited_photos)


def confidence(n_studios: int) -> str | None:
    if n_studios >= 8:
        return "High"
    if n_studios >= 4:
        return "Medium"
    if n_studios >= 3:
        return "Low"
    return None


def estimate_tier(packages: list[StudioPackage], album: bool = False, frames: int = 0, casting: bool = False) -> dict:
    """Range for one tier's packages: base + each picked component, low/high/median summed."""
    # A complete requested price from at least three distinct studios is needed.
    # Otherwise the range would silently omit unknown selected components.
    requested = [("album", album), ("frames", bool(frames)), ("casting", casting)]
    missing = [name for name, selected in requested if selected and len({p.studio_name for p in packages
               if total_cost(p, album=name == "album", frames=frames if name == "frames" else 0,
                             casting=name == "casting") is not None}) < 3]
    priced = [p for p in packages if total_cost(p, album=album, frames=frames, casting=casting) is not None]
    studios = {p.studio_name for p in priced}
    level = confidence(len(studios))
    if missing or level is None:
        return {"estimate": None, "message": NOT_ENOUGH, "n_studios": len(studios), "not_listed_components": missing}
    packages = priced
    components = {"base": [p.price_inr for p in packages if p.price_inr is not None]}
    if album:
        components["album"] = [p.album.price_inr or _extra_price(p, "album") or 0 for p in packages
                               if p.album.offered or p.album.price_inr is not None or _extra_price(p, "album") is not None]
    if frames:
        components["frames"] = [_frame_price(p, frames) for p in packages]
    if casting:
        components["casting"] = [p.casting.price_inr for p in packages if p.casting.price_inr is not None]
    missing = [name for name, values in components.items() if not values]
    low = sum(min(v) for v in components.values() if v)
    high = sum(max(v) for v in components.values() if v)
    typical = sum(median(v) for v in components.values() if v)
    return {"estimate": {"low": low, "high": high, "typical": round(typical)}, "confidence": level, "n_studios": len(studios),
            "components": {k: {"low": min(v), "high": max(v), "median": median(v), "n": len(v)} for k, v in components.items() if v},
            "not_listed_components": missing, "label": LABEL}


def assign_tiers(packages: list[StudioPackage]) -> dict[str, list[StudioPackage]]:
    """Split priced packages into tiers by listed price, with at least 3 studios per tier where
    possible: 9+ priced packages -> Budget / Mid / Premium, 6-8 -> Budget / Premium, else one group."""
    priced = sorted((p for p in packages if p.price_inr is not None), key=lambda p: p.price_inr)
    n = len(priced)
    if n >= 9:
        cuts = [round(n / 3), round(2 * n / 3)]
        return {"Budget": priced[:cuts[0]], "Mid": priced[cuts[0]:cuts[1]], "Premium": priced[cuts[1]:]}
    if n >= 6:
        return {"Budget": priced[:n // 2], "Premium": priced[n // 2:]}
    return {"All studios": priced}


def estimate_cost(packages: list[StudioPackage], album: bool = False, frames: int = 0, casting: bool = False) -> dict:
    """Per-tier ranges with confidence, sample size, checked-on dates and every source behind them."""
    tiers = assign_tiers(packages)
    out = {"label": LABEL, "tiers": {}}
    for name, group in tiers.items():
        result = estimate_tier(group, album=album, frames=frames, casting=casting)
        result["sources"] = [{"studio": p.studio_name, "package": p.package_name, "url": p.source_url,
                              "checked_on": p.checked_on.isoformat(), "price_inr": p.price_inr} for p in group]
        out["tiers"][name] = result
    return out


def quote_request(studio: str, shoot_type: str, picks: dict, date_text: str | None = None, city: str | None = None) -> str:
    """A draft enquiry listing exactly the components the parent picked. Never sent by Nestling."""
    lines = [f"Hello {studio},", "", f"We are planning a {shoot_type.replace('_', ' ')} shoot" + (f" in {city}" if city else "")
             + (f" around {date_text}" if date_text else "") + ". Could you share a quote for:"]
    if picks.get("edited_photos"):
        lines.append(f"- {picks['edited_photos']} edited photos (soft copies), and the delivery time")
    if picks.get("album"):
        pages = f", about {picks['album_pages']} pages" if picks.get("album_pages") else ""
        lines.append(f"- A printed album{pages}")
    if picks.get("frames"):
        lines.append(f"- {picks['frames']} framed print(s)" + (f" ({picks['frame_sizes']})" if picks.get("frame_sizes") else ""))
    if picks.get("casting"):
        lines.append("- Hand and foot casting")
    lines += ["- Travel, outfits, props or makeup charges, if any, and whether GST is included", "", "Thank you!"]
    return "\n".join(lines)
