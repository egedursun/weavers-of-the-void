from collections.abc import Sequence
from dataclasses import dataclass

ELLIPSIS = "…"
LINE_BREAK = "\n"
PARTIAL_LINE_RESERVE = 2


@dataclass(frozen=True)
class BudgetSection:
    text: str
    floor: int
    hint: str


def budget_trailer(hidden_lines: int, hint: str) -> str:
    return f"{LINE_BREAK}{ELLIPSIS} (+{hidden_lines} more lines; {hint})"


def budget(text: str, limit: int, hint: str, trim_min: int) -> str:
    if not text or len(text) <= limit:
        return text
    lines = text.split(LINE_BREAK)
    kept: list[str] = []
    used = 0
    for line in lines:
        if used + len(line) + 1 > limit:
            room = limit - used - PARTIAL_LINE_RESERVE
            if room >= trim_min:
                kept.append(line[:room] + ELLIPSIS)
            break
        kept.append(line)
        used += len(line) + 1
    if not kept:
        kept.append(lines[0][: max(0, limit - 1)] + ELLIPSIS)
    return LINE_BREAK.join(kept) + budget_trailer(len(lines) - len(kept), hint)


def sectioned_budget(sections: Sequence[BudgetSection], limit: int, trim_min: int) -> str:
    present = [section for section in sections if section.text]
    if not present:
        return ""
    floors = [min(len(section.text), section.floor) for section in present]
    total = sum(floors) + len(present)
    ratio = limit / total if total > limit else 1.0
    shares = [int(floor * ratio) for floor in floors]
    left = limit - sum(shares) - len(present)
    for index, section in enumerate(present):
        if left <= 0:
            break
        extra = min(left, len(section.text) - shares[index])
        if extra > 0:
            shares[index] += extra
            left -= extra
    rendered = [
        section.text if len(section.text) <= share else budget(section.text, max(1, share), section.hint, trim_min)
        for section, share in zip(present, shares, strict=True)
    ]
    return LINE_BREAK.join(rendered)
