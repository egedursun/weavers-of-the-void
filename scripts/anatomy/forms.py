import math
import re
from collections.abc import Callable

from render import ellipse

PAIR = re.compile(r"(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)")
Point = tuple[float, float]


def num(value: float) -> str:
    rounded = round(value, 1)
    return f"{rounded:g}"


def moved(path: str, place: Callable[[float, float], Point]) -> str:
    def swap(match: re.Match[str]) -> str:
        x, y = place(float(match.group(1)), float(match.group(2)))
        return f"{num(x)},{num(y)}"

    return PAIR.sub(swap, path)


def mirrored(path: str, axis: float) -> str:
    return moved(path, lambda x, y: (2 * axis - x, y))


def outline(points: list[Point]) -> str:
    n = len(points)
    path = f"M{num(points[0][0])},{num(points[0][1])}"
    for i in range(n):
        p0, p1, p2, p3 = (
            points[i - 1],
            points[i],
            points[(i + 1) % n],
            points[(i + 2) % n],
        )
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        path += f" C{num(c1[0])},{num(c1[1])} {num(c2[0])},{num(c2[1])} {num(p2[0])},{num(p2[1])}"
    return path + " Z"


def profile(axis: float, widths: list[tuple[float, float]]) -> str:
    right = [(axis + w, y) for y, w in widths]
    left = [(axis - w, y) for y, w in reversed(widths)]
    return outline(right + left)


def curve(points: list[Point], samples: int) -> list[Point]:
    padded = [points[0], *points, points[-1]]
    segments = len(points) - 1
    out: list[Point] = []
    for index in range(samples + 1):
        u = index / samples * segments
        seg = min(int(u), segments - 1)
        t = u - seg
        p0, p1, p2, p3 = padded[seg], padded[seg + 1], padded[seg + 2], padded[seg + 3]
        out.append(
            (
                0.5
                * (2 * p1[0] + (-p0[0] + p2[0]) * t + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t * t + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t**3),
                0.5
                * (2 * p1[1] + (-p0[1] + p2[1]) * t + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t * t + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t**3),
            )
        )
    return out


def sides(line: list[Point], width: Callable[[float], float]) -> tuple[list[Point], list[Point]]:
    left: list[Point] = []
    right: list[Point] = []
    for i, (x, y) in enumerate(line):
        a = line[max(0, i - 1)]
        b = line[min(len(line) - 1, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        norm = math.hypot(dx, dy) or 1
        nx, ny = -dy / norm, dx / norm
        w = width(i / (len(line) - 1)) / 2
        left.append((x + nx * w, y + ny * w))
        right.append((x - nx * w, y - ny * w))
    return left, right


def tapered(spine: list[Point], root: float, tip: float, *, samples: int = 40) -> str:
    line = curve(spine, samples)
    left, right = sides(line, lambda t: root + (tip - root) * t**0.85)
    end, before = line[-1], line[-3]
    dx, dy = end[0] - before[0], end[1] - before[1]
    norm = math.hypot(dx, dy) or 1
    cap = (end[0] + dx / norm * tip * 1.4, end[1] + dy / norm * tip * 1.4)
    path = "M" + " L".join(f"{num(x)},{num(y)}" for x, y in left)
    path += f" Q{num(cap[0])},{num(cap[1])} {num(right[-1][0])},{num(right[-1][1])}"
    path += " L" + " L".join(f"{num(x)},{num(y)}" for x, y in right[::-1][1:])
    return path + " Z"


def capsule(spine: list[Point], width: float) -> str:
    line = curve(spine, max(12, len(spine) * 6))
    left, right = sides(line, lambda _: width)
    start, end = line[0], line[-1]
    head = (
        end[0] + (end[0] - line[-2][0]) * 1.2,
        end[1] + (end[1] - line[-2][1]) * 1.2,
    )
    foot = (
        start[0] - (line[1][0] - start[0]) * 1.2,
        start[1] - (line[1][1] - start[1]) * 1.2,
    )
    path = "M" + " L".join(f"{num(x)},{num(y)}" for x, y in left)
    path += f" Q{num(head[0])},{num(head[1])} {num(right[-1][0])},{num(right[-1][1])}"
    path += " L" + " L".join(f"{num(x)},{num(y)}" for x, y in right[::-1][1:])
    path += f" Q{num(foot[0])},{num(foot[1])} {num(left[0][0])},{num(left[0][1])}"
    return path + " Z"


def teeth(cx: float, cy: float, width: float, height: float = 3.0, count: int = 6) -> str:
    step = width / count
    top = cy - height / 2
    path = f"M{num(cx - width / 2)},{num(top)} L{num(cx + width / 2)},{num(top)}"
    for i in range(count, -1, -1):
        x = cx - width / 2 + i * step
        y = top + (height if i % 2 else height * 0.3)
        path += f" L{num(x)},{num(y)}"
    return path + " Z"


def toes(feet: list[str]) -> str:
    pieces: list[str] = []
    for foot in feet:
        xs = [float(m.group(1)) for m in PAIR.finditer(foot)]
        ys = [float(m.group(2)) for m in PAIR.finditer(foot)]
        x0, x1, y1 = min(xs), max(xs), max(ys)
        w = x1 - x0
        for i in range(4):
            pieces.append(
                ellipse(
                    round(x0 + w * (0.24 + 0.17 * i), 1),
                    round(y1 - 2.4, 1),
                    round(max(1.3, w * 0.055), 1),
                    2.0,
                )
            )
    return " ".join(pieces)


def heart(cx: float, cy: float, size: float) -> str:
    s = size
    return outline(
        [
            (cx, cy - s * 0.35),
            (cx + s * 0.5, cy - s * 0.7),
            (cx + s * 0.95, cy - s * 0.25),
            (cx + s * 0.6, cy + s * 0.4),
            (cx, cy + s),
            (cx - s * 0.6, cy + s * 0.4),
            (cx - s * 0.95, cy - s * 0.25),
            (cx - s * 0.5, cy - s * 0.7),
        ]
    )


def blob(cx: float, cy: float, radius: float, wobble: float, phase: float, count: int = 20) -> str:
    points = []
    for i in range(count):
        theta = i / count * 2 * math.pi
        r = radius * (1 + wobble * math.sin(3 * theta + phase) + wobble * 0.6 * math.cos(5 * theta + phase * 1.7))
        points.append((cx + r * math.cos(theta), cy + r * math.sin(theta)))
    return outline(points)
