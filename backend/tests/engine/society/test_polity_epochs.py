from pathlib import Path

from sqlalchemy import select

from aerona.db.base import Base
from aerona.db.session import Database
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.polity import LawProfileRow, OfficeRow, TreatyProfileRow
from aerona.domain.enums.bond import BondState
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.polity import TreatyStatus
from aerona.engine.pipeline import simulate
from tests.engine.integration.factories import seed_rich_cosmos


async def test_two_epochs_keep_every_faction_law_and_treaty_typed_and_bonded(tmp_path: Path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path}/polity.db")
    try:
        async with database.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with database.write() as session:
            await seed_rich_cosmos(session)
        await simulate(database, 2)
        async with database.read() as session:
            factions = set(
                await session.scalars(select(EntityRow.id).where(EntityRow.entity_type == EntityType.FACTION, EntityRow.status == EntityStatus.CANON))
            )
            profiled = set(await session.scalars(select(FactionProfileRow.faction_entity_id)))
            assert factions <= profiled
            laws = set(await session.scalars(select(EntityRow.id).where(EntityRow.entity_type == EntityType.LAW, EntityRow.status == EntityStatus.CANON)))
            assert laws <= set(await session.scalars(select(LawProfileRow.law_entity_id)))
            fixups = set(await session.scalars(select(AppliedFixupRow.key)))
            assert {"law_kinds_from_text", "treaties_from_bonds", "faction_profiles_from_kinds", "houses_dynasty_ancestors"} <= fixups
            for profile in await session.scalars(select(TreatyProfileRow).where(TreatyProfileRow.status == TreatyStatus.IN_FORCE)):
                if profile.source_bond_id is not None:
                    bond = await session.get(BondRow, profile.source_bond_id)
                    assert bond is not None and bond.state is BondState.ACTIVE
            for office in await session.scalars(select(OfficeRow)):
                assert office.powers or office.kind.value in {"ruler", "heir_designate", "regent"}
    finally:
        await database.dispose()
