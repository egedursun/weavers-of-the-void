import math
import sys
from pathlib import Path

from forms import heart, num, outline, tapered
from render import C, Part, Plan, draw, ellipse, page

OUT = Path(__file__).parent
WIDTH, HEIGHT = 300, 300
CX, CY = 150.0, 152.0


def ray(angle: float, radius: float) -> tuple[float, float]:
    return CX + radius * math.cos(angle), CY + radius * math.sin(angle)


def arm(k: int) -> str:
    a = math.radians(-90 + k * 72)
    spine = [ray(a, 30), ray(a + 0.03, 64), ray(a + 0.11, 98), ray(a + 0.2, 128)]
    return tapered(spine, 34, 5)


def groove(k: int) -> str:
    a = math.radians(-90 + k * 72)
    start, middle, end = ray(a + 0.01, 50), ray(a + 0.06, 82), ray(a + 0.15, 112)
    return f"M{num(start[0])},{num(start[1])} Q{num(middle[0])},{num(middle[1])} {num(end[0])},{num(end[1])}"


ARMS = " | ".join(arm(k) for k in range(5))
DISC = outline([ray(t - math.pi / 2, 44 + 5 * math.cos(5 * t)) for t in (i * 2 * math.pi / 30 for i in range(30))])


def radial(states: dict[str, str]) -> Plan:
    parts = [
        Part("tentacles", "Arms", ARMS, (238, 120)),
        Part("core", "Disc", DISC, (182, 178)),
        Part("eye", "Eye", ellipse(CX, CY - 18, 8, 6.5), (CX, CY - 18)),
        Part("gut", "Gut", ellipse(CX, CY + 6, 24, 18), (CX - 16, CY + 10), inner=True),
        Part("heart", "Heart", heart(CX, CY + 4, 7), (CX + 2, CY + 4), inner=True),
        Part("groin", "Groin", ellipse(CX, CY + 31, 6, 5), (CX, CY + 31), inner=True),
    ]
    details = [groove(k) for k in range(5)]
    marks = []
    state = states.get("eye", "unhurt")
    if state not in {"lost", "prosthesis"}:
        marks.append(f'<circle cx="{num(CX)}" cy="{num(CY - 18)}" r="3" fill="{C["gold"]}" fill-opacity="0.6"/>')
    elif state == "prosthesis":
        marks.append(f'<circle cx="{num(CX)}" cy="{num(CY - 18)}" r="3" fill="#2a3b55" stroke="#9fc3ff" stroke-width="0.4"/>')
    underlay = (
        '<defs><filter id="rshadow" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="4"/></filter></defs>'
        f'<g filter="url(#rshadow)" opacity="0.4" transform="translate(3,6)"><path d="{DISC} {ARMS.replace(" | ", " ")}" fill="#000"/></g>'
    )
    return Plan("Radial", WIDTH, HEIGHT, parts, details, marks, underlay)


if __name__ == "__main__":
    wounded = {"tentacles": "lost", "core": "scarred"}
    fallen = {"gut": "fatal", "eye": "open"}
    panels = [
        ("Unhurt", draw(radial({}), {}), "Five arms around one disc, seen from above."),
        ("Wounded", draw(radial(wounded), wounded), "Arms lost, the disc scarred."),
        (
            "Fallen",
            draw(radial(fallen), fallen),
            "The gut at the centre takes the killing blow.",
        ),
    ]
    (OUT / sys.argv[1]).write_text(page("Radial body", "Bodies built around a centre.", panels), encoding="utf-8")
