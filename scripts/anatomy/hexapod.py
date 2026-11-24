import sys
from pathlib import Path

from forms import heart, outline, profile
from insectoid import (
    ANTENNA,
    ANTENNA_W,
    EYE,
    FORELEG,
    FORELEG_W,
    HEAD,
    HEIGHT,
    HINDLEG,
    HINDLEG_W,
    MIDLEG,
    MIDLEG_W,
    WIDTH,
    facets,
    flip,
    joints,
    limb,
    mirror,
)
from render import C, Part, Plan, draw, ellipse, page

OUT = Path(__file__).parent
BODY = profile(
    150,
    [
        (83, 13),
        (96, 24),
        (120, 29),
        (150, 30),
        (186, 34),
        (222, 33),
        (250, 25),
        (270, 13),
        (281, 4),
    ],
)
LUNGS = ellipse(139, 122, 9, 18) + " " + ellipse(161, 122, 9, 18)
POUCH = outline([(130, 227), (150, 221), (170, 227), (167, 239), (150, 244), (133, 239)])
DETAILS = [
    "M137,104 C144,107 156,107 163,104",
    "M126,168 C138,174 162,174 174,168",
    "M121,204 C136,212 164,212 179,204",
    "M128,248 C140,254 160,254 172,248",
    "M142,48 C146,52 154,52 158,48",
    "M150,52 L150,78",
]


def hexapod(states: dict[str, str]) -> Plan:
    parts = [
        Part("right_hindleg", "Right hind leg", limb(HINDLEG, HINDLEG_W), (98, 186)),
        Part(
            "left_hindleg",
            "Left hind leg",
            mirror(limb(HINDLEG, HINDLEG_W)),
            flip((98, 186)),
        ),
        Part("right_midleg", "Right middle leg", limb(MIDLEG, MIDLEG_W), (88, 136)),
        Part(
            "left_midleg",
            "Left middle leg",
            mirror(limb(MIDLEG, MIDLEG_W)),
            flip((88, 136)),
        ),
        Part("right_foreleg", "Right foreleg", limb(FORELEG, FORELEG_W), (102, 76)),
        Part(
            "left_foreleg",
            "Left foreleg",
            mirror(limb(FORELEG, FORELEG_W)),
            flip((102, 76)),
        ),
        Part("torso", "Body", BODY, (176, 206)),
        Part("right_antenna", "Right antenna", limb(ANTENNA, ANTENNA_W), (112, 25)),
        Part(
            "left_antenna",
            "Left antenna",
            mirror(limb(ANTENNA, ANTENNA_W)),
            flip((112, 25)),
        ),
        Part("head", "Head", HEAD, (150, 70)),
        Part("right_eye", "Right eye", EYE, (130, 57.5)),
        Part("left_eye", "Left eye", mirror(EYE), flip((130, 57.5))),
        Part("lungs", "Lungs", LUNGS, (139, 122), inner=True),
        Part("heart", "Heart", heart(150, 150, 8), (150, 150), inner=True),
        Part("gut", "Gut", ellipse(150, 192, 17, 24), (150, 192), inner=True),
        Part("pouch", "Brood pouch", POUCH, (166, 233), inner=True),
        Part("groin", "Groin", ellipse(150, 261, 7, 8), (150, 261), inner=True),
    ]
    details = [
        *DETAILS,
        joints(FORELEG),
        mirror(joints(FORELEG)),
        joints(MIDLEG),
        mirror(joints(MIDLEG)),
        joints(HINDLEG),
        mirror(joints(HINDLEG)),
    ]
    marks = [
        '<path d="M150,98 C164,104 172,130 172,170 C172,214 164,246 150,262 C146,240 144,206 144,170 C144,132 146,108 150,98 Z" fill="#ffffff" fill-opacity="0.035"/>'
    ]
    for side, centre in (("right", (130.5, 57.5)), ("left", flip((130.5, 57.5)))):
        if states.get(f"{side}_eye", "unhurt") not in {"lost", "prosthesis"}:
            marks.append(f'<path d="{facets(*centre)}" fill="{C["gold"]}" fill-opacity="0.35"/>')
    underlay = (
        '<defs><filter id="xshadow" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="3"/></filter></defs>'
        f'<g filter="url(#xshadow)" opacity="0.5" transform="translate(3,5)"><path d="{BODY} {HEAD}" fill="#000"/></g>'
    )
    return Plan("Six-limbed", WIDTH, HEIGHT, parts, details, marks, underlay)


if __name__ == "__main__":
    wounded = {
        "left_midleg": "lost",
        "right_antenna": "scarred",
        "torso": "open",
        "pouch": "festering",
    }
    fallen = {"heart": "fatal", "left_foreleg": "open"}
    panels = [
        (
            "Unhurt",
            draw(hexapod({}), {}),
            "Six limbs on one long body; the brood pouch sits dashed beneath.",
        ),
        (
            "Wounded",
            draw(hexapod(wounded), wounded),
            "A middle leg lost, an antenna scarred, the body open, the pouch festering.",
        ),
        ("Fallen", draw(hexapod(fallen), fallen), "The heart takes the killing blow."),
    ]
    (OUT / sys.argv[1]).write_text(
        page("Six-limbed body", "Beings with six limbs and feelers.", panels),
        encoding="utf-8",
    )
