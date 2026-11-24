import sys
from pathlib import Path

from forms import heart, mirrored, outline, profile, tapered
from render import C, Part, Plan, draw, ellipse, page

OUT = Path(__file__).parent
WIDTH, HEIGHT, AXIS = 300, 330, 150.0
MANTLE = profile(AXIS, [(16, 0.5), (22, 30), (40, 54), (70, 64), (104, 63), (128, 56), (146, 40)])
HEAD = profile(AXIS, [(138, 28), (150, 40), (164, 45), (180, 40), (194, 28), (202, 10)])
BEAK = outline([(144, 187), (156, 187), (154, 195), (150, 201), (146, 195)])
GILL = outline([(116, 112), (121, 120), (122, 134), (118, 144), (114, 134), (113, 121)])
EYE = outline([(118, 166), (126, 160), (136, 163), (139, 168), (131, 174), (121, 173)])
SPREAD = (-52.0, -36.0, -20.0, -7.0, 7.0, 20.0, 36.0, 52.0)


def arm(offset: float) -> str:
    side = 1 if offset > 0 else -1
    root = AXIS + offset * 0.72
    bend = abs(offset) / 52
    spine = [
        (root, 192),
        (root + offset * 0.3, 226),
        (root + offset * 0.9, 262),
        (root + offset * 1.05 + side * 10 * bend, 292),
        (root + offset * 0.8 + side * 24 * bend, 312 - abs(offset) * 0.3),
    ]
    return tapered(spine, 15 if abs(offset) > 30 else 12.5, 2.2)


ARMS = " | ".join(arm(offset) for offset in SPREAD)
DETAILS = [
    "M126,40 C140,34 160,34 174,40",
    "M112,80 C120,74 128,72 136,72",
    "M188,80 C180,74 172,72 164,72",
    "M134,152 C144,156 156,156 166,152",
]


def tentacled(states: dict[str, str]) -> Plan:
    parts = [
        Part("tentacles", "Tentacles", ARMS, (204, 292)),
        Part("core", "Mantle", MANTLE, (176, 58)),
        Part("gills", "Gills", GILL + " " + mirrored(GILL, AXIS), (116, 128)),
        Part("head", "Head", HEAD, (196, 172)),
        Part("beak", "Beak", BEAK, (150, 194), subtle=True),
        Part("right_eye", "Right eye", EYE, (128, 167)),
        Part("left_eye", "Left eye", mirrored(EYE, AXIS), (172, 167)),
        Part("heart", "Heart", heart(150, 72, 8), (150, 72), inner=True),
        Part("gut", "Gut", ellipse(150, 104, 18, 14), (150, 104), inner=True),
        Part("groin", "Groin", ellipse(150, 130, 8, 6), (150, 130), inner=True),
    ]
    marks = []
    for side, x in (("right", 128.5), ("left", 171.5)):
        if states.get(f"{side}_eye", "unhurt") not in {"lost", "prosthesis"}:
            marks.append(f'<path d="{ellipse(x, 167.5, 3.6, 1.6)}" fill="{C["gold"]}" fill-opacity="0.6"/>')
        elif states.get(f"{side}_eye") == "prosthesis":
            marks.append(f'<path d="{ellipse(x, 167.5, 3.6, 1.6)}" fill="#2a3b55" stroke="#9fc3ff" stroke-width="0.4"/>')
    underlay = (
        '<defs><filter id="oshadow2" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="4"/></filter></defs>'
        f'<g filter="url(#oshadow2)" opacity="0.45" transform="translate(4,7)"><path d="{MANTLE} {HEAD}" fill="#000"/></g>'
    )
    return Plan("Tentacled", WIDTH, HEIGHT, parts, DETAILS, marks, underlay)


if __name__ == "__main__":
    wounded = {"tentacles": "lost", "core": "open", "left_eye": "scarred"}
    fallen = {"heart": "fatal", "gills": "festering"}
    panels = [
        (
            "Unhurt",
            draw(tentacled({}), {}),
            "A mantle over a head ringed by eight arms; the beak sits between them.",
        ),
        (
            "Wounded",
            draw(tentacled(wounded), wounded),
            "Arms torn away, the mantle open, an eye scarred.",
        ),
        (
            "Fallen",
            draw(tentacled(fallen), fallen),
            "The heart under the mantle takes the killing blow.",
        ),
    ]
    (OUT / sys.argv[1]).write_text(
        page("Tentacled body", "Bodies that grasp and move with many arms.", panels),
        encoding="utf-8",
    )
