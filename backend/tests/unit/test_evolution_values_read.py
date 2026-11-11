import re
from enum import StrEnum
from pathlib import Path

from aerona.domain.enums.evolution import EvolvedTrait, KeystoneRole, PlagueResponse, SuccessionStage, TrophicLevel

SOURCE = Path(__file__).resolve().parents[2] / "src" / "aerona"
ENUMS: tuple[type[StrEnum], ...] = (EvolvedTrait, KeystoneRole, TrophicLevel, PlagueResponse, SuccessionStage)


def engine_source() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for folder in ("engine", "catalog") for path in (SOURCE / folder).rglob("*.py"))


def test_every_value_of_the_living_world_enums_drives_the_engine() -> None:
    source = engine_source()
    missing = [f"{kind.__name__}.{member.name}" for kind in ENUMS for member in kind if not re.search(rf"\.{member.name}\b", source)]
    assert missing == []
