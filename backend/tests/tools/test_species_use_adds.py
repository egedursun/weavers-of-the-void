import re
from pathlib import Path

from sqlalchemy import func, select

from aerona.db.session import Database
from aerona.db.tables.ecology import SpeciesUseRow
from aerona.domain.enums.ecology import AnimalRole
from aerona.engine.ecology.uses import give_use
from tests.tools.factories import seed_realm

SOURCE = Path(__file__).resolve().parents[2] / "src" / "aerona"


def test_species_uses_are_made_only_through_give_use() -> None:
    makers = [str(path.relative_to(SOURCE)) for path in SOURCE.rglob("*.py") if re.search(r"(?<!class )\bSpeciesUseRow\(", path.read_text())]
    assert makers == ["engine/ecology/uses.py"]


async def test_a_use_given_twice_before_a_flush_is_made_once(database: Database) -> None:
    realm = await seed_realm(database)
    async with database.write() as session:
        await give_use(session, realm.species_id, AnimalRole.DISPLAY)
        await give_use(session, realm.species_id, AnimalRole.DISPLAY)
        await session.flush()
        made = await session.scalar(
            select(func.count()).select_from(SpeciesUseRow).where(SpeciesUseRow.species_entity_id == realm.species_id, SpeciesUseRow.use == AnimalRole.DISPLAY)
        )
    assert made == 1
