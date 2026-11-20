import importlib.util
from pathlib import Path

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db import tables
from aerona.db.base import Base
from aerona.db.migrations import SCRIPT_LOCATION, build_config, upgrade_to_head_sync
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmos import CosmosRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind, BondRole
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.world import LoreLanguage
from aerona.domain.models.entity_stats import RegionStats
from tests.db.factories import make_entity, make_son

assert tables


def test_linear_migration_history() -> None:
    migrations = sorted((SCRIPT_LOCATION / "versions").glob("*.py"))
    roots = [path for path in migrations if "down_revision = None" in path.read_text(encoding="utf-8")]
    assert len(roots) == 1
    assert len(ScriptDirectory.from_config(build_config("sqlite+aiosqlite://")).get_heads()) == 1


def test_migration_matches_models(tmp_path: Path) -> None:
    path = tmp_path / "migrated.db"
    upgrade_to_head_sync(f"sqlite+aiosqlite:///{path}")
    engine = create_engine(f"sqlite:///{path}")
    with engine.connect() as connection:
        context = MigrationContext.configure(connection, opts={"render_as_batch": True})
        differences = compare_metadata(context, Base.metadata)
        created = set(inspect(connection).get_table_names())
    engine.dispose()
    assert differences == []
    assert set(Base.metadata.tables) <= created


async def test_cosmos_is_a_singleton(session: AsyncSession) -> None:
    def cosmos(identifier: int) -> CosmosRow:
        return CosmosRow(
            id=identifier,
            name="Orvael",
            rng_seed=7,
            lore_language=LoreLanguage.ENGLISH,
            seed_idea="First create light",
            cosmology="",
            tone="",
            rules_snapshot={},
        )

    session.add(cosmos(1))
    await session.flush()
    session.add(cosmos(2))
    with pytest.raises(IntegrityError):
        await session.flush()


async def test_stat_ranges_are_enforced(session: AsyncSession, world_id: int) -> None:
    son = await make_son(session, "Lemir", world_id)
    son.stars = 6
    with pytest.raises(IntegrityError):
        await session.flush()


async def test_entity_requires_existing_world(session: AsyncSession) -> None:
    session.add(
        EntityRow(
            name="Nowhere",
            entity_type="region",
            description="A region of no world.",
            stats=RegionStats(),
            power_level=1,
            origin="engine",
            world_id=999,
            birth_epoch=1,
        )
    )
    with pytest.raises(IntegrityError):
        await session.flush()


async def test_bond_cannot_loop_on_itself(session: AsyncSession, world_id: int) -> None:
    region = await make_entity(session, "Vael", EntityType.REGION, world_id=world_id)
    session.add(BondRow(source_node_id=region.id, target_node_id=region.id, kind=BondKind.RELATED, epoch=1))
    with pytest.raises(IntegrityError):
        await session.flush()


async def test_enum_columns_reject_unknown_values(session: AsyncSession, world_id: int) -> None:
    await make_son(session, "Teshar", world_id)
    with pytest.raises(IntegrityError):
        await session.execute(text("UPDATE sons SET rarity = 'divine'"))


async def test_enum_columns_validate_on_bind(session: AsyncSession, world_id: int) -> None:
    son = await make_son(session, "Morun", world_id)
    son.status = "wandering"
    with pytest.raises(StatementError):
        await session.flush()


async def test_duplicate_active_state_bond_is_blocked_by_the_schema(session: AsyncSession, world_id: int) -> None:
    first = await make_entity(session, "Ilar", EntityType.REGION, world_id=world_id)
    second = await make_entity(session, "Osk", EntityType.REGION, world_id=world_id)
    session.add(BondRow(source_node_id=first.id, target_node_id=second.id, kind=BondKind.ALLY, epoch=1))
    await session.flush()
    session.add(BondRow(source_node_id=first.id, target_node_id=second.id, kind=BondKind.ALLY, epoch=2))
    with pytest.raises(IntegrityError):
        await session.flush()


@pytest.mark.parametrize("kind", [BondKind.ALLY, BondKind.LOVES])
async def test_symmetric_and_singular_bonds_are_unique_per_unordered_pair(session: AsyncSession, world_id: int, kind: BondKind) -> None:
    first = await make_entity(session, "Ilar", EntityType.REGION, world_id=world_id)
    second = await make_entity(session, "Osk", EntityType.REGION, world_id=world_id)
    session.add(BondRow(source_node_id=first.id, target_node_id=second.id, kind=kind, epoch=1))
    await session.flush()
    session.add(BondRow(source_node_id=second.id, target_node_id=first.id, kind=kind, epoch=2))
    with pytest.raises(IntegrityError):
        await session.flush()


async def test_related_bonds_may_repeat_with_different_descriptions(session: AsyncSession, world_id: int) -> None:
    first = await make_entity(session, "Ilar", EntityType.REGION, world_id=world_id)
    second = await make_entity(session, "Osk", EntityType.REGION, world_id=world_id)
    for description in ("kin", "rivals"):
        session.add(BondRow(source_node_id=first.id, target_node_id=second.id, kind=BondKind.RELATED, description=description, epoch=1))
    await session.flush()
    session.add(BondRow(source_node_id=first.id, target_node_id=second.id, kind=BondKind.RELATED, description="kin", epoch=2))
    with pytest.raises(IntegrityError):
        await session.flush()


async def test_an_entity_has_at_most_one_active_inside_bond(session: AsyncSession, world_id: int) -> None:
    thing = await make_entity(session, "Ilar", EntityType.REGION, world_id=world_id)
    first = await make_entity(session, "Osk", EntityType.REGION, world_id=world_id)
    second = await make_entity(session, "Teyl", EntityType.REGION, world_id=world_id)
    session.add(BondRow(source_node_id=thing.id, target_node_id=first.id, kind=BondKind.INSIDE, epoch=1))
    await session.flush()
    session.add(BondRow(source_node_id=thing.id, target_node_id=second.id, kind=BondKind.INSIDE, role=BondRole.SPIRIT_BINDING, epoch=1))
    await session.flush()
    session.add(BondRow(source_node_id=thing.id, target_node_id=second.id, kind=BondKind.INSIDE, epoch=2))
    with pytest.raises(IntegrityError):
        await session.flush()


async def test_sons_and_entities_share_the_node_registry(session: AsyncSession, world_id: int) -> None:
    son = await make_son(session, "Asra", world_id)
    region = await make_entity(session, "Teyl", EntityType.REGION, world_id=world_id)
    assert son.id != region.id
    assert isinstance(await session.get(SonRow, son.id), SonRow)


async def test_the_homeland_migration_gives_a_first_people_its_own_first_town(session: AsyncSession, world_id: int) -> None:
    spec = importlib.util.spec_from_file_location("genesis_homelands", SCRIPT_LOCATION / "versions" / "c4e8a2f6b913_genesis_homelands.py")
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    folk = await make_entity(session, "Ruvenar", EntityType.PEOPLE, world_id=world_id)
    town = await make_entity(session, "Halmure", EntityType.SETTLEMENT, world_id=world_id)
    taken = await make_entity(session, "Tesuvar", EntityType.SETTLEMENT, world_id=world_id)
    taken.birth_epoch = 3
    housed = await make_entity(session, "Vesmari", EntityType.PEOPLE, world_id=world_id)
    home = await make_entity(session, "Sulenure", EntityType.SETTLEMENT, world_id=world_id)
    first = BondRow(source_node_id=folk.id, target_node_id=town.id, kind=BondKind.RULES, epoch=1)
    conquest = BondRow(source_node_id=folk.id, target_node_id=taken.id, kind=BondKind.RULES, epoch=3)
    kept = BondRow(source_node_id=housed.id, target_node_id=home.id, kind=BondKind.RULES, epoch=1, role=BondRole.HOMELAND)
    other = BondRow(source_node_id=housed.id, target_node_id=town.id, kind=BondKind.RULES, epoch=1)
    session.add_all([first, conquest, kept, other])
    await session.flush()
    await session.execute(migration.HOMELESS_FIRST_TOWNS)
    for row in (first, conquest, kept, other):
        await session.refresh(row)
    assert (first.role, conquest.role, kept.role, other.role) == (BondRole.HOMELAND, None, BondRole.HOMELAND, None)
