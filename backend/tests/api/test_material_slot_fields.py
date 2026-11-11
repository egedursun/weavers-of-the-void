import re
from pathlib import Path

from aerona.api.schemas.economy import MaterialSlotView

FRONTEND = Path(__file__).resolve().parents[3] / "frontend" / "src" / "features" / "entity" / "economy"
LEFT_OUT = re.compile(r"property\.key !== '(\w+)'")


def test_every_property_a_material_slot_shows_is_served() -> None:
    labels = (FRONTEND / "labels.ts").read_text(encoding="utf-8")
    block = labels[labels.index("export const MATERIAL_PROPERTIES") :]
    block = block[: block.index("\n]")]
    shown = set(re.findall(r"key: '(\w+)'", block)) - set(LEFT_OUT.findall((FRONTEND / "NodeMaterials.tsx").read_text(encoding="utf-8")))
    assert shown
    assert sorted(shown - set(MaterialSlotView.model_fields)) == []
