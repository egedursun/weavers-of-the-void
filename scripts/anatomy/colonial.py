import sys
from pathlib import Path

from forms import blob, outline, tapered
from render import C, Part, Plan, draw, ellipse, page

OUT = Path(__file__).parent
WIDTH, HEIGHT = 300, 230
CELLS = (
    (124, 108, 32),
    (172, 98, 28),
    (196, 140, 30),
    (146, 150, 31),
    (100, 148, 22),
    (214, 102, 19),
    (160, 124, 22),
)
BODY = " | ".join(blob(x, y, r, 0.04, i * 1.3) for i, (x, y, r) in enumerate(CELLS))
PODS = " | ".join(
    tapered(spine, root, 3)
    for spine, root in (
        ([(98, 112), (72, 102), (52, 96), (32, 80)], 16),
        ([(92, 164), (74, 182), (60, 196), (44, 214)], 14),
        ([(218, 158), (238, 172), (256, 182), (278, 196)], 15),
        ([(222, 90), (238, 72), (250, 56), (262, 36)], 13),
    )
)
CORE = outline([(150, 112), (166, 116), (170, 128), (160, 140), (142, 140), (134, 128), (138, 116)])
DETAILS = [
    "M110,98 C116,92 126,90 134,92",
    "M184,132 C190,128 198,128 204,132",
    "M134,158 C140,162 150,163 158,160",
]


def colonial(states: dict[str, str]) -> Plan:
    parts = [
        Part("pseudopods", "Pseudopods", PODS, (40, 90)),
        Part("torso", "Body", BODY, (206, 150)),
        Part("eye", "Eye", ellipse(172, 96, 8, 7), (172, 96)),
        Part("core", "Core", CORE, (150, 126), inner=True),
    ]
    marks = []
    state = states.get("eye", "unhurt")
    if state not in {"lost", "prosthesis"}:
        marks.append(f'<circle cx="172" cy="96" r="3.1" fill="{C["gold"]}" fill-opacity="0.6"/>')
    elif state == "prosthesis":
        marks.append('<circle cx="172" cy="96" r="3.1" fill="#2a3b55" stroke="#9fc3ff" stroke-width="0.4"/>')
    underlay = (
        '<defs><filter id="cshadow" x="-20%" y="-30%" width="140%" height="170%"><feGaussianBlur stdDeviation="5"/></filter></defs>'
        f'<g filter="url(#cshadow)" opacity="0.45" transform="translate(4,8)"><path d="{BODY.replace(" | ", " ")}" fill="#000"/></g>'
    )
    return Plan("Colonial", WIDTH, HEIGHT, parts, DETAILS, marks, underlay)


if __name__ == "__main__":
    wounded = {"pseudopods": "lost", "torso": "festering"}
    fallen = {"core": "fatal"}
    panels = [
        (
            "Unhurt",
            draw(colonial({}), {}),
            "Many bodies grown into one, reaching with pseudopods.",
        ),
        (
            "Wounded",
            draw(colonial(wounded), wounded),
            "Pseudopods lost, the bodies festering.",
        ),
        (
            "Fallen",
            draw(colonial(fallen), fallen),
            "The shared core takes the killing blow.",
        ),
    ]
    (OUT / sys.argv[1]).write_text(page("Colonial body", "One being made of many.", panels), encoding="utf-8")
