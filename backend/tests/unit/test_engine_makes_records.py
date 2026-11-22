import re
from pathlib import Path

from aerona.db.base import Base
from aerona.engine.interconnect.catalog_orders51 import ORDERS51_MECHANICS

SOURCE = Path(__file__).resolve().parents[2] / "src" / "aerona"
AUTHORS = ("tools", "services")


def made_by(root: Path, folder: str, name: str) -> list[str]:
    pattern = re.compile(rf"\b{name}\(")
    return sorted(str(path.relative_to(root)) for path in (root / folder).rglob("*.py") if pattern.search(path.read_text(encoding="utf-8")))


def idle_records(root: Path, tables: dict[str, list[str]], classes: dict[str, str]) -> list[str]:
    found: list[str] = []
    for key, names in tables.items():
        for table in names:
            name = classes.get(table)
            if name is None or made_by(root, "engine", name):
                continue
            authors = [path for folder in AUTHORS for path in made_by(root, folder, name)]
            if authors:
                found.append(f"{key}: {table} is made only by {', '.join(authors)}")
    return found


def test_the_engine_itself_makes_the_records_of_every_mechanic_the_model_can_make() -> None:
    classes = {table.name: mapper.class_.__name__ for mapper in Base.registry.mappers for table in mapper.tables}
    tables = {mechanic.key: list(mechanic.tables) for mechanic in ORDERS51_MECHANICS}
    assert idle_records(SOURCE, tables, classes) == []


def test_a_record_only_a_tool_makes_is_caught(tmp_path: Path) -> None:
    for folder in ("engine", *AUTHORS):
        (tmp_path / folder).mkdir()
    (tmp_path / "tools" / "warn.py").write_text("row = WaveWarningRow(region_entity_id=1)\n", encoding="utf-8")
    (tmp_path / "engine" / "waves.py").write_text("row = SeaWaveRow(world_id=1)\n", encoding="utf-8")
    classes = {"wave_warnings": "WaveWarningRow", "sea_waves": "SeaWaveRow"}
    found = idle_records(tmp_path, {"sea_waves": ["sea_waves", "wave_warnings"]}, classes)
    assert found == ["sea_waves: wave_warnings is made only by tools/warn.py"]
