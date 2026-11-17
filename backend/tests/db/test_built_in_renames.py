import ast
import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.base import Base
from aerona.engine.kinds.culture_life import ensure_culture_built_ins
from aerona.engine.kinds.nature import ensure_built_ins as ensure_nature_built_ins

VERSIONS = Path(__file__).resolve().parents[2] / "src" / "aerona" / "db" / "alembic" / "versions"


def renamed_values(text: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for node in ast.parse(text).body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id.endswith("_RENAMED") for target in node.targets):
            pairs.extend(tuple(pair) for pair in ast.literal_eval(node.value))
    return pairs


def unrenamed_keys(text: str, keys: set[str]) -> list[str]:
    missing = []
    for old, new in renamed_values(text):
        for key in sorted(key for key in keys if key == new or key.endswith(f".{new}")):
            former = key[: len(key) - len(new)] + old
            if not re.search(rf"built_in_key = '{re.escape(key)}' WHERE built_in_key = '{re.escape(former)}'", text):
                missing.append(f"{former} -> {key}")
    return missing


async def built_in_keys(session: AsyncSession) -> set[str]:
    await ensure_nature_built_ins(session)
    await ensure_culture_built_ins(session)
    keys: set[str] = set()
    for table in Base.metadata.sorted_tables:
        if "built_in_key" in table.columns:
            keys |= {key for key in await session.scalars(select(table.c.built_in_key)) if key is not None}
    return keys


async def test_a_renamed_value_carries_every_built_in_kind_keyed_by_it(session: AsyncSession) -> None:
    keys = await built_in_keys(session)
    assert keys
    every = "\n".join(path.read_text() for path in sorted(VERSIONS.glob("*.py")))
    assert unrenamed_keys(every, keys) == []


def test_a_rename_without_its_built_in_key_is_caught() -> None:
    text = 'TENETKIND_RENAMED = (("human_sacrifice", "sacrifice_of_people"),)\n'
    assert unrenamed_keys(text, {"doctrine.sacrifice_of_people"}) == ["doctrine.human_sacrifice -> doctrine.sacrifice_of_people"]
    fixed = text + "op.execute(\"UPDATE tenet_kinds SET built_in_key = 'doctrine.sacrifice_of_people' WHERE built_in_key = 'doctrine.human_sacrifice'\")\n"
    assert unrenamed_keys(fixed, {"doctrine.sacrifice_of_people"}) == []
