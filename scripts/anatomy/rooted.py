import sys
from pathlib import Path

from forms import mirrored, profile, tapered
from render import Part, Plan, draw, ellipse, page

OUT = Path(__file__).parent
WIDTH, HEIGHT, AXIS = 300, 330, 150.0
TRUNK = profile(AXIS, [(68, 6), (76, 13), (94, 18), (128, 17), (168, 19), (208, 22), (236, 27), (254, 37), (266, 52)])
ROOTS = " | ".join(
    tapered(spine, root, 2.2)
    for spine, root in (
        ([(AXIS - 22, 258), (AXIS - 50, 276), (AXIS - 82, 288), (AXIS - 116, 306)], 14),
        ([(AXIS - 10, 262), (AXIS - 22, 284), (AXIS - 36, 300), (AXIS - 50, 318)], 12),
        ([(AXIS, 264), (AXIS + 2, 286), (AXIS - 2, 302), (AXIS + 4, 322)], 11),
        ([(AXIS + 10, 262), (AXIS + 22, 284), (AXIS + 36, 300), (AXIS + 50, 318)], 12),
        ([(AXIS + 22, 258), (AXIS + 50, 276), (AXIS + 82, 288), (AXIS + 116, 306)], 14),
    )
)
BRANCH = " | ".join(
    (
        tapered([(AXIS - 12, 156), (AXIS - 44, 140), (AXIS - 70, 106), (AXIS - 86, 64)], 19, 3.6),
        tapered([(AXIS - 64, 116), (AXIS - 82, 116), (AXIS - 100, 108), (AXIS - 116, 92)], 8, 2.2),
    )
)
DETAILS = [
    "M142,96 C139,124 142,152 140,180",
    "M158,104 C161,134 157,166 160,198",
    "M146,214 C144,230 147,244 142,258",
    "M156,222 C158,236 156,248 160,260",
    "M140,82 C146,79 154,79 160,82",
]


def rooted(states: dict[str, str]) -> Plan:
    parts = [
        Part("roots", "Roots", ROOTS, (60, 300)),
        Part("right_branch", "Right branch", BRANCH, (66, 100)),
        Part("left_branch", "Left branch", mirrored(BRANCH, AXIS), (234, 100)),
        Part("torso", "Trunk", TRUNK, (168, 212)),
        Part("core", "Heartwood", ellipse(AXIS, 178, 8, 44), (AXIS, 178), inner=True),
    ]
    underlay = (
        '<defs><filter id="pshadow" x="-30%" y="-60%" width="160%" height="220%"><feGaussianBlur stdDeviation="5"/></filter></defs>'
        f'<path d="{ellipse(AXIS, 318, 124, 9)}" fill="#000" opacity="0.5" filter="url(#pshadow)"/>'
    )
    return Plan("Rooted", WIDTH, HEIGHT, parts, DETAILS, [], underlay)


if __name__ == "__main__":
    wounded = {"left_branch": "lost", "roots": "scarred", "torso": "open"}
    fallen = {"core": "fatal"}
    panels = [
        (
            "Unhurt",
            draw(rooted({}), {}),
            "A trunk held fast by its roots, reaching with two branches.",
        ),
        (
            "Wounded",
            draw(rooted(wounded), wounded),
            "A branch lost, the roots scarred, the trunk split.",
        ),
        (
            "Fallen",
            draw(rooted(fallen), fallen),
            "The heartwood takes the killing blow.",
        ),
    ]
    (OUT / sys.argv[1]).write_text(
        page("Rooted body", "Beings that live held to the ground.", panels),
        encoding="utf-8",
    )
