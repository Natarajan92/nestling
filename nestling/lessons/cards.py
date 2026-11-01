"""Step cards: draws a lesson's title card, one card per step and a closing card as 1080x1920 PNGs.

No image model and no photographs: the cards are drawn in code with the Nestling palette, Fraunces and
Inter (assets/fonts, SIL OFL) and Phosphor icons (assets/icons, MIT) on a soft blob shape. Icons are SVG
paths rasterised here (Pillow only), so they stay crisp. The same module says what each card narrates.
"""

import math
import re
from functools import cache
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from nestling import retrieval
from nestling.lessons import ASSETS
from nestling.lessons.stitch import CAPTION_Y

W, H = 1080, 1920
SS = 3  # supersampling for shapes and icons

CREAM, PEACH, BLUSH, SAGE, INK, GOLD = "#FFF8F1", "#F7B49A", "#EFA3B5", "#9CB89A", "#2E2A3A", "#E8B65A"
# One tone per step: soft background, stronger blob, deep accent for the number.
TONES = [
    {"bg": "#FDEADF", "blob": PEACH, "deep": "#C4684A"},
    {"bg": "#FBE6EB", "blob": BLUSH, "deep": "#B24F6C"},
    {"bg": "#E7F0E5", "blob": SAGE, "deep": "#5E8460"},
    {"bg": "#FBF0D6", "blob": GOLD, "deep": "#A97A1E"},
    {"bg": "#FDEADF", "blob": PEACH, "deep": "#C4684A"},
]
CLOSING_REVIEW_PENDING = "Pending review"
DISCLAIMER = "General information from trusted sources, not a substitute for medical advice."


# ---------- fonts and drawing helpers ----------

@cache
def font(family: str, size: int, weight: int) -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(ASSETS / "fonts" / f"{family}.ttf"), size)
    if family == "Fraunces":  # axes: optical size, weight, softness, wonk
        f.set_variation_by_axes([min(144, max(9, size / 2)), weight, 100, 0])
    else:  # Inter: optical size, weight
        f.set_variation_by_axes([min(32, max(14, size / 3)), weight])
    return f


def wrap(draw: ImageDraw.ImageDraw, text: str, fnt, max_width: int) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if line and draw.textlength(trial, font=fnt) > max_width:
            lines.append(line)
            line = word
        else:
            line = trial
    return lines + [line] if line else lines


def text_block(draw, xy, text, fnt, fill, max_width, line_height, anchor="l", max_lines=None) -> int:
    """Draw wrapped text. xy is the top-left (anchor 'l') or the top-centre (anchor 'm'). Returns the bottom y."""
    x, y = xy
    lines = wrap(draw, text, fnt, max_width)
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(" .,;") + "…"
    for line in lines:
        draw.text((x, y), line, font=fnt, fill=fill, anchor=anchor + "a")
        y += line_height
    return y


def _paste_mask(img: Image.Image, mask: Image.Image, fill: str, xy=(0, 0)) -> None:
    img.paste(Image.new("RGB", mask.size, fill), xy, mask)


def shape_mask(size: tuple[int, int], draw_fn) -> Image.Image:
    """Antialiased mask: draw_fn(ImageDraw, scale) paints white on a supersampled canvas."""
    big = Image.new("L", (size[0] * SS, size[1] * SS), 0)
    draw_fn(ImageDraw.Draw(big), SS)
    return big.resize(size, Image.LANCZOS)


def shadowed(img: Image.Image, mask: Image.Image, fill: str, xy=(0, 0), blur=26, offset=(0, 18), opacity=0.16) -> None:
    """Paste a filled mask with a soft ink shadow beneath it."""
    shadow = mask.filter(ImageFilter.GaussianBlur(blur)).point(lambda v: int(v * opacity))
    img.paste(Image.new("RGB", mask.size, INK), (xy[0] + offset[0], xy[1] + offset[1]), shadow)
    _paste_mask(img, mask, fill, xy)


def pill(img, box, fill, radius=None, shadow=False) -> None:
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    r = radius if radius is not None else h // 2
    pad = 60 if shadow else 0
    mask = shape_mask((w + 2 * pad, h + 2 * pad),
                      lambda d, s: d.rounded_rectangle((pad * s, pad * s, (pad + w) * s - 1, (pad + h) * s - 1), r * s, fill=255))
    xy = (x0 - pad, y0 - pad)
    shadowed(img, mask, fill, xy, blur=14, offset=(0, 8), opacity=0.12) if shadow else _paste_mask(img, mask, fill, xy)


def blob_polygon(cx: float, cy: float, r: float, seed: int, n: int = 360) -> list[tuple[float, float]]:
    """A soft organic round shape: a circle gently wobbled by low harmonics (different per seed)."""
    ph = [(seed * 1.7 + k * 2.3) % (2 * math.pi) for k in range(3)]
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        wob = 1 + 0.045 * math.sin(2 * t + ph[0]) + 0.035 * math.sin(3 * t + ph[1]) + 0.02 * math.sin(5 * t + ph[2])
        pts.append((cx + r * wob * math.cos(t), cy + r * wob * math.sin(t)))
    return pts


# ---------- SVG icons (Phosphor "fill" paths) ----------

_TOKEN = re.compile(r"[MmLlHhVvCcSsQqTtAaZz]|-?(?:\d+\.?\d*|\.\d+)(?:e-?\d+)?")


def _arc(p0, rx, ry, rot, large, sweep, p1, steps=24):
    """Flatten an SVG elliptical arc (endpoint form) to points."""
    (x0, y0), (x1, y1) = p0, p1
    if rx == 0 or ry == 0 or p0 == p1:
        return [p1]
    phi = math.radians(rot)
    cp, sp = math.cos(phi), math.sin(phi)
    dx, dy = (x0 - x1) / 2, (y0 - y1) / 2
    x1p, y1p = cp * dx + sp * dy, -sp * dx + cp * dy
    rx, ry = abs(rx), abs(ry)
    lam = x1p**2 / rx**2 + y1p**2 / ry**2
    if lam > 1:
        rx, ry = rx * math.sqrt(lam), ry * math.sqrt(lam)
    num = rx**2 * ry**2 - rx**2 * y1p**2 - ry**2 * x1p**2
    den = rx**2 * y1p**2 + ry**2 * x1p**2
    co = math.sqrt(max(0, num / den)) * (-1 if large == sweep else 1)
    cxp, cyp = co * rx * y1p / ry, -co * ry * x1p / rx
    cx, cy = cp * cxp - sp * cyp + (x0 + x1) / 2, sp * cxp + cp * cyp + (y0 + y1) / 2

    def ang(ux, uy, vx, vy):
        a = math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)
        return a

    th1 = ang(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry)
    dth = ang((x1p - cxp) / rx, (y1p - cyp) / ry, (-x1p - cxp) / rx, (-y1p - cyp) / ry)
    if not sweep and dth > 0:
        dth -= 2 * math.pi
    elif sweep and dth < 0:
        dth += 2 * math.pi
    pts = []
    for i in range(1, steps + 1):
        t = th1 + dth * i / steps
        pts.append((cp * rx * math.cos(t) - sp * ry * math.sin(t) + cx, sp * rx * math.cos(t) + cp * ry * math.sin(t) + cy))
    return pts


def path_subpaths(d: str) -> list[list[tuple[float, float]]]:
    """Flatten an SVG path 'd' (M L H V C S Q T A Z, absolute and relative) into polygons."""
    tokens = _TOKEN.findall(d)
    subs, cur, pos, start, cmd, last_c = [], [], (0.0, 0.0), (0.0, 0.0), "", None
    i = 0

    def num():
        nonlocal i
        i += 1
        return float(tokens[i - 1])

    while i < len(tokens):
        if tokens[i].isalpha():
            cmd = tokens[i]
            i += 1
            if cmd in "Zz":
                if cur:
                    subs.append(cur)
                cur, pos = [], start
                continue
        rel, c = cmd.islower(), cmd.upper()
        ox, oy = pos if rel else (0.0, 0.0)
        if c == "M":
            pos = (ox + num(), oy + num())
            if cur:
                subs.append(cur)
            cur, start = [pos], pos
            cmd = "l" if rel else "L"
        elif c == "L":
            pos = (ox + num(), oy + num())
            cur.append(pos)
        elif c == "H":
            pos = ((pos[0] if rel else 0) + num(), pos[1])
            cur.append(pos)
        elif c == "V":
            pos = (pos[0], (pos[1] if rel else 0) + num())
            cur.append(pos)
        elif c in "CS":
            if c == "C":
                p1 = (ox + num(), oy + num())
            else:  # smooth: reflect the previous control point
                p1 = (2 * pos[0] - last_c[0], 2 * pos[1] - last_c[1]) if last_c else pos
            p2 = (ox + num(), oy + num())
            p3 = (ox + num(), oy + num())
            for k in range(1, 21):
                t = k / 20
                u = 1 - t
                cur.append(tuple(u**3 * a + 3 * u * u * t * b + 3 * u * t * t * c_ + t**3 * d_
                                 for a, b, c_, d_ in zip(pos, p1, p2, p3)))
            pos, last_c = p3, p2
            continue
        elif c in "QT":
            p1 = (ox + num(), oy + num()) if c == "Q" else ((2 * pos[0] - last_c[0], 2 * pos[1] - last_c[1]) if last_c else pos)
            p2 = (ox + num(), oy + num())
            for k in range(1, 13):
                t = k / 12
                u = 1 - t
                cur.append(tuple(u * u * a + 2 * u * t * b + t * t * c_ for a, b, c_ in zip(pos, p1, p2)))
            pos, last_c = p2, p1
            continue
        elif c == "A":
            rx, ry, rot, large, sweep = num(), num(), num(), int(num()), int(num())
            end = (ox + num(), oy + num())
            cur.extend(_arc(pos, rx, ry, rot, large, sweep, end))
            pos = end
        last_c = None
    if cur:
        subs.append(cur)
    return subs


@cache
def icon_mask(name: str, size: int) -> Image.Image:
    """Antialiased mask of a vendored Phosphor icon at size x size (even-odd fill of its path)."""
    svg = (ASSETS / "icons" / f"{name}.svg").read_text(encoding="utf-8")
    view = [float(v) for v in re.search(r'viewBox="([^"]+)"', svg).group(1).split()]
    scale = size * SS / view[2]
    mask = Image.new("L", (size * SS, size * SS), 0)
    for d in re.findall(r'\sd="([^"]+)"', svg):
        for poly in path_subpaths(d):
            if len(poly) < 3:
                continue
            layer = Image.new("L", mask.size, 0)
            ImageDraw.Draw(layer).polygon([((x - view[0]) * scale, (y - view[1]) * scale) for x, y in poly], fill=255)
            mask = ImageChops.logical_xor(mask.convert("1"), layer.convert("1")).convert("L")
    return mask.resize((size, size), Image.LANCZOS)


def draw_icon(img, name, center, size, fill) -> None:
    _paste_mask(img, icon_mask(name, size), fill, (int(center[0] - size / 2), int(center[1] - size / 2)))


# ---------- what each card says ----------

def source_lines(board: dict) -> list[str]:
    """One line per source: 'Title, Publisher (year), pp. 87, 88'."""
    registry = retrieval.load_registry()
    pages: dict[str, list[str]] = {}
    for s in board["scenes"]:
        pages.setdefault(s["source_id"], [])
        if s["page_label"] not in pages[s["source_id"]]:
            pages[s["source_id"]].append(s["page_label"])
    lines = []
    for sid in board["sources"]:
        src = registry.get(sid, {})
        label = src.get("title", sid)
        publisher = src.get("publisher", "")
        lines.append((f"{label}. {publisher} ({src['year']})" if src.get("year") else f"{label}. {publisher}", "p. " + ", ".join(pages.get(sid, []))))
    return lines


def card_plan(board: dict) -> list[dict]:
    """Every card in order: kind and the narration read over it."""
    steps = [{"kind": "step", "scene": s, "narration": s["narration_line"]} for s in board["scenes"]]
    return ([{"kind": "title", "narration": f"{board['title']}."}] + steps +
            [{"kind": "closing", "narration": "If you are unsure, please ask your doctor."}])


# ---------- the cards ----------

def _frame(bg: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (W, H), bg)
    # a faint lighter wash from the top for depth
    wash = Image.linear_gradient("L").resize((W, H)).transpose(Image.FLIP_TOP_BOTTOM).point(lambda v: int(v * 0.35))
    img.paste(Image.new("RGB", (W, H), CREAM), (0, 0), wash)
    return img, ImageDraw.Draw(img)


def _wordmark(img, draw) -> None:
    draw.text((84, 92), "Nestling", font=font("Fraunces", 52, 600), fill=INK)
    draw_icon(img, "heart", (84 + draw.textlength("Nestling", font=font("Fraunces", 52, 600)) + 38, 122), 34, "#D9766A")


def _dots(img, count: int, active: int, tone: dict) -> None:
    """Progress dots; the current one is a longer pill. Laid out left to right with equal gaps."""
    widths = [60 if i == active else 22 for i in range(count)]
    x = W / 2 - (sum(widths) + 22 * (count - 1)) / 2
    for i, w in enumerate(widths):
        pill(img, (int(x), 1838, int(x + w), 1860), tone["deep"] if i == active else tone["blob"])
        x += w + 22


def _blob_with_icon(img, tone, icon, seed, cy=860, r=330, icon_size=380) -> None:
    box = (int(r * 1.25) * 2, int(r * 1.25) * 2)
    c = (box[0] // 2, box[1] // 2)
    mask = shape_mask(box, lambda d, s: d.polygon([(x * s, y * s) for x, y in blob_polygon(c[0], c[1], r, seed)], fill=255))
    shadowed(img, mask, tone["blob"], (W // 2 - c[0], cy - c[1]), blur=34, offset=(0, 26), opacity=0.18)
    halo = shape_mask(box, lambda d, s: d.polygon([(x * s, y * s) for x, y in blob_polygon(c[0], c[1], r * 0.8, seed + 3)], fill=255))
    _paste_mask(img, halo.point(lambda v: int(v * 0.30)), "#FFFFFF", (W // 2 - c[0], cy - c[1]))
    draw_icon(img, icon, (W // 2, cy), icon_size, INK)


def _safety_pill(img, draw, text: str, y: int) -> None:
    """Gold pill: shield icon, a small 'SAFETY' label and the step's first safety point (up to two lines)."""
    fnt = font("Inter", 36, 500)
    lines = wrap(draw, text, fnt, 740)[:2]
    h = 40 + 38 + 46 * len(lines) + 16
    pill(img, (84, y, W - 84, y + h), GOLD, radius=44, shadow=True)
    draw_icon(img, "shield-check", (84 + 70, y + h / 2), 64, INK)
    draw.text((84 + 134, y + 34), "SAFETY", font=font("Inter", 24, 800), fill="#6B4A0F")
    ty = y + 34 + 38
    for line in lines:
        draw.text((84 + 134, ty), line, font=fnt, fill=INK)
        ty += 46


def render_step(board: dict, index: int) -> Image.Image:
    scene, total = board["scenes"][index], len(board["scenes"])
    tone = TONES[index % len(TONES)]
    img, draw = _frame(tone["bg"])
    _wordmark(img, draw)
    draw.text((W - 84, 100), f"Step {index + 1} of {total}", font=font("Inter", 34, 600), fill=INK, anchor="ra")
    draw.text((84, 190), str(scene["step_no"]), font=font("Fraunces", 380, 700), fill=tone["deep"])
    _blob_with_icon(img, tone, scene["icon"], seed=index + 1, cy=860)
    size = 72
    while size > 56 and len(wrap(draw, scene["caption"], font("Fraunces", size, 650), W - 180)) > 2:
        size -= 4
    bottom = text_block(draw, (W // 2, 1250), scene["caption"], font("Fraunces", size, 650), INK, W - 180, int(size * 1.17), anchor="m", max_lines=2)
    if scene.get("safety_points"):
        _safety_pill(img, draw, scene["safety_points"][0], bottom + 36)
    _dots(img, total + 2, index + 1, tone)
    return img


def render_title(board: dict) -> Image.Image:
    tone = TONES[0]
    img, draw = _frame(tone["bg"])
    _wordmark(img, draw)
    used = {sc["icon"] for sc in board["scenes"]}
    # A valid board has at most five steps, so six choices always leave one unused.
    title_icon = next(i for i in ("hand-heart", "baby", "heart", "sparkle", "smiley", "feather") if i not in used)
    _blob_with_icon(img, tone, title_icon, seed=7, cy=740, r=310, icon_size=360)
    pill(img, (W // 2 - 190, 1120, W // 2 + 190, 1196), INK)
    draw.text((W // 2, 1158), "LITTLE LESSONS", font=font("Inter", 30, 700), fill=CREAM, anchor="mm")
    y = text_block(draw, (W // 2, 1250), board["title"], font("Fraunces", 104, 700), INK, W - 160, 118, anchor="m", max_lines=3)
    draw.text((W // 2, y + 24), f"{len(board['scenes'])} gentle steps", font=font("Inter", 36, 500), fill=tone["deep"], anchor="ma")
    _dots(img, len(board["scenes"]) + 2, 0, tone)
    return img


def render_closing(board: dict, reviewed_on: str | None) -> Image.Image:
    tone = TONES[2]
    img, draw = _frame(tone["bg"])
    _wordmark(img, draw)
    fnt, pages_fnt = font("Inter", 34, 500), font("Inter", 30, 700)
    cards = [(wrap(draw, title, fnt, W - 248), pages) for title, pages in source_lines(board)]
    heights = [56 + 46 * len(lines) + 50 for lines, _ in cards]
    # layout as one centred group: heading, check badge, source cards, review pill, disclaimer
    group = 100 + 40 + 360 + 50 + sum(h + 28 for h in heights) + 40 + 92 + 40 + 100
    y = 190 + max(0, (1790 - 190 - group) // 2)
    badge_height, after_badge, card_gap, before_review = 360, 50, 28, 40
    disclaimer_font = font("Inter", 32, 500)
    disclaimer_lines = wrap(draw, DISCLAIMER, disclaimer_font, W - 220)
    disclaimer_bottom = max(draw.textbbox((W // 2, 132 + i * 46), line,
                                          font=disclaimer_font, anchor="ma")[3]
                            for i, line in enumerate(disclaimer_lines))
    bottom = y + 140 + badge_height + after_badge + sum(h + card_gap for h in heights) + before_review + disclaimer_bottom
    if bottom > CAPTION_Y - 24:
        # Keep the actual citation type size; compact only decoration and spacing.
        badge_height, after_badge, card_gap, before_review = 240, 30, 20, 24
        group = 140 + badge_height + after_badge + sum(h + card_gap for h in heights) + before_review + disclaimer_bottom
        available = CAPTION_Y - 24 - 190
        if group > available:
            raise ValueError("Full source citations cannot fit above the video caption strip")
        y = 190 + (available - group) // 2
    draw.text((W // 2, y), "Where this comes from", font=font("Fraunces", 78, 700), fill=INK, anchor="ma")
    y += 140
    badge = shape_mask((440, 440), lambda d, s: d.polygon([(x * s, yy * s) for x, yy in blob_polygon(220, 220, 150, 11)], fill=255))
    if badge_height != 360:
        badge = badge.resize((294, 294), Image.Resampling.LANCZOS)
    badge_center = y + badge_height // 2
    shadowed(img, badge, tone["blob"], (W // 2 - badge.width // 2, badge_center - badge.height // 2), blur=24, offset=(0, 16), opacity=0.16)
    draw_icon(img, "check-circle", (W // 2, badge_center), 190 if badge_height == 360 else 130, INK)
    y += badge_height + after_badge
    for (lines, pages), h in zip(cards, heights):
        pill(img, (84, y, W - 84, y + h), "#FFFFFF", radius=40, shadow=True)
        ty = y + 32
        for line in lines:
            draw.text((124, ty), line, font=fnt, fill=INK)
            ty += 46
        draw.text((124, ty + 6), pages, font=pages_fnt, fill=tone["deep"])
        y += h + card_gap
    y += before_review
    label = f"Reviewed on {reviewed_on}" if reviewed_on else CLOSING_REVIEW_PENDING
    pill(img, (W // 2 - 270, y, W // 2 + 270, y + 92), GOLD if not reviewed_on else SAGE, shadow=True)
    draw.text((W // 2, y + 46), label, font=font("Inter", 38, 700), fill=INK, anchor="mm")
    text_block(draw, (W // 2, y + 132), DISCLAIMER, disclaimer_font, INK, W - 220, 46, anchor="m")
    _dots(img, len(board["scenes"]) + 2, len(board["scenes"]) + 1, tone)
    return img


CAPTION_BOX = (W, 150)


def render_caption(text: str) -> Image.Image:
    """Fit the complete narration in its transparent strip; never truncate instructions."""
    img = Image.new("RGBA", CAPTION_BOX, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    for size in range(38, 27, -2):
        fnt = font("Inter", size, 500)
        lines = wrap(draw, text, fnt, W - 200)
        spacing = round(size * 48 / 38)
        y = (CAPTION_BOX[1] - spacing * len(lines)) / 2
        boxes = [draw.textbbox((W / 2, y + i * spacing), line, font=fnt, anchor="ma")
                 for i, line in enumerate(lines)]
        if boxes and all(100 <= x0 < x1 <= W - 100 and 0 <= y0 < y1 <= CAPTION_BOX[1]
                         for x0, y0, x1, y1 in boxes):
            break
    else:
        raise ValueError("Narration caption cannot fit legibly in the video strip")
    for line in lines:
        draw.text((W / 2, y), line, font=fnt, fill=INK, anchor="ma")
        y += spacing
    return img


def render_cards(board: dict, out_dir: Path, reviewed_on: str | None = None) -> list[Path]:
    """Write card_1.png (title), card_2.. (steps), the closing card and a caption_<n>.png strip for each, to out_dir.
    Returns the card paths in order."""
    out_dir.mkdir(parents=True, exist_ok=True)
    images = [render_title(board), *(render_step(board, i) for i in range(len(board["scenes"]))), render_closing(board, reviewed_on)]
    paths = []
    for n, (im, card) in enumerate(zip(images, card_plan(board)), 1):
        render_caption(card["narration"]).save(out_dir / f"caption_{n}.png")
        path = out_dir / f"card_{n}.png"
        im.save(path, optimize=True)
        paths.append(path)
    return paths
