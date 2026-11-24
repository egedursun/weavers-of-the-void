import json
from pathlib import Path

from aerona.catalog.anatomy import ANATOMIES
from aerona.domain.enums.body import BodyPlan

DRAWINGS = Path(__file__).resolve().parents[3] / "frontend" / "src" / "features" / "entity" / "body" / "anatomy"


def drawn(plan: BodyPlan) -> set[str]:
    path = DRAWINGS / f"{plan.value}.json"
    return {part["key"] for part in json.loads(path.read_text(encoding="utf-8"))["parts"]} if path.exists() else set()


def test_every_body_plan_has_a_drawing() -> None:
    assert sorted(plan.value for plan in BodyPlan if not (DRAWINGS / f"{plan.value}.json").exists()) == []


def test_every_part_a_plan_gives_is_drawn() -> None:
    missing = [f"{plan.value}.{part.key.value}" for plan, anatomy in ANATOMIES.items() for part in anatomy.parts if part.key.value not in drawn(plan)]
    assert missing == []


def test_every_drawn_part_belongs_to_its_plan() -> None:
    extra = [f"{plan.value}.{key}" for plan, anatomy in ANATOMIES.items() for key in sorted(drawn(plan) - {part.key.value for part in anatomy.parts})]
    assert extra == []
