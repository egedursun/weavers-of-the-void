import ast
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.epochs import EpochRunRow, EpochStepRow
from aerona.domain.enums.epoch import EpochStepKind
from aerona.services.books.typed import TypedIndex
from tests.services.app.factories import Cosmos


async def test_a_reference_to_a_table_keyed_by_something_other_than_id_is_labelled(session: AsyncSession, world: Cosmos) -> None:
    del world
    session.add(EpochRunRow(epoch=7))
    await session.flush()
    session.add(EpochStepRow(epoch=7, step=EpochStepKind.BACKUP))
    await session.flush()
    index = TypedIndex({})
    await index.load_references(session)
    assert 7 in index.references["epoch_runs"]


def test_no_generic_table_read_keys_its_rows_by_an_id_column_it_may_not_have() -> None:
    source = Path(__file__).resolve().parents[3] / "src" / "aerona"
    found: list[str] = []
    for path in sorted(source.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.DictComp) and isinstance(node.key, ast.Attribute) and node.key.attr == "id" and "mapper.class_" in ast.unparse(node):
                found.append(f"{path.relative_to(source)}:{node.lineno}")
    assert found == []
