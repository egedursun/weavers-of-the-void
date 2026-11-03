import sys
from pathlib import Path

from render import C, Part, Plan, draw, page

OUT = Path(__file__).parent

FAR_FORELEG = (
    "M122,122 C128,138 134,152 134,168 C134,184 132,198 132,210 C132,215 130,219 127,221 "
    "C124,223 123,227 127,227 L142,227 C145,227 145,223 143,220 C143,214 144,206 145,196 "
    "C147,180 149,162 148,146 C147,136 142,128 134,124 Z"
)
FAR_HINDLEG = (
    "M222,100 C242,100 258,112 258,130 C258,144 250,154 244,162 C240,172 246,184 250,196 "
    "C250,204 246,212 242,218 C240,222 242,227 246,227 L232,227 C228,227 228,223 230,220 "
    "C232,214 234,206 232,198 C230,188 222,176 218,164 C212,148 208,130 210,116 C212,106 216,101 222,100 Z"
)
FAR_EAR = "M74,30 C73,19 76,10 81,4 C85,12 87,22 85,31 Z"
TORSO = (
    "M96,108 C100,90 112,80 128,78 C160,74 210,76 246,82 C266,86 280,98 282,114 "
    "C283,126 278,136 268,140 C254,140 240,138 228,140 C206,146 180,150 156,152 "
    "C136,154 116,152 104,144 C96,136 94,122 96,108 Z"
)
NECK = "M130,80 C118,72 106,62 98,52 L70,58 C70,74 74,92 84,108 C88,116 94,121 99,120 C97,108 101,96 109,90 C116,85 123,82 130,80 Z"
HEAD = "M99,46 C97,34 87,26 75,26 C63,26 55,34 53,44 C52,52 55,60 63,64 C73,68 87,66 95,60 C98,56 100,51 99,46 Z"
MUZZLE = "M57,42 C47,42 37,44 27,48 C22,50 20,54 22,57 C25,60 31,60 39,60 C47,60 55,58 61,56 C58,51 57,46 57,42 Z"
JAW = "M24,60 C32,63 44,64 56,62 C62,62 66,64 64,68 C58,71 46,71 36,69 C29,68 24,65 22,62 C22,61 23,60 24,60 Z"
EAR = "M85,32 C85,20 89,9 95,2 C100,12 101,24 97,35 Z"
EYE_NEAR = "M64,40 C66,37.5 71,37.5 74,40 C71,42.5 66,42.5 64,40 Z"
EYE_FAR = "M55,37.5 C56.3,36.3 58.7,36.3 60,37.5 C58.7,38.9 56.3,38.9 55,37.5 Z"
FORELEG = (
    "M102,118 C108,136 114,150 114,166 C114,182 112,196 112,208 C112,214 110,218 106,220 "
    "C102,222 100,227 104,227 L122,227 C126,227 126,223 124,220 C124,214 125,206 126,196 "
    "C128,178 130,160 130,142 C130,130 126,121 118,117 Z"
)
HINDLEG = (
    "M238,96 C260,96 278,110 278,128 C278,142 270,152 262,160 C258,172 264,184 268,196 "
    "C268,204 264,212 260,218 C258,222 260,227 264,227 L248,227 C244,227 244,223 246,220 "
    "C248,214 250,206 248,198 C246,188 238,176 234,164 C228,148 224,130 226,114 C228,104 232,98 238,96 Z"
)
TAIL = "M278,96 C294,98 306,110 312,126 C318,142 318,160 312,176 C306,168 300,156 294,144 C288,130 282,118 276,108 Z"
HEART = "M122,114 C119,110 114,112 115,117 C116,121 120,124 124,127 C128,124 132,121 132,117 C132,112 127,110 125,114 C124,115 123,115 122,114 Z"
LUNGS = "M114,94 C126,86 148,86 160,94 C164,104 162,116 154,122 C140,126 124,124 116,116 C110,110 110,100 114,94 Z"
GUT = "M166,100 C186,94 210,96 222,104 C226,116 224,128 214,134 C198,140 180,140 168,132 C160,122 160,108 166,100 Z"
GROIN = "M206,136 C212,135 220,137 222,142 C219,147 212,148 207,146 C204,143 204,139 206,136 Z"
NOSE_MARK = "M20,52 C20,49 23,48 25,49 C26.5,51 25.5,54 23,55 C21,55 20,54 20,52 Z"
DETAILS = [
    "M108,96 C114,108 120,116 126,120",
    "M240,104 C252,112 260,122 262,136",
    "M110,196 C113,198 121,198 124,196",
    "M128,200 C131,202 139,202 142,200",
    "M156,146 C176,148 196,146 214,140",
    "M30,56 C38,57 46,56 54,54",
    "M106,224 L106,227 M111,223 L111,227 M116,223 L116,227",
    "M250,224 L250,227 M255,223 L255,227 M260,224 L260,227",
    "M286,112 C292,124 296,138 296,152",
]


def quadruped(states: dict[str, str]) -> Plan:
    parts = [
        Part("right_foreleg", "Right foreleg", FAR_FORELEG, (139, 200), far=True),
        Part("right_hindleg", "Right hind leg", FAR_HINDLEG, (241, 200), far=True),
        Part("right_ear", "Right ear", FAR_EAR, (80, 18), far=True),
        Part("tail", "Tail", TAIL, (302, 140)),
        Part("torso", "Flank", TORSO, (190, 88)),
        Part("left_hindleg", "Left hind leg", HINDLEG, (258, 126)),
        Part("neck", "Neck", NECK, (98, 82)),
        Part("left_foreleg", "Left foreleg", FORELEG, (119, 176)),
        Part("head", "Head", HEAD, (84, 46)),
        Part("left_ear", "Left ear", EAR, (93, 18)),
        Part("face", "Muzzle", MUZZLE, (38, 51)),
        Part("jaw", "Jaws", JAW, (44, 66)),
        Part("left_eye", "Left eye", EYE_NEAR, (69, 40)),
        Part("right_eye", "Right eye", EYE_FAR, (57.5, 37.5), far=True),
        Part("lungs", "Lungs", LUNGS, (146, 104), inner=True),
        Part("heart", "Heart", HEART, (123, 119), inner=True),
        Part("gut", "Gut", GUT, (194, 118), inner=True),
        Part("groin", "Groin", GROIN, (213, 141), inner=True),
    ]
    marks = [f'<path d="{NOSE_MARK}" fill="#2c2d38" stroke="{C["stroke"]}" stroke-width="0.8"/>']
    if states.get("left_eye", "unhurt") not in {"lost", "prosthesis"}:
        marks.append(f'<circle cx="69.5" cy="40" r="1.9" fill="{C["stroke"]}"/>')
    return Plan("Four-legged", 340, 240, parts, DETAILS, marks)


if __name__ == "__main__":
    wounded = {
        "left_foreleg": "lost",
        "left_eye": "festering",
        "torso": "open",
        "jaw": "scarred",
        "tail": "lasting",
        "right_hindleg": "prosthesis",
    }
    fallen = {"lungs": "fatal", "neck": "open", "left_ear": "lost"}
    panels = [
        (
            "Unhurt",
            draw(quadruped({}), {}, scale=1.25),
            "Seen from its left side. The far legs, ear and eye sit darker behind; all four legs and both eyes take their own wounds.",
        ),
        (
            "Wounded",
            draw(quadruped(wounded), wounded, scale=1.25),
            "Foreleg lost, eye festering, flank open, jaws scarred, tail lamed for good, iron hind leg.",
        ),
        ("Fallen", draw(quadruped(fallen), fallen, scale=1.25), "Lungs crushed by the killing blow; an ear lost, the throat torn."),
    ]
    (OUT / sys.argv[1]).write_text(page("Four-legged body", "Wolves, horses, great cats and every beast that walks on four legs.", panels), encoding="utf-8")
