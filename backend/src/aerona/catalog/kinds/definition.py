from dataclasses import dataclass


@dataclass(frozen=True)
class Defined:
    label: str
    checked_by: tuple[str, ...]
    used_by: tuple[str, ...]
