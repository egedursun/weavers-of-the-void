import sys
from pathlib import Path

from arboreal import mirror, tapered
from render import C, Part, Plan, draw, ellipse, page

OUT = Path(__file__).parent

SHROUD = (
    "M150,24 C170,24 186,38 190,58 C194,76 198,90 212,102 C223,111 227,128 225,146 C223,170 217,196 215,222 "
    "C213,246 216,266 222,286 Q214,282 208,276 Q206,292 200,304 Q194,290 188,280 Q182,298 172,312 "
    "Q168,294 164,284 Q158,302 150,316 Q144,300 140,286 Q132,304 124,312 Q122,294 118,282 Q110,296 100,302 "
    "Q100,288 96,276 Q88,282 80,288 C86,266 87,244 85,222 C83,196 77,170 75,146 C73,128 77,111 88,102 "
    "C102,90 106,76 110,58 C114,38 130,24 150,24 Z"
)
SLEEVE = "M112,104 C96,112 78,130 62,152 C52,165 42,174 33,180 C42,187 53,189 62,186 C66,172 76,156 90,142 C100,132 110,126 118,122 Z"
FINGERS = [
    tapered([(38, 184), (32, 196), (28, 210)], [4.2, 3, 1.4], 18, 1.4),
    tapered([(45, 187), (41, 201), (39, 216)], [4.4, 3, 1.4], 18, 1.4),
    tapered([(52, 188), (51, 202), (51, 216)], [4.2, 3, 1.4], 18, 1.4),
    tapered([(58, 186), (61, 198), (64, 210)], [3.8, 2.6, 1.2], 18, 1.4),
]
HOOD = "M129,60 C129,45 171,45 171,60 C173,78 167,95 150,99 C133,95 127,78 129,60 Z"
VISAGE = "M137,63 C139,53 161,53 163,63 C165,76 160,88 150,92 C140,88 135,76 137,63 Z"
ESSENCE = ellipse(150, 128, 13, 13)
FOLDS = [
    "M120,112 C117,150 113,196 110,262",
    "M134,108 C134,150 132,204 130,282",
    "M166,108 C166,150 168,204 170,282",
    "M180,112 C183,150 187,196 190,262",
    "M112,64 C116,84 124,98 136,104",
    "M188,64 C184,84 176,98 164,104",
    "M74,140 C66,152 58,164 48,174",
]
FACE_LINES = ["M141,73 C142,78 142,82 141,86", "M159,73 C158,78 158,82 159,86", "M144,62 C146,60 148,60 149,61", "M151,61 C152,60 154,60 156,62"]


def incorporeal(states: dict[str, str]) -> Plan:
    sleeve = SLEEVE + " " + " ".join(FINGERS)
    torso = " | ".join((sleeve, mirror(sleeve), SHROUD))
    parts = [
        Part("torso", "Shroud", torso, (204, 210)),
        Part("face", "Visage", VISAGE, (150, 58), prelude=f'<path d="{HOOD}" fill="#05060a" fill-opacity="0.92"/>'),
        Part("core", "Essence", ESSENCE, (150, 128)),
    ]
    marks = []
    if states.get("face", "unhurt") not in {"lost"}:
        for x in (143.5, 156.5):
            marks.append(f'<ellipse cx="{x}" cy="68" rx="3.6" ry="2.4" fill="#05060a"/>')
            marks.append(f'<ellipse cx="{x}" cy="68" rx="1.7" ry="1.2" fill="#9fdcff"/>')
            marks.append(f'<circle cx="{x}" cy="68" r="6" fill="#9fdcff" fill-opacity="0.12"/>')
    if states.get("core", "unhurt") == "unhurt":
        marks.append(
            '<defs><radialGradient id="essence" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#e6f6ff" stop-opacity="0.95"/>'
            '<stop offset="0.45" stop-color="#9fdcff" stop-opacity="0.55"/><stop offset="1" stop-color="#9fdcff" stop-opacity="0"/></radialGradient></defs>'
            '<circle cx="150" cy="128" r="22" fill="url(#essence)"/><circle cx="150" cy="128" r="6" fill="#ffffff" fill-opacity="0.8"/>'
        )
    marks.append(
        '<defs><linearGradient id="fade" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0f1017" stop-opacity="0"/>'
        '<stop offset="1" stop-color="#0f1017" stop-opacity="1"/></linearGradient></defs>'
        '<rect x="60" y="236" width="180" height="80" fill="url(#fade)"/>'
    )
    marks.extend(f'<path d="{path}" fill="none" stroke="{C["detail"]}" stroke-width="0.8"/>' for path in FACE_LINES)
    if states.get("face", "unhurt") != "lost":
        marks.append('<ellipse cx="150" cy="82" rx="3.2" ry="4.2" fill="#05060a"/>')
    underlay = (
        '<defs><filter id="ghostglow" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="9"/></filter></defs>'
        f'<g filter="url(#ghostglow)" opacity="0.22"><path d="{SHROUD} {SLEEVE} {mirror(SLEEVE)}" fill="#9fdcff"/></g>'
    )
    return Plan("Incorporeal", 300, 320, parts, [*FOLDS, mirror(FOLDS[-1])], marks, underlay)


if __name__ == "__main__":
    wounded = {"torso": "open", "face": "scarred"}
    hurt = {"torso": "lasting", "face": "festering"}
    fallen = {"core": "fatal", "torso": "lost"}
    panels = [
        (
            "Unhurt",
            draw(incorporeal({}), {}, scale=1.25),
            "A shade with no flesh. Blades, arrows and fists pass through it; only magic, holy fire and the void can wound its shroud, its visage and its essence.",
        ),
        ("Wounded", draw(incorporeal(hurt), hurt, scale=1.25), "Its shroud worn thin for good by holy fire; its visage blistered and festering with void-rot."),
        ("Fallen", draw(incorporeal(fallen), fallen, scale=1.25), "The essence shattered; the shroud unravels into nothing."),
    ]
    (OUT / sys.argv[1]).write_text(page("Incorporeal body", "Ghosts, wraiths, spirits and every being without flesh.", panels), encoding="utf-8")
