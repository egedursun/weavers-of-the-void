import math
import re
import sys
from pathlib import Path

from colossal import ramp
from human import NAVEL
from humanoid import humanoid
from render import C, Part, Plan, draw, page

OUT = Path(__file__).parent
SHIFT = 60.0
WIDTH = 320
PAIR = re.compile(r"(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)")


def vertical(y: float) -> float:
    if y < 62:
        return 30 + (y - 10) * 0.9
    if y < 214:
        return 30 + 52 * 0.9 + (y - 62)
    return 30 + 52 * 0.9 + (214 - 62) + (y - 214) * 1.06


def scale(y: float) -> float:
    if y < 90:
        return ramp(y, 56, 90, 0.92, 1.42)
    if y < 172:
        return ramp(y, 112, 172, 1.42, 1.04)
    if y < 236:
        return ramp(y, 196, 236, 1.04, 1.2)
    return ramp(y, 300, 400, 1.2, 1.06)


def point(x: float, y: float) -> tuple[float, float]:
    return (100 + (x - 100) * scale(y) + SHIFT, vertical(y))


def warp(path: str) -> str:
    return PAIR.sub(lambda m: "{:.1f},{:.1f}".format(*point(float(m.group(1)), float(m.group(2)))), path)


def mirror_human(path: str) -> str:
    return PAIR.sub(lambda m: f"{200 - float(m.group(1)):g},{m.group(2)}", path)


ARM = (
    "M121,103 C110,97 91,99 83,109 C76,118 75,131 77,142 C75,153 76,166 80.5,178 C82,184 82,188 81,192 "
    "C75,202 76,222 84.4,249 L99.4,250 C101,236 105,222 108,210 C110.5,202 109.5,195 107,190 "
    "C110.5,180 114.5,166 115.5,152 C116.5,140 116.5,128 117.5,120 C118.5,112 119.5,107 121,103 Z"
)
ARM_LINES = [
    "M78.5,141 C88,139 99,132 107,119",
    "M90,146 C92,158 95,170 98,180",
    "M109,140 C112,151 112,164 108,176",
    "M87,187 C93,191 100,191 105.5,188",
    "M83,198 C85,210 88,222 91,236",
    "M101,198 C100,210 98,222 96.5,234",
    "M83,204 C89,208 96,209 104,206",
]
ARM_LIGHT = ["M86,110 C81,117 79,127 80,136", "M80,150 C79,160 80,168 82,174", "M80,204 C79,214 81,225 84,234", "M100,128 C104,124 108,118 112,112"]
BRACER = "M80.4,224 L104,224 L100,247 L84,247 Z"
CX, CY = 160.0, 150.0
K = 0.5523


def circle(x: float, y: float, r: float, reverse: bool = False) -> str:
    k = r * K
    if reverse:
        return (
            f"M{x - r},{y} C{x - r},{y + k} {x - k},{y + r} {x},{y + r} C{x + k},{y + r} {x + r},{y + k} {x + r},{y} "
            f"C{x + r},{y - k} {x + k},{y - r} {x},{y - r} C{x - k},{y - r} {x - r},{y - k} {x - r},{y} Z"
        )
    return (
        f"M{x - r},{y} C{x - r},{y - k} {x - k},{y - r} {x},{y - r} C{x + k},{y - r} {x + r},{y - k} {x + r},{y} "
        f"C{x + r},{y + k} {x + k},{y + r} {x},{y + r} C{x - k},{y + r} {x - r},{y + k} {x - r},{y} Z"
    )


def flames(cx: float, cy: float, r: float, count: int) -> str:
    out = []
    for i in range(count):
        a = i / count * 2 * math.pi
        da = math.pi / count * 0.55
        length = 14 + 6 * (0.5 + 0.5 * math.sin(i * 2.3)) + (6 if i % 3 == 0 else 0)
        bend = 0.12
        base_l = (cx + r * math.cos(a - da), cy + r * math.sin(a - da))
        base_r = (cx + r * math.cos(a + da), cy + r * math.sin(a + da))
        tip = (cx + (r + length) * math.cos(a + bend), cy + (r + length) * math.sin(a + bend))
        ctrl_l = (cx + (r + length * 0.55) * math.cos(a - da * 1.4), cy + (r + length * 0.55) * math.sin(a - da * 1.4))
        ctrl_r = (cx + (r + length * 0.45) * math.cos(a + da * 1.6 + bend), cy + (r + length * 0.45) * math.sin(a + da * 1.6 + bend))
        out.append(
            f"M{base_l[0]:.1f},{base_l[1]:.1f} Q{ctrl_l[0]:.1f},{ctrl_l[1]:.1f} {tip[0]:.1f},{tip[1]:.1f} "
            f"Q{ctrl_r[0]:.1f},{ctrl_r[1]:.1f} {base_r[0]:.1f},{base_r[1]:.1f} Z"
        )
    return " ".join(out)


HEAD_SHAPES = {
    "head": "M160,29 C172,29 181,37 182,49 C183,57 182,63 180,68 L176,76 C172,82 166,86 160,86 C154,86 148,82 144,76 L140,68 C138,63 137,57 138,49 C139,37 148,29 160,29 Z",
    "face": "M146,45 C152,42 168,42 174,45 C176,54 175,64 172,72 C168,78 164,80 160,80 C156,80 152,78 148,72 C145,64 144,54 146,45 Z",
    "jaw": "M143,70 L147,77 C151,82 155,85 160,85 C165,85 169,82 173,77 L177,70 C176,76 172,84 166,88 C162,90 158,90 154,88 C148,84 144,76 143,70 Z",
    "right_eye": "M146.5,53.5 C148,51.4 154,51.4 155.5,53.5 C154,55.2 148,55.2 146.5,53.5 Z",
    "left_eye": "MIRROR_EYE",
    "nose": "M160,51 C159,56 157.5,60 157,63.4 C158.5,65 161.5,65 163,63.4 C162.5,60 161,56 160,51 Z",
    "right_ear": "M138.6,48.5 C134.4,47.5 133.4,56 135,61 C136,63.6 138,63.6 139,61 Z",
    "left_ear": "MIRROR_EAR",
    "tongue": "M156,73 C158,75 162,75 164,73 C162,74.2 158,74.2 156,73 Z",
}
HEAD_SHAPES["left_eye"] = "M173.5,53.5 C172,51.4 166,51.4 164.5,53.5 C166,55.2 172,55.2 173.5,53.5 Z"
HEAD_SHAPES["left_ear"] = "M181.4,48.5 C185.6,47.5 186.6,56 185,61 C184,63.6 182,63.6 181,61 Z"
HEAD_ANCHORS = {
    "head": (179, 52),
    "face": (172, 62),
    "jaw": (160, 86),
    "right_eye": (151, 53.5),
    "left_eye": (169, 53.5),
    "nose": (160, 59),
    "right_ear": (136, 55),
    "left_ear": (184, 55),
    "tongue": (160, 74),
}
HEAD_LINES = [
    "M154.5,71.6 C157,72.6 163,72.6 165.5,71.6",
    "M147,60 C150,62.4 152.5,63.4 155,63.4",
    "M173,60 C170,62.4 167.5,63.4 165,63.4",
    "M157,47 L158.4,51 M163,47 L161.6,51",
]
BROWS = ["M144.5,50 C148.5,47 153,46.6 157,48.4", "M175.5,50 C171.5,47 167,46.6 163,48.4"]
BEARD = "M143.5,61 C144.5,72 150,84 160,93 C170,84 175.5,72 176.5,61 C174.5,69 170.5,75.5 165.5,77.5 C162.5,75.6 157.5,75.6 154.5,77.5 C149.5,75.5 145.5,69 143.5,61 Z"
MOUSTACHE = "M151.5,69 C155,67 158,67.2 160,68.6 C162,67.2 165,67 168.5,69 C165.5,71 162,71 160,69.8 C158,71 154.5,71 151.5,69 Z"

MUSCLES = [
    "M70,113 C76,125 90,129 100,125",
    "M90,141 C94,143 98,143 100,141",
    "M90,156 C94,158 98,158 100,156",
    "M91,171 C94,173 98,173 100,171",
    "M70,186 C78,204 88,213 96,219",
    "M68,122 L73,126 M67,132 L72,135 M67,142 L71,144",
    "M70,242 C74,262 77,280 79,296",
    "M90,246 C88,264 86,280 86,294",
    "M69,320 C66,336 68,350 72,362",
    "M92,62 C94,70 96,76 98,80",
]


def rays(cx: float, cy: float, inner: float, outer: float, *, count: int, width: float, opacity: float) -> str:
    out = []
    for i in range(count):
        a = i / count * 2 * math.pi
        b = a + width
        p1 = (cx + inner * math.cos(a), cy + inner * math.sin(a))
        p2 = (cx + outer * math.cos((a + b) / 2), cy + outer * math.sin((a + b) / 2))
        p3 = (cx + inner * math.cos(b), cy + inner * math.sin(b))
        out.append(f"M{p1[0]:.1f},{p1[1]:.1f} L{p2[0]:.1f},{p2[1]:.1f} L{p3[0]:.1f},{p3[1]:.1f} Z")
    return f'<path d="{" ".join(out)}" fill="{C["gold"]}" fill-opacity="{opacity}"/>'


def crown() -> str:
    hx, hy = 160.0, 38.0
    spikes = []
    for dx, h in ((-17, 9), (-11, 13), (-5.5, 16), (0, 21), (5.5, 16), (11, 13), (17, 9)):
        x = hx + dx
        base_y = hy + abs(dx) * 0.16
        spikes.append(f"M{x - 2.4:.1f},{base_y:.1f} L{x:.1f},{base_y - h:.1f} L{x + 2.4:.1f},{base_y:.1f} Z")
    band = f"M{hx - 20:.1f},{hy + 4:.1f} C{hx - 10:.1f},{hy - 1:.1f} {hx + 10:.1f},{hy - 1:.1f} {hx + 20:.1f},{hy + 4:.1f} L{hx + 19:.1f},{hy + 8:.1f} C{hx + 9:.1f},{hy + 3.5:.1f} {hx - 9:.1f},{hy + 3.5:.1f} {hx - 19:.1f},{hy + 8:.1f} Z"
    return (
        f'<path d="{" ".join(spikes)}" fill="{C["gold"]}" fill-opacity="0.9" stroke="#f3d68f" stroke-width="0.5"/>'
        f'<path d="{band}" fill="{C["gold"]}" stroke="#f3d68f" stroke-width="0.6"/>'
        f'<circle cx="{hx:.1f}" cy="{hy + 3:.1f}" r="2.4" fill="#fff4d6"/>'
    )


def flip_x(path: str) -> str:
    return PAIR.sub(lambda m: f"{WIDTH - float(m.group(1)):.1f},{m.group(2)}", path)


def cloak() -> str:
    bottom = vertical(400)
    outer = (
        f"M140,98 C132,92 124,82 120,66 C112,74 106,86 104,100 C96,104 90,112 86,122 "
        f"C70,170 52,250 40,{bottom - 30:.1f} C36,{bottom - 14:.1f} 34,{bottom - 4:.1f} 36,{bottom + 4:.1f} "
        f"Q48,{bottom + 14:.1f} 60,{bottom + 4:.1f} Q72,{bottom + 16:.1f} 86,{bottom + 6:.1f} Q100,{bottom + 18:.1f} 114,{bottom + 4:.1f} "
        f"C116,{bottom - 60:.1f} 110,250 108,190 C107,160 110,130 120,112 Z"
    )
    lining = (
        f"M114,{bottom + 4:.1f} C116,{bottom - 60:.1f} 110,250 108,190 C107,170 108,150 112,134 "
        f"C118,170 124,240 128,{bottom - 40:.1f} C129,{bottom - 20:.1f} 128,{bottom - 6:.1f} 126,{bottom + 2:.1f} Z"
    )
    collar = "M140,98 C132,92 124,82 120,66 C126,64 134,70 140,80 C144,86 146,92 146,98 Z"
    hem = (
        f"M36,{bottom + 4:.1f} Q48,{bottom + 14:.1f} 60,{bottom + 4:.1f} Q72,{bottom + 16:.1f} 86,{bottom + 6:.1f} Q100,{bottom + 18:.1f} 114,{bottom + 4:.1f} "
        f"L114.6,{bottom - 4:.1f} Q100,{bottom + 9:.1f} 86,{bottom - 2:.1f} Q72,{bottom + 8:.1f} 60,{bottom - 4:.1f} Q48,{bottom + 6:.1f} 37,{bottom - 4:.1f} Z"
    )
    folds = " ".join(
        (
            f"M96,124 C84,180 72,260 62,{bottom - 2:.1f}",
            f"M102,132 C96,190 90,270 86,{bottom + 2:.1f}",
            f"M92,140 C78,200 62,280 50,{bottom - 6:.1f}",
            f"M106,150 C104,210 102,290 104,{bottom:.1f}",
        )
    )
    stud_points = ((48, bottom + 2), (60, bottom - 1), (73, bottom + 3), (86, bottom + 1), (100, bottom + 4))
    defs = (
        '<defs><linearGradient id="cloak" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3a2f1c"/><stop offset="0.5" stop-color="#241c10"/><stop offset="1" stop-color="#140f08"/></linearGradient>'
        '<linearGradient id="lining" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#0f2c29"/><stop offset="1" stop-color="#1d4a44"/></linearGradient>'
        '<linearGradient id="cloakshade" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#000" stop-opacity="0.4"/><stop offset="0.6" stop-color="#000" stop-opacity="0"/></linearGradient></defs>'
    )
    half = (
        f'<path d="{outer}" fill="url(#cloak)" stroke="{C["gold"]}" stroke-opacity="0.8" stroke-width="1.1"/>'
        f'<path d="{outer}" fill="url(#cloakshade)"/>'
        f'<path d="{lining}" fill="url(#lining)" stroke="{C["gold"]}" stroke-opacity="0.6" stroke-width="0.8"/>'
        f'<path d="{folds}" fill="none" stroke="#000" stroke-opacity="0.45" stroke-width="1.4" stroke-linecap="round"/>'
        f'<path d="{folds}" fill="none" stroke="#f3d68f" stroke-opacity="0.06" stroke-width="0.8" transform="translate(2,0)"/>'
        f'<path d="{hem}" fill="{C["gold"]}" fill-opacity="0.85" stroke="#f3d68f" stroke-width="0.5"/>'
        f'<path d="{collar}" fill="url(#cloak)" stroke="{C["gold"]}" stroke-width="1"/>'
    )
    mirrored = PAIR.sub(lambda m: f"{WIDTH - float(m.group(1)):.1f},{m.group(2)}", half)
    studs = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.1" fill="#fff4d6"/><circle cx="{WIDTH - x:.1f}" cy="{y:.1f}" r="1.1" fill="#fff4d6"/>' for x, y in stud_points
    )
    trim = (
        f'<path d="{outer}" fill="none" stroke="{C["gold"]}" stroke-opacity="0.35" stroke-width="3.2" stroke-dasharray="0.1 5.5" stroke-linecap="round"/>'
        f'<path d="{hem}" fill="none" stroke="#7a5a1e" stroke-width="0.6" stroke-dasharray="2 2"/>'
    )
    half = half.replace(f'<path d="{hem}"', trim + f'<path d="{hem}"', 1)
    mirrored = PAIR.sub(lambda m: f"{WIDTH - float(m.group(1)):.1f},{m.group(2)}", half)
    mirrored = mirrored.replace("url(#cloakshade)", "url(#cloakshadeR)")
    defs += '<defs><linearGradient id="cloakshadeR" x1="1" y1="0" x2="0" y2="0"><stop offset="0" stop-color="#000" stop-opacity="0.4"/><stop offset="0.6" stop-color="#000" stop-opacity="0"/></linearGradient></defs>'
    return defs + half + mirrored + studs


def band(path: str, fill: float = 0.28) -> str:
    return f'<path d="{warp(path)}" fill="{C["gold"]}" fill-opacity="{fill}" stroke="{C["gold"]}" stroke-width="0.9"/>'


def regalia() -> list[str]:
    marks = []
    marks.append(crown())
    belt = "M68,192 C80,197 120,197 132,192 L132,200 C120,205 80,205 68,200 Z"
    marks.append(band(belt, 0.55))
    bx, by = point(100, 199)
    marks.append(
        f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="5.6" fill="{C["gold"]}" stroke="#f3d68f" stroke-width="0.7"/><circle cx="{bx:.1f}" cy="{by:.1f}" r="2.2" fill="#fff4d6"/>'
    )
    for wrist in (BRACER, PAIR.sub(lambda m: f"{WIDTH - float(m.group(1)):.1f},{m.group(2)}", BRACER)):
        marks.append(f'<path d="{wrist}" fill="{C["gold"]}" fill-opacity="0.3" stroke="{C["gold"]}" stroke-width="0.9"/>')
    for greave in ("M68,350 L87,350 L88,382 L71,382 Z", "M113,350 L132,350 L129,382 L112,382 Z"):
        marks.append(band(greave))
    for x in (66, 134):
        sx, sy = point(x, 90)
        marks.append(
            f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="5" fill="{C["gold"]}" stroke="#f3d68f" stroke-width="0.7"/><circle cx="{sx:.1f}" cy="{sy:.1f}" r="1.8" fill="#fff4d6"/>'
        )
    sigil_x, sigil_y = point(100, 104)
    marks.append(
        f'<path d="M{sigil_x},{sigil_y - 9} L{sigil_x + 5},{sigil_y} L{sigil_x},{sigil_y + 9} L{sigil_x - 5},{sigil_y} Z" fill="{C["gold"]}" fill-opacity="0.85"/>'
    )
    marks.append(
        f'<path d="M{sigil_x - 16},{sigil_y} L{sigil_x - 7},{sigil_y} M{sigil_x + 7},{sigil_y} L{sigil_x + 16},{sigil_y}" stroke="{C["gold"]}" stroke-opacity="0.6" stroke-width="0.9"/>'
    )
    rim_l = warp("M66,96 C62,140 66,180 70,214")
    marks.append(f'<path d="{rim_l}" fill="none" stroke="#ffe7a8" stroke-opacity="0.12" stroke-width="3" stroke-linecap="round"/>')
    return marks


def divine(states: dict[str, str]) -> Plan:
    base = humanoid(states)
    hx, hy = 160.0, 56.0
    halo = (
        '<defs><radialGradient id="halo" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#ffe7a8" stop-opacity="0.6"/>'
        f'<stop offset="0.7" stop-color="{C["gold"]}" stop-opacity="0.18"/><stop offset="1" stop-color="{C["gold"]}" stop-opacity="0"/></radialGradient></defs>'
        + rays(hx, hy, 34, 60, count=32, width=0.07, opacity=0.36)
        + f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="38" fill="url(#halo)"/>'
        + f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="32" fill="none" stroke="{C["gold"]}" stroke-opacity="0.85" stroke-width="1.5"/>'
        + f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="28.5" fill="none" stroke="{C["gold"]}" stroke-opacity="0.35" stroke-width="0.6"/>'
    )
    cx = 100 + SHIFT
    ring = circle(CX, CY, 121) + " " + circle(CX, CY, 113, reverse=True)
    parts = [Part("aura", "Aura", ring, (CX + 116, CY - 30), tone="aura")]
    for part in base.parts:
        tone = "" if part.inner or part.subtle else "divine"
        path = warp(part.path)
        if part.key == "right_arm":
            path = ARM
        elif part.key == "left_arm":
            path = PAIR.sub(lambda m: f"{WIDTH - float(m.group(1)):.1f},{m.group(2)}", ARM)
        anchor = point(*part.anchor)
        if part.key in HEAD_SHAPES:
            path, anchor = HEAD_SHAPES[part.key], HEAD_ANCHORS[part.key]
        if part.key in {"right_arm", "left_arm"}:
            anchor = (94, 160) if part.key == "right_arm" else (WIDTH - 94, 160)
        parts.append(Part(part.key, part.label, path, anchor, part.inner, part.subtle, part.far, halo if part.key == "head" else "", tone))
    details = [warp(path) for path in base.details if path != NAVEL and min(float(m.group(2)) for m in PAIR.finditer(path)) > 62]
    details += HEAD_LINES
    details += [warp(path) for path in MUSCLES] + [warp(mirror_human(path)) for path in MUSCLES]
    details += ARM_LINES + [PAIR.sub(lambda m: f"{WIDTH - float(m.group(1)):.1f},{m.group(2)}", line) for line in ARM_LINES]
    marks = []
    light = ARM_LIGHT + [flip_x(path) for path in ARM_LIGHT]
    marks.append(f'<path d="{" ".join(light)}" fill="none" stroke="#ffe7a8" stroke-opacity="0.16" stroke-width="2.2" stroke-linecap="round"/>')
    beard = (
        '<defs><linearGradient id="beard" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#8a6a2c"/><stop offset="1" stop-color="#4a3814"/></linearGradient></defs>'
        f'<path d="{BEARD}" fill="url(#beard)" stroke="{C["gold"]}" stroke-opacity="0.7" stroke-width="0.7"/>'
        f'<path d="{MOUSTACHE}" fill="url(#beard)" stroke="{C["gold"]}" stroke-opacity="0.7" stroke-width="0.6"/>'
        + "".join(
            f'<path d="M{x},{y0} C{x + (x - 160) * 0.05:.1f},{y0 + 6} {x + (x - 160) * 0.02:.1f},{y0 + 11} {160 + (x - 160) * 0.8:.1f},{y0 + 15}" fill="none" stroke="#d8b25a" stroke-opacity="0.35" stroke-width="0.5"/>'
            for x, y0 in ((148, 70), (152, 75), (156, 78), (164, 78), (168, 75), (172, 70))
        )
    )
    if states.get("jaw", "unhurt") not in {"lost"}:
        marks.append(beard)
    marks.extend(f'<path d="{path}" fill="none" stroke="{C["gold"]}" stroke-opacity="0.9" stroke-width="1.9" stroke-linecap="round"/>' for path in BROWS)
    for side, x in (("right", 151.0), ("left", 169.0)):
        if states.get(f"{side}_eye", "unhurt") not in {"lost", "prosthesis"}:
            ex, ey = x, 53.5
            marks.append(
                f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="2.1" fill="#fff4d6"/><circle cx="{ex:.1f}" cy="{ey:.1f}" r="5" fill="#ffe7a8" fill-opacity="0.2"/>'
            )
    marks.extend(regalia())
    pool_y = vertical(420) + 12
    aureole = (
        f'<defs><radialGradient id="flame" cx="{CX}" cy="{CY}" r="150" gradientUnits="userSpaceOnUse">'
        + '<stop offset="0.78" stop-color="#ffe7a8" stop-opacity="0.75"/><stop offset="0.9" stop-color="#d8b25a" stop-opacity="0.35"/>'
        + '<stop offset="1" stop-color="#d8b25a" stop-opacity="0"/></radialGradient>'
        + f'<radialGradient id="disc" cx="{CX}" cy="{CY}" r="113" gradientUnits="userSpaceOnUse">'
        + '<stop offset="0" stop-color="#ffe7a8" stop-opacity="0.10"/><stop offset="0.85" stop-color="#d8b25a" stop-opacity="0.05"/>'
        + '<stop offset="1" stop-color="#d8b25a" stop-opacity="0.14"/></radialGradient></defs>'
        + f'<circle cx="{CX}" cy="{CY}" r="113" fill="url(#disc)"/>'
        + f'<path d="{flames(CX, CY, 120, 60)}" fill="url(#flame)"/>'
        + rays(CX, CY, 20, 104, count=48, width=0.035, opacity=0.07)
        + f'<circle cx="{CX}" cy="{CY}" r="96" fill="none" stroke="{C["gold"]}" stroke-opacity="0.3" stroke-width="0.8" stroke-dasharray="1 4"/>'
        + f'<circle cx="{CX}" cy="{CY}" r="128" fill="none" stroke="{C["gold"]}" stroke-opacity="0.18" stroke-width="0.6"/>'
    )
    underlay = (
        aureole
        + rays(cx, vertical(200), 140, 300, count=40, width=0.045, opacity=0.035)
        + '<defs><radialGradient id="pool" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#ffe7a8" stop-opacity="0.55"/>'
        '<stop offset="1" stop-color="#ffe7a8" stop-opacity="0"/></radialGradient></defs>'
        f'<ellipse cx="{cx}" cy="{pool_y:.1f}" rx="88" ry="10" fill="url(#pool)"/>'
    )
    first = parts[1]
    parts[1] = Part(first.key, first.label, first.path, first.anchor, first.inner, first.subtle, first.far, cloak() + first.prelude, first.tone)
    return Plan("Divine manifestation", WIDTH, int(pool_y + 16), parts, details, marks, underlay)


if __name__ == "__main__":
    wounded = {"aura": "festering", "right_hand": "lost", "torso": "open", "left_eye": "scarred", "face": "lasting"}
    fallen = {"heart": "fatal", "aura": "lost", "head": "open"}
    panels = [
        (
            "Unhurt",
            draw(divine({}), {}, scale=1.25),
            "A god walking in a body: the same parts as a person, cast as a titan and lit from within, with an aura that can itself be wounded. Divine bodies heal twice as fast and do not fester.",
        ),
        (
            "Wounded",
            draw(divine(wounded), wounded, scale=1.25),
            "The aura rotting at its edge, a hand lost to a rival god, the body opened, an eye scarred, the face marked for good.",
        ),
        ("Fallen", draw(divine(fallen), fallen, scale=1.25), "Struck through the heart; the aura gone dark, the head split. The god falls into a long sleep."),
    ]
    (OUT / sys.argv[1]).write_text(
        page("Divine manifestation", "The sons of the creator, foreign gods and every god that walks among the living.", panels), encoding="utf-8"
    )
