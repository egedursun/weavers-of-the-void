import re
import sys
from pathlib import Path

from render import C, Part, Plan, draw, page

OUT = Path(__file__).parent
WIDTH = 240
K = 0.5523


def mirror(path: str) -> str:
    return re.sub(r"(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)", lambda m: f"{WIDTH - float(m.group(1)):g},{m.group(2)}", path)


def flip(point: tuple[float, float]) -> tuple[float, float]:
    return (WIDTH - point[0], point[1])


def circle(x: float, y: float, r: float) -> str:
    k = r * K
    return (
        f"M{x - r},{y} C{x - r},{y - k} {x - k},{y - r} {x},{y - r} C{x + k},{y - r} {x + r},{y - k} {x + r},{y} "
        f"C{x + r},{y + k} {x + k},{y + r} {x},{y + r} C{x - k},{y + r} {x - r},{y + k} {x - r},{y} Z"
    )


HEAD = "M101,28 L139,28 L150,39 L150,72 L140,83 L100,83 L90,72 L90,39 Z"
CREST = "M112,28 L120,18 L128,28 Z"
GRILLE = "M103,65 L137,65 L139,77 L101,77 Z"
NECK = "M107,82 L133,82 L135,95 L105,95 Z"
CHEST = "M70,93 L170,93 L184,105 L180,170 L164,196 L150,206 L90,206 L76,196 L60,170 L56,105 Z"
PELVIS = "M88,206 L152,206 L146,228 L94,228 Z"
PAULDRON = "M58,92 C42,91 31,101 31,116 C31,124 36,129 45,129 L67,129 L72,104 Z"
UPPER = "M41,129 L65,129 L63,167 L43,167 Z"
FOREARM = "M37,181 L67,181 L65,228 L41,228 Z"
HAND = "M35,229 L70,229 L72,252 L33,252 Z"
THUMB = "M70,236 L79,240 L77,253 L70,251 Z"
FINGERS = " ".join(f"M{x},252 L{x + 6.4},252 L{x + 6},268 C{x + 6},270 {x + 0.4},270 {x + 0.4},268 Z" for x in (34.2, 42.2, 50.2, 58.2))
THIGH = "M82,229 L113,229 L111,279 L84,279 Z"
SHIN = "M79,297 L114,297 L115,340 L78,340 Z"
BASE = "M73,340 L117,340 L119,357 L69,357 Z"
DETAILS = [
    "M60,170 L180,170",
    "M76,196 L164,196",
    "M88,120 L104,104 M152,120 L136,104",
    "M106,69 L134,69 M105,72.5 L135,72.5",
    "M90,52 L150,52",
    "M43,148 L63,148",
    "M40,204 L66,204",
    "M84,254 L112,254",
    "M79,318 L115,318",
    "M98,104 L98,93 M142,104 L142,93",
]
RIVETS = [
    (66, 100),
    (174, 100),
    (64, 164),
    (176, 164),
    (96, 200),
    (144, 200),
    (94, 34),
    (146, 34),
    (94, 77),
    (146, 77),
    (46, 133),
    (60, 133),
    (42, 185),
    (62, 185),
    (86, 233),
    (109, 233),
    (83, 301),
    (110, 301),
    (76, 344),
    (114, 344),
]
RUNES = [
    "M84,124 L84,146 M84,130 L92,124 M84,138 L92,132",
    "M156,124 L156,146 M156,128 L148,136 L156,144",
    "M114,96 L120,90 L126,96",
    "M112,36 L120,44 L128,36 M120,44 L120,48",
    "M93,250 L101,242 L101,262 M139,250 L147,242 L147,262",
]


def construct(states: dict[str, str]) -> Plan:
    arm = " | ".join((UPPER, circle(53, 174, 9.5), FOREARM, PAULDRON))
    leg = " | ".join((THIGH, circle(97, 288, 10.5), SHIN, BASE))
    parts = [
        Part("right_leg", "Right leg", leg, (100, 316)),
        Part("left_leg", "Left leg", mirror(leg), flip((100, 316))),
        Part("torso", "Frame", " | ".join((NECK, PELVIS, CHEST)), (172, 150)),
        Part("right_arm", "Right arm", arm, (52, 150)),
        Part("left_arm", "Left arm", mirror(arm), flip((52, 150))),
        Part("right_hand", "Right hand", HAND + " " + THUMB, (52, 240)),
        Part("left_hand", "Left hand", mirror(HAND + " " + THUMB), flip((52, 240))),
        Part("fingers", "Fingers", FINGERS + " " + mirror(FINGERS), (44, 262)),
        Part("head", "Rune head", HEAD + " " + CREST, (120, 32)),
        Part("jaw", "Voice grille", GRILLE, (120, 71)),
        Part("right_eye", "Right lens", circle(108, 51, 6.2), (108, 51)),
        Part("left_eye", "Left lens", circle(132, 51, 6.2), (132, 51)),
        Part("core", "Animating core", circle(120, 140, 15), (120, 140), inner=True),
    ]
    rivets = "".join(f'<circle cx="{x}" cy="{y}" r="1.5" fill="#0b0c12" stroke="{C["stroke"]}" stroke-width="0.5"/>' for x, y in RIVETS)
    runes = "".join(f'<path d="{path}" fill="none" stroke="{C["gold"]}" stroke-opacity="0.55" stroke-width="1.3" stroke-linecap="round"/>' for path in RUNES)
    bevels = "".join(
        f'<path d="{path}" fill="none" stroke="#ffffff" stroke-opacity="0.07" stroke-width="1.6"/>'
        for path in ("M72,96 L168,96", "M103,31 L137,31", "M43,131 L63,131", "M39,183 L65,183", "M86,231 L114,231", "M84,299 L116,299")
    )
    marks = [rivets, runes, bevels]
    marks.append(f'<path d="{circle(120, 140, 19)}" fill="#0b0c12" stroke="{C["stroke"]}" stroke-width="1"/>')
    for x in (114, 120, 126):
        marks.append(f'<line x1="{x}" y1="123" x2="{x}" y2="157" stroke="{C["stroke"]}" stroke-width="1.1"/>')
    if states.get("core", "unhurt") == "unhurt":
        marks.append(
            '<defs><radialGradient id="corelight" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#ffe2a0" stop-opacity="0.9"/>'
            f'<stop offset="0.5" stop-color="{C["gold"]}" stop-opacity="0.45"/><stop offset="1" stop-color="{C["gold"]}" stop-opacity="0"/></radialGradient></defs>'
            '<circle cx="120" cy="140" r="17" fill="url(#corelight)"/>'
        )
    for side, x in (("right", 108), ("left", 132)):
        if states.get(f"{side}_eye", "unhurt") == "unhurt":
            marks.append(
                f'<circle cx="{x}" cy="51" r="3.2" fill="#9fdcff" fill-opacity="0.85"/><circle cx="{x}" cy="51" r="8" fill="#9fdcff" fill-opacity="0.1"/>'
            )
    underlay = (
        '<defs><filter id="kshadow" x="-30%" y="-80%" width="160%" height="260%"><feGaussianBlur stdDeviation="5"/></filter></defs>'
        '<ellipse cx="120" cy="358" rx="74" ry="6" fill="#000" opacity="0.6" filter="url(#kshadow)"/>'
    )
    return Plan("Construct", WIDTH, 366, parts, DETAILS + [mirror(line) for line in DETAILS[5:7]], marks, underlay)


if __name__ == "__main__":
    wounded = {"right_arm": "lost", "left_eye": "lasting", "torso": "open", "jaw": "scarred", "left_hand": "prosthesis", "right_leg": "lasting"}
    fallen = {"core": "fatal", "head": "open", "left_arm": "lost"}
    panels = [
        (
            "Unhurt",
            draw(construct({}), {}, scale=1.35),
            "A made body of stone and bronze. It does not bleed, fester or heal by itself; it must be mended. The animating core is its heart.",
        ),
        (
            "Wounded",
            draw(construct(wounded), wounded, scale=1.35),
            "An arm sheared off, a lens cracked for good, the frame breached, the grille dented, a replacement hand, a leg seized.",
        ),
        ("Fallen", draw(construct(fallen), fallen, scale=1.35), "The core shattered and the light gone out; the head split, an arm torn away."),
    ]
    (OUT / sys.argv[1]).write_text(
        page("Construct body", "Golems, automatons, animated statues and every body that was made rather than born.", panels), encoding="utf-8"
    )
