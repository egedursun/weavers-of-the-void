import sys
from pathlib import Path

from human import ABS, FACE, GROIN, GUT, HEAD, HEART, JAW, MOUTH, NAVEL, NECK, NOSE, RIGHT, TONGUE, TORSO, mirror
from render import C, Part, Plan, draw, page

OUT = Path(__file__).parent


def flip(point: tuple[float, float]) -> tuple[float, float]:
    return (200 - point[0], point[1])


def sided(key: str, label: str, path: str, anchor: tuple[float, float]) -> list[Part]:
    return [
        Part(f"right_{key}", f"Right {label}", path, anchor),
        Part(f"left_{key}", f"Left {label}", mirror(path), flip(anchor)),
    ]


def humanoid(states: dict[str, str]) -> Plan:
    parts: list[Part] = [
        *sided("leg", "leg", RIGHT["leg"], (80, 300)),
        *sided("foot", "foot", RIGHT["foot"], (80, 408)),
        Part("torso", "Torso", TORSO, (76, 176)),
        *sided("arm", "arm", RIGHT["arm"], (47, 150)),
        *sided("hand", "hand", RIGHT["hand"], (40, 245)),
        Part("fingers", "Fingers", RIGHT["fingers"] + " " + mirror(RIGHT["fingers"]), (38, 266)),
        Part("neck", "Neck", NECK, (100, 71)),
        *sided("ear", "ear", RIGHT["ear"], (75.5, 42)),
        Part("head", "Head", HEAD, (100, 20)),
        Part("face", "Face", FACE, (110, 47), subtle=True),
        Part("jaw", "Jaw", JAW, (100, 63), subtle=True),
        *sided("eye", "eye", RIGHT["eye"], (90.8, 39.5)),
        Part("nose", "Nose", NOSE, (100, 46)),
        Part("tongue", "Tongue", TONGUE, (100, 56), inner=True, subtle=True),
        Part("lungs", "Lungs", RIGHT["lung"] + " " + mirror(RIGHT["lung"]), (84, 118), inner=True),
        Part("heart", "Heart", HEART, (106, 119), inner=True),
        Part("gut", "Gut", GUT, (100, 170), inner=True),
        Part("groin", "Groin", GROIN, (100, 223), inner=True),
    ]
    details = [
        RIGHT["brow"],
        mirror(RIGHT["brow"]),
        MOUTH,
        RIGHT["collar"],
        mirror(RIGHT["collar"]),
        RIGHT["chest"],
        mirror(RIGHT["chest"]),
        ABS,
        RIGHT["knee"],
        mirror(RIGHT["knee"]),
        RIGHT["shin"],
        mirror(RIGHT["shin"]),
        RIGHT["toes"],
        mirror(RIGHT["toes"]),
        RIGHT["hip"],
        mirror(RIGHT["hip"]),
        NAVEL,
    ]
    marks = []
    for side, iris in (("right", RIGHT["iris"]), ("left", mirror(RIGHT["iris"]))):
        if states.get(f"{side}_eye", "unhurt") not in {"lost", "prosthesis"}:
            marks.append(f'<path d="{iris}" fill="{C["stroke"]}"/>')
        elif states.get(f"{side}_eye") == "prosthesis":
            marks.append(f'<path d="{iris}" fill="#2a3b55" stroke="#9fc3ff" stroke-width="0.4"/>')
    return Plan("Humanoid", 200, 440, parts, details, marks)


if __name__ == "__main__":
    wounded = {
        "right_hand": "lost",
        "left_eye": "lost",
        "left_leg": "festering",
        "torso": "open",
        "left_arm": "scarred",
        "right_foot": "prosthesis",
        "nose": "lasting",
    }
    fallen = {"heart": "fatal", "right_arm": "open", "head": "scarred"}
    panels = [
        ("Unhurt", draw(humanoid({}), {}), "Each part takes its own wound. Organs sit dashed inside the torso."),
        ("Wounded", draw(humanoid(wounded), wounded), "Hand lost, eye gouged, leg festering, torso open, arm scarred, iron foot, nose broken for good."),
        ("Fallen", draw(humanoid(fallen), fallen), "The killing wound glows deep red; older wounds keep their marks."),
    ]
    (OUT / sys.argv[1]).write_text(
        page("Humanoid body", "Wounds shown by state: texture, a mark on the part and a label at the side.", panels), encoding="utf-8"
    )
