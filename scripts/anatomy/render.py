from dataclasses import dataclass, field

C = {
    "bg": "#0a0b10",
    "card": "#0f1017",
    "line": "#2a2b36",
    "skin_top": "#20212c",
    "skin_bottom": "#15161e",
    "stroke": "#4d4f5e",
    "detail": "#33343f",
    "inner": "#3c3e4b",
    "text": "#d6d7de",
    "muted": "#7d7f8c",
    "gold": "#d8b25a",
    "amber": "#e2a336",
    "red": "#e5484d",
    "crimson": "#b3262c",
    "green": "#5bb878",
    "grey": "#9a9ca8",
}

STATE_LABEL = {
    "open": ("Open wound", C["amber"]),
    "festering": ("Festering", C["red"]),
    "scarred": ("Scarred", C["green"]),
    "lasting": ("Lasting harm", C["grey"]),
    "lost": ("Lost", C["red"]),
    "prosthesis": ("Prosthesis", C["gold"]),
    "fatal": ("Fatal", C["crimson"]),
}


def ellipse(cx: float, cy: float, rx: float, ry: float) -> str:
    kx, ky = rx * 0.5523, ry * 0.5523
    return (
        f"M{cx - rx:g},{cy:g} C{cx - rx:g},{cy - ky:g} {cx - kx:g},{cy - ry:g} {cx:g},{cy - ry:g} "
        f"C{cx + kx:g},{cy - ry:g} {cx + rx:g},{cy - ky:g} {cx + rx:g},{cy:g} "
        f"C{cx + rx:g},{cy + ky:g} {cx + kx:g},{cy + ry:g} {cx:g},{cy + ry:g} "
        f"C{cx - kx:g},{cy + ry:g} {cx - rx:g},{cy + ky:g} {cx - rx:g},{cy:g} Z"
    )


@dataclass
class Part:
    key: str
    label: str
    path: str
    anchor: tuple[float, float]
    inner: bool = False
    subtle: bool = False
    far: bool = False
    prelude: str = ""
    tone: str = ""


@dataclass
class Plan:
    name: str
    width: int
    height: int
    parts: list[Part]
    details: list[str] = field(default_factory=list)
    marks: list[str] = field(default_factory=list)
    underlay: str = ""


DEFS = f"""
<defs>
  <linearGradient id="skin" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="{C["skin_top"]}"/><stop offset="1" stop-color="{C["skin_bottom"]}"/>
  </linearGradient>
  <linearGradient id="divine" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#3b3222"/><stop offset="1" stop-color="#1d1a13"/>
  </linearGradient>
  <radialGradient id="aurafill" cx="50%" cy="40%" r="60%">
    <stop offset="0" stop-color="#d8b25a" stop-opacity="0.22"/><stop offset="0.6" stop-color="#d8b25a" stop-opacity="0.07"/>
    <stop offset="1" stop-color="#d8b25a" stop-opacity="0.02"/>
  </radialGradient>
  <linearGradient id="auraband" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#f3d68f" stop-opacity="0.85"/><stop offset="0.5" stop-color="#d8b25a" stop-opacity="0.55"/>
    <stop offset="1" stop-color="#a88a45" stop-opacity="0.8"/>
  </linearGradient>
  <linearGradient id="far" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#16171f"/><stop offset="1" stop-color="#0f1016"/>
  </linearGradient>
  <linearGradient id="rim" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#ffffff" stop-opacity="0.05"/><stop offset="0.5" stop-color="#ffffff" stop-opacity="0"/>
    <stop offset="1" stop-color="#ffffff" stop-opacity="0.03"/>
  </linearGradient>
  <linearGradient id="open" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="{C["amber"]}" stop-opacity="0.22"/><stop offset="1" stop-color="{C["amber"]}" stop-opacity="0.07"/>
  </linearGradient>
  <radialGradient id="festering" cx="50%" cy="50%" r="60%">
    <stop offset="0" stop-color="#ff7a45" stop-opacity="0.75"/><stop offset="0.45" stop-color="{C["red"]}" stop-opacity="0.45"/>
    <stop offset="1" stop-color="{C["red"]}" stop-opacity="0.12"/>
  </radialGradient>
  <radialGradient id="fatal" cx="50%" cy="45%" r="65%">
    <stop offset="0" stop-color="#ff5a5f" stop-opacity="0.95"/><stop offset="0.5" stop-color="{C["crimson"]}" stop-opacity="0.9"/>
    <stop offset="1" stop-color="#5a0c10" stop-opacity="0.9"/>
  </radialGradient>
  <linearGradient id="metal" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#7a6233"/><stop offset="0.45" stop-color="{C["gold"]}"/>
    <stop offset="0.7" stop-color="#a88a45"/><stop offset="1" stop-color="#5e4a22"/>
  </linearGradient>
  <linearGradient id="scar" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="{C["green"]}" stop-opacity="0.08"/><stop offset="1" stop-color="{C["green"]}" stop-opacity="0.02"/>
  </linearGradient>
  <pattern id="hatch" width="3.2" height="3.2" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
    <rect width="3.2" height="3.2" fill="#9a9ca8" fill-opacity="0.08"/>
    <line x1="0" y1="0" x2="0" y2="3.2" stroke="{C["grey"]}" stroke-opacity="0.45" stroke-width="0.9"/>
  </pattern>
  <filter id="glow" x="-40%" y="-40%" width="180%" height="180%">
    <feGaussianBlur stdDeviation="2.4" result="blur"/>
    <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <filter id="softglow" x="-40%" y="-40%" width="180%" height="180%">
    <feGaussianBlur stdDeviation="1.4" result="blur"/>
    <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
</defs>
"""


BASE = {"stroke-linejoin": "round", "stroke-width": "1.1"}
RIM = {"fill": "url(#rim)", "stroke": "none"}
SKIN = {"fill": "url(#skin)"}
LOOKS: dict[str, list[dict[str, str]]] = {
    "unhurt": [{**BASE, "fill": "url(#skin)", "stroke": C["stroke"], "title": "1"}, RIM],
    "unhurt:inner": [{**BASE, "fill": "#0b0c12", "fill-opacity": "0.32", "stroke": C["inner"], "stroke-dasharray": "2.2 1.8", "title": "1"}],
    "unhurt:subtle": [{**BASE, "fill": "none", "stroke": "#25262f", "title": "1"}],
    "unhurt:divine": [{**BASE, "fill": "url(#divine)", "stroke": C["gold"], "stroke-opacity": "0.75", "title": "1"}, RIM],
    "unhurt:aura": [{**BASE, "fill": "url(#auraband)", "stroke": "#f3d68f", "stroke-opacity": "0.8", "stroke-width": "0.8", "title": "1"}],
    "unhurt:far": [{**BASE, "fill": "url(#far)", "stroke": "#3a3b47", "title": "1"}],
    "open": [{**BASE, "fill": "url(#skin)", "stroke": C["amber"]}, {"fill": "url(#open)", "stroke": "none", "title": "1"}],
    "festering": [SKIN, {**BASE, "fill": "url(#festering)", "stroke": C["red"], "filter": "url(#softglow)", "title": "1"}],
    "scarred": [{**BASE, "fill": "url(#skin)", "stroke": C["green"], "stroke-opacity": "0.55"}, {"fill": "url(#scar)", "stroke": "none", "title": "1"}],
    "lasting": [{**BASE, "fill": "url(#skin)", "stroke": C["grey"]}, {"fill": "url(#hatch)", "stroke": "none", "title": "1"}],
    "lost": [{**BASE, "fill": C["red"], "fill-opacity": "0.05", "stroke": C["red"], "stroke-opacity": "0.75", "stroke-dasharray": "2.6 2", "title": "1"}],
    "prosthesis": [{**BASE, "fill": "url(#metal)", "stroke": "#f0d48a", "stroke-width": "0.9", "title": "1"}],
    "fatal": [SKIN, {**BASE, "fill": "url(#fatal)", "stroke": "#ff8a8e", "filter": "url(#glow)", "title": "1"}],
}


def look_of(part: Part, state: str) -> str:
    if state != "unhurt":
        return state
    for flag, look in (
        (part.inner, "unhurt:inner"),
        (part.subtle, "unhurt:subtle"),
        (part.tone == "divine", "unhurt:divine"),
        (part.tone == "aura", "unhurt:aura"),
        (part.far, "unhurt:far"),
    ):
        if flag:
            return look
    return "unhurt"


def styled(part: Part, state: str) -> str:
    out: list[str] = []
    for piece in part.path.split("|"):
        for layer in LOOKS[look_of(part, state)]:
            attrs = " ".join(f'{name}="{value}"' for name, value in layer.items() if name != "title")
            title = f"<title>{part.label}</title>" if "title" in layer else ""
            out.append(f'<path d="{piece.strip()}" {attrs}>{title}</path>')
    return "".join(out)


def glyph(part: Part, state: str) -> str:
    x, y = part.anchor
    cuts = f'<line x1="{x - 3.5}" y1="{y + 2.5}" x2="{x + 1.5}" y2="{y - 3.5}"/><line x1="{x - 0.5}" y1="{y + 3.5}" x2="{x + 4}" y2="{y - 1.5}"/>'
    ticks = "".join(f'<line x1="{x - 4 + i * 2.6:g}" y1="{y - 1.8}" x2="{x - 4 + i * 2.6:g}" y2="{y + 1.8}"/>' for i in range(4))
    glyphs = {
        "open": (
            f'<g stroke="#07080c" stroke-opacity="0.7" stroke-width="2.8" stroke-linecap="round">{cuts}</g>'
            f'<g stroke="{C["amber"]}" stroke-width="1.2" stroke-linecap="round">{cuts}</g>'
        ),
        "festering": (
            f'<g filter="url(#glow)"><circle cx="{x}" cy="{y}" r="2.6" fill="#ffb27a"/>'
            f'<circle cx="{x}" cy="{y}" r="5" fill="none" stroke="#ff7a45" stroke-opacity="0.6"/></g>'
        ),
        "scarred": f'<g stroke="{C["green"]}" stroke-width="0.8" stroke-linecap="round"><line x1="{x - 5.5}" y1="{y}" x2="{x + 5.5}" y2="{y}"/>{ticks}</g>',
        "lost": (
            f'<g stroke="{C["red"]}" stroke-width="1.3" stroke-linecap="round">'
            f'<line x1="{x - 3}" y1="{y - 3}" x2="{x + 3}" y2="{y + 3}"/><line x1="{x - 3}" y1="{y + 3}" x2="{x + 3}" y2="{y - 3}"/></g>'
        ),
        "prosthesis": "".join(
            f'<circle cx="{x + dx}" cy="{y + dy}" r="0.9" fill="#3d2f12"/>' for dx, dy in ((-2.5, -2.5), (2.5, -2.5), (-2.5, 2.5), (2.5, 2.5))
        ),
        "fatal": f'<path d="M{x},{y - 4} L{x + 3.5},{y} L{x},{y + 4} L{x - 3.5},{y} Z" fill="#ffd3d4" fill-opacity="0.9"/>',
    }
    return glyphs.get(state, "")


def callouts(plan: Plan, states: dict[str, str], offset: float, total: float) -> str:
    wounded = [part for part in plan.parts if states.get(part.key, "unhurt") != "unhurt"]
    left = sorted([part for part in wounded if part.anchor[0] < plan.width / 2], key=lambda part: part.anchor[1])
    right = sorted([part for part in wounded if part.anchor[0] >= plan.width / 2], key=lambda part: part.anchor[1])
    out: list[str] = []
    for column, side in ((left, "left"), (right, "right")):
        spots: list[float] = []
        last = -100.0
        for part in column:
            spot = max(part.anchor[1], last + 30, 14)
            spots.append(spot)
            last = spot
        overflow = (spots[-1] if spots else 0) - (plan.height - 14)
        if overflow > 0:
            spots = [spot - overflow for spot in spots]
            for index in range(len(spots) - 2, -1, -1):
                spots[index] = min(spots[index], spots[index + 1] - 30)
        for part, ly in zip(column, spots, strict=True):
            ax, ay = part.anchor[0] + offset, part.anchor[1]
            label, colour = STATE_LABEL[states[part.key]]
            if side == "left":
                tx, anchor, edge, elbow = 8, "start", offset + 22, offset - 4
                end = tx + 66
            else:
                tx, anchor, edge, elbow = total - 8, "end", offset + plan.width - 22, offset + plan.width + 4
                end = tx - 66
            out.append(
                f'<path d="M{ax},{ay} L{edge},{ay} L{elbow},{ly} L{end},{ly}" fill="none" stroke="{colour}" stroke-opacity="0.55" stroke-width="0.7"/>'
                f'<circle cx="{ax}" cy="{ay}" r="1.6" fill="{colour}"/>'
                f'<text x="{tx}" y="{ly - 3.5}" text-anchor="{anchor}" font-size="8.6" fill="{C["text"]}" font-weight="500">{part.label}</text>'
                f'<text x="{tx}" y="{ly + 7.5}" text-anchor="{anchor}" font-size="6.8" fill="{colour}" letter-spacing="0.6">{label.upper()}</text>'
            )
    return "".join(out)


def draw(plan: Plan, states: dict[str, str], *, labels: bool = True, scale: float = 1.5) -> str:
    gutter = 92 if labels else 12
    total = plan.width + gutter * 2
    body: list[str] = [plan.underlay]
    ordered = [part for part in plan.parts if not part.inner] + [part for part in plan.parts if part.inner]
    for part in ordered:
        state = states.get(part.key, "unhurt")
        if part.inner and state == "unhurt" and part.subtle:
            continue
        body.append(part.prelude + styled(part, state))
    detail = "".join(f'<path d="{path}" fill="none" stroke="{C["detail"]}" stroke-width="0.85" stroke-linecap="round"/>' for path in plan.details)
    marks = "".join(plan.marks)
    insert = len([part for part in plan.parts if not part.inner]) + 1
    body.insert(insert, detail + marks)
    glyphs = "".join(glyph(part, states[part.key]) for part in plan.parts if states.get(part.key, "unhurt") != "unhurt")
    figure = f'<g transform="translate({gutter},0)">{"".join(body)}{glyphs}</g>'
    notes = callouts(plan, states, gutter, total) if labels else ""
    return (
        f'<svg viewBox="0 0 {total} {plan.height}" width="{total * scale}" height="{plan.height * scale}" '
        f'xmlns="http://www.w3.org/2000/svg" font-family="Inter, -apple-system, sans-serif">{DEFS}{figure}{notes}</svg>'
    )


LEGEND = ["unhurt", "open", "festering", "scarred", "lasting", "lost", "prosthesis", "fatal"]


SWATCH = "M3,3 L19,3 Q21,3 21,5 L21,15 Q21,17 19,17 L3,17 Q1,17 1,15 L1,5 Q1,3 3,3 Z"


def swatch(state: str) -> str:
    part = Part("swatch", "", SWATCH, (11, 10))
    inner = styled(part, state) + glyph(part, state)
    return f'<svg viewBox="0 0 22 20" width="26" height="24">{DEFS}{inner}</svg>'


def page(title: str, subtitle: str, panels: list[tuple[str, str, str]]) -> str:
    cards = "".join(f'<div class="card"><div class="caption">{name}</div>{svg}<div class="note">{note}</div></div>' for name, svg, note in panels)
    legend = "".join(f'<span class="item">{swatch(state)}{STATE_LABEL.get(state, ("Unhurt", C["muted"]))[0]}</span>' for state in LEGEND)
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
body{{margin:0;background:{C["bg"]};font-family:Inter,-apple-system,sans-serif;color:{C["text"]}}}
.wrap{{padding:28px;display:flex;flex-direction:column;gap:16px;width:max-content}}
h1{{font-size:18px;letter-spacing:.14em;text-transform:uppercase;color:{C["gold"]};margin:0;font-weight:600}}
.sub{{font-size:13px;color:{C["muted"]};margin-top:-8px}}
.row{{display:flex;gap:18px}}
.card{{background:{C["card"]};border:1px solid {C["line"]};border-radius:14px;padding:18px 16px;display:flex;flex-direction:column;align-items:center;gap:8px}}
.caption{{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:{C["muted"]}}}
.note{{font-size:12px;color:{C["muted"]};max-width:330px;text-align:center;line-height:1.45}}
.legend{{display:flex;gap:18px;flex-wrap:wrap;font-size:13px;color:{C["muted"]};align-items:center}}
.item{{display:flex;align-items:center;gap:7px}}
</style></head><body><div class="wrap"><h1>{title}</h1><div class="sub">{subtitle}</div><div class="row">{cards}</div><div class="legend">{legend}</div></div></body></html>"""
