import sys
from pathlib import Path

import human
import quadruped as beast
from forms import capsule, moved, num, teeth
from render import C, Part, Plan, draw, page

OUT = Path(__file__).parent
SHIFT_X, SHIFT_Y = 6.0, 62.0
SCALE = 0.66
WAIST_X, WAIST_Y = 126.0, 150.0


def low(x: float, y: float) -> tuple[float, float]:
    return x + SHIFT_X, y + SHIFT_Y


def high(x: float, y: float) -> tuple[float, float]:
    return WAIST_X + (x - 100) * SCALE, WAIST_Y + (y - 200) * SCALE


def lower(path: str) -> str:
    return moved(path, low)


def upper(path: str) -> str:
    return moved(path, high)


def sided(key: str, label: str, path: str, anchor: tuple[float, float]) -> list[Part]:
    return [
        Part(f"right_{key}", f"Right {label}", upper(path), high(*anchor)),
        Part(
            f"left_{key}",
            f"Left {label}",
            upper(human.mirror(path)),
            high(200 - anchor[0], anchor[1]),
        ),
    ]


def centauroid(states: dict[str, str]) -> Plan:
    jaw_x, jaw_y = high(100, 55)
    parts = [
        Part(
            "right_foreleg",
            "Right foreleg",
            lower(beast.FAR_FORELEG),
            low(139, 200),
            far=True,
        ),
        Part(
            "right_hindleg",
            "Right hind leg",
            lower(beast.FAR_HINDLEG),
            low(241, 200),
            far=True,
        ),
        Part("tail", "Tail", lower(beast.TAIL), low(302, 140)),
        Part(
            "torso",
            "Torso",
            lower(beast.TORSO) + " | " + upper(human.TORSO),
            low(200, 92),
        ),
        Part("left_hindleg", "Left hind leg", lower(beast.HINDLEG), low(258, 126)),
        Part("left_foreleg", "Left foreleg", lower(beast.FORELEG), low(119, 176)),
        *sided("arm", "arm", human.RIGHT["arm"], (47, 150)),
        *sided("hand", "hand", human.RIGHT["hand"], (40, 245)),
        Part(
            "fingers",
            "Fingers",
            upper(human.RIGHT["fingers"] + " " + human.mirror(human.RIGHT["fingers"])),
            high(38, 266),
        ),
        Part("neck", "Neck", upper(human.NECK), high(100, 71)),
        *sided("ear", "ear", human.RIGHT["ear"], (75.5, 42)),
        Part("head", "Head", upper(human.HEAD), high(100, 20)),
        Part("face", "Face", upper(human.FACE), high(110, 47), subtle=True),
        Part("jaw", "Jaw", upper(human.JAW), high(100, 63), subtle=True),
        *sided("eye", "eye", human.RIGHT["eye"], (90.8, 39.5)),
        Part(
            "tongue",
            "Tongue",
            upper(human.TONGUE),
            high(100, 56),
            inner=True,
            subtle=True,
        ),
        Part(
            "teeth",
            "Teeth",
            teeth(jaw_x, jaw_y - 0.4, 9.6 * SCALE, 2.4 * SCALE, 5),
            (jaw_x, jaw_y - 0.4),
            inner=True,
            subtle=True,
        ),
        Part(
            "lungs",
            "Lungs",
            upper(human.RIGHT["lung"] + " " + human.mirror(human.RIGHT["lung"])),
            high(84, 118),
            inner=True,
        ),
        Part("heart", "Heart", upper(human.HEART), high(106, 119), inner=True),
        Part("gut", "Gut", lower(beast.GUT), low(194, 118), inner=True),
        Part("groin", "Groin", lower(beast.GROIN), low(213, 141), inner=True),
        Part(
            "spine",
            "Spine",
            capsule(
                [low(136, 82), low(170, 80), low(210, 81), low(250, 86), low(274, 96)],
                4.4,
            ),
            low(200, 81),
            inner=True,
            subtle=True,
        ),
    ]
    details = [lower(path) for path in beast.DETAILS[:5] + beast.DETAILS[6:]]
    details += [
        upper(path)
        for path in (
            human.MOUTH,
            human.RIGHT["brow"],
            human.mirror(human.RIGHT["brow"]),
            human.RIGHT["collar"],
            human.mirror(human.RIGHT["collar"]),
        )
    ]
    details += [
        upper(path)
        for path in (
            human.RIGHT["chest"],
            human.mirror(human.RIGHT["chest"]),
            human.ABS,
            human.NOSE,
        )
    ]
    marks = []
    for side, iris in (
        ("right", human.RIGHT["iris"]),
        ("left", human.mirror(human.RIGHT["iris"])),
    ):
        if states.get(f"{side}_eye", "unhurt") not in {"lost", "prosthesis"}:
            marks.append(f'<path d="{upper(iris)}" fill="{C["stroke"]}"/>')
        elif states.get(f"{side}_eye") == "prosthesis":
            marks.append(f'<path d="{upper(iris)}" fill="#2a3b55" stroke="#9fc3ff" stroke-width="0.4"/>')
    sx, sy = low(194, 228)
    underlay = (
        '<defs><filter id="kshadow" x="-30%" y="-80%" width="160%" height="260%"><feGaussianBlur stdDeviation="5"/></filter></defs>'
        f'<ellipse cx="{num(sx)}" cy="{num(sy + 2)}" rx="110" ry="6" fill="#000" opacity="0.5" filter="url(#kshadow)"/>'
    )
    return Plan("Centauroid", 340, 300, parts, details, marks, underlay)


if __name__ == "__main__":
    wounded = {
        "left_foreleg": "lost",
        "right_arm": "scarred",
        "torso": "open",
        "left_eye": "prosthesis",
    }
    fallen = {"heart": "fatal", "tail": "lasting"}
    panels = [
        (
            "Unhurt",
            draw(centauroid({}), {}, scale=1.25),
            "Arms, chest and head of a walker over the body and four legs of a beast.",
        ),
        (
            "Wounded",
            draw(centauroid(wounded), wounded, scale=1.25),
            "A foreleg lost, an arm scarred, the flank open, an eye of metal.",
        ),
        (
            "Fallen",
            draw(centauroid(fallen), fallen, scale=1.25),
            "The heart in the chest takes the killing blow.",
        ),
    ]
    (OUT / sys.argv[1]).write_text(
        page(
            "Centauroid body",
            "Upper body of one shape on the lower body of another.",
            panels,
        ),
        encoding="utf-8",
    )
