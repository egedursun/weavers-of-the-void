import importlib.util
import sys
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.structure_effects import STRUCTURE_OWN_EFFECTS
from aerona.catalog.structures import ACTS_AS
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.enums.structure import StructureEffect, StructureKind
from aerona.domain.models.entity_stats import StructureStats
from aerona.engine.structures.own_effects import act_own_effects, own_effects
from tests.engine.core.factories import CoreWorld, entity, settlement
from tests.engine.core.test_minds_w44 import at

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]


async def build(session: AsyncSession, world: CoreWorld, town_id: int, kind: StructureKind, level: int = 3) -> None:
    work = await entity(session, kind.value, EntityType.STRUCTURE, StructureStats(), world_id=world.world.id, location_id=town_id)
    session.add(StructureProfileRow(structure_entity_id=work.id, kind=kind, host_entity_id=town_id, level=level))
    await session.flush()


async def test_every_kind_that_acts_as_another_has_effects_of_its_own() -> None:
    assert all(STRUCTURE_OWN_EFFECTS[kind] for kind in ACTS_AS)
    spec = importlib.util.spec_from_file_location("check_acts_as", REPOSITORY_ROOT / "scripts" / "check_acts_as.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_acts_as"] = module
    spec.loader.exec_module(module)
    assert module.findings() == []


async def test_a_factory_dirties_its_town_and_a_courthouse_settles_it(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Greyhaven", world, world.regions[0])
    await build(session, world, town.id, StructureKind.FACTORY)
    await build(session, world, town.id, StructureKind.COURTHOUSE)
    ctx = await at(session, 2)
    found = await own_effects(ctx, town.id)
    assert found[StructureEffect.POLLUTION] > 0 and found[StructureEffect.JUSTICE_THROUGHPUT] > 0
    profile = SettlementProfileRow(settlement_entity_id=town.id, size_tier=SizeTier.TOWN, sanitation=50, public_order=50, locked=[])
    session.add(profile)
    await session.flush()
    sanitation, order = profile.sanitation, profile.public_order
    assert await act_own_effects(ctx, town, profile) > 0
    assert profile.sanitation < sanitation and profile.public_order > order
