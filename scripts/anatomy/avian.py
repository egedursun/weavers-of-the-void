import re
import sys
from pathlib import Path

from render import C, Part, Plan, draw, ellipse, page

OUT = Path(__file__).parent
WIDTH = 360
PAIR = re.compile(r"(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)")


def mirror(path: str) -> str:
    return PAIR.sub(lambda m: f"{WIDTH - float(m.group(1)):g},{m.group(2)}", path)


def flip(point: tuple[float, float]) -> tuple[float, float]:
    return (WIDTH - point[0], point[1])


HEAD = "M180,30 C192,30 200,38 201,48 C202,56 198,64 192,68 C188,70 184,71 180,71 C176,71 172,70 168,68 C162,64 158,56 159,48 C160,38 168,30 180,30 Z"
BEAK = "M173,54 C175,50 185,50 187,54 C189,60 188,68 184,76 C183,80 181,83 178.5,85 C178,80 176,74 175,68 C173,64 172,58 173,54 Z"
CERE = "M173.5,57 C177,59 183,59 186.5,57"
EYE = "M164,48.5 C166,45.5 173,45.5 175,48.5 C173,51.5 166,51.5 164,48.5 Z"
BROW = "M162,45 C166,41.5 172,41 177,43.5"
IRIS = ellipse(169.6, 48.5, 2, 2)
NECK = "M167,64 C165,74 161,84 156,96 C164,100 172,101 180,101 C188,101 196,100 204,96 C199,84 195,74 193,64 C188,69 172,69 167,64 Z"
TORSO = "M158,96 C146,104 142,122 144,144 C146,166 158,184 180,190 C202,184 214,166 216,144 C218,122 214,104 202,96 C194,92 166,92 158,96 Z"
WING = (
    "M162,100 C140,84 110,62 76,48 C64,43 50,42 38,44 C28,46 18,50 10,56 C20,58 30,58 38,58 "
    "C28,64 18,70 12,78 C22,79 32,77 40,74 C32,82 24,90 18,98 C28,97 38,94 46,89 "
    "C40,98 34,107 30,116 C40,113 49,107 56,101 C52,110 50,118 50,126 C58,121 64,116 70,111 "
    "C70,119 72,126 76,132 C82,126 88,120 92,115 C94,123 98,129 104,134 C108,127 112,121 116,117 "
    "C120,124 126,129 132,132 C134,124 138,118 142,114 C148,118 154,120 158,118 Z"
)
WING_LINES = [
    "M76,48 C96,62 124,82 156,104",
    "M38,58 C60,60 84,66 110,78",
    "M40,74 C62,76 84,82 106,92",
    "M46,89 C66,92 86,96 104,104",
    "M56,101 C74,104 92,108 110,112",
    "M70,111 C90,112 112,114 134,112",
]
LEG = (
    "M162,176 C158,188 158,198 162,206 L164,222 C160,226 154,232 152,236 C156,236 160,233 163,230 "
    "C163,235 163,240 165,243 C167,239 168,235 168,231 C170,235 174,238 177,238 C176,234 174,229 171,225 "
    "L170,206 C174,198 175,188 172,178 Z"
)
TAIL = "M168,184 C163,200 160,222 162,246 C168,252 174,254 180,254 C186,254 192,252 198,246 C200,222 197,200 192,184 C186,188 174,188 168,184 Z"
TAIL_LINES = ["M172,196 L169,250", "M180,196 L180,253", "M188,196 L191,250"]
LUNGS = (
    "M176,102 C167,102 161,110 161,119 C161,127 166,132 174,131 C176,121 177,111 176,102 Z "
    "M184,102 C193,102 199,110 199,119 C199,127 194,132 186,131 C184,121 183,111 184,102 Z"
)
HEART = "M178,122 C175,118 170,120 171,125 C172,129 176,132 180,135 C184,132 188,129 189,125 C190,120 185,118 182,122 C181,123 179,123 178,122 Z"
GUT = "M166,142 C172,138 188,138 194,142 C198,152 197,164 190,170 C185,174 175,174 170,170 C163,164 162,152 166,142 Z"
GROIN = "M172,174 C176,172 184,172 188,174 C188,180 185,183 180,184 C175,183 172,180 172,174 Z"
BREAST = [
    "M168,110 C172,113 176,114 180,114 C184,114 188,113 192,110",
    "M162,128 C168,133 174,135 180,135 C186,135 192,133 198,128",
    "M160,150 C166,155 173,157 180,157 C187,157 194,155 200,150",
    "M164,170 C169,174 174,176 180,176 C186,176 191,174 196,170",
    "M168,82 C172,86 176,87 180,87 C184,87 188,86 192,82",
    "M160,196 C162,200 164,204 166,206",
]


def avian(states: dict[str, str]) -> Plan:
    parts = [
        Part("tail", "Tail feathers", TAIL, (180, 230)),
        Part("right_wing", "Right wing", WING, (80, 84)),
        Part("left_wing", "Left wing", mirror(WING), flip((80, 84))),
        Part("right_leg", "Right talon", LEG, (166, 214)),
        Part("left_leg", "Left talon", mirror(LEG), flip((166, 214))),
        Part("torso", "Breast", TORSO, (204, 140)),
        Part("neck", "Neck", NECK, (180, 92)),
        Part("head", "Head", HEAD, (180, 36)),
        Part("right_eye", "Right eye", EYE, (169.6, 48.5)),
        Part("left_eye", "Left eye", mirror(EYE), flip((169.6, 48.5))),
        Part("jaw", "Beak", BEAK, (180, 66)),
        Part("lungs", "Lungs", LUNGS, (167, 116), inner=True),
        Part("heart", "Heart", HEART, (180, 126), inner=True),
        Part("gut", "Gut", GUT, (180, 156), inner=True),
        Part("groin", "Groin", GROIN, (180, 178), inner=True),
    ]
    details = [*WING_LINES, *(mirror(line) for line in WING_LINES), *TAIL_LINES, *BREAST, *(mirror(line) for line in BREAST[-1:]), BROW, mirror(BROW), CERE]
    marks = []
    for side, iris in (("right", IRIS), ("left", mirror(IRIS))):
        if states.get(f"{side}_eye", "unhurt") not in {"lost", "prosthesis"}:
            marks.append(f'<path d="{iris}" fill="{C["gold"]}" fill-opacity="0.55" stroke="{C["stroke"]}" stroke-width="0.5"/>')
    return Plan("Winged", WIDTH, 262, parts, details, marks)


if __name__ == "__main__":
    wounded = {
        "left_wing": "lost",
        "right_wing": "festering",
        "right_eye": "scarred",
        "jaw": "lasting",
        "torso": "open",
        "left_leg": "prosthesis",
    }
    fallen = {"heart": "fatal", "neck": "open", "tail": "scarred"}
    panels = [
        ("Unhurt", draw(avian({}), {}, scale=1.15), "Wings spread to show both; each wing, eye and talon takes its own wound. Losing a wing grounds the bird."),
        (
            "Wounded",
            draw(avian(wounded), wounded, scale=1.15),
            "A wing torn away, the other festering, an eye scarred, beak cracked for good, breast open, a silver talon.",
        ),
        ("Fallen", draw(avian(fallen), fallen, scale=1.15), "Struck through the heart; the throat open, old scars on the tail."),
    ]
    (OUT / sys.argv[1]).write_text(
        page("Winged body", "Eagles, owls, rocs, harpies' mounts and every beast that flies on feathered wings.", panels), encoding="utf-8"
    )
