import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.tables.couplings import DeepSealRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.living import LivingLineRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.polity import OathRow
from aerona.db.tables.powers import PowerRow
from aerona.domain.enums.arcana import SpellForm, SpellTechnique
from aerona.domain.enums.couplings import SealKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.living import CultivationMethod
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.polity import OathKind, OathStatus
from aerona.domain.enums.powers import PowerState
from aerona.domain.models.entity_stats import PlaceStats
from aerona.engine.context import TickContext
from aerona.engine.couplings.control import seal
from aerona.engine.couplings.deep import SealLinks, missing_link, seal_deep
from aerona.engine.couplings.deep import test_seal as try_seal
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, entity, mortal, seed_core_world

RULES = Rules()


async def sealed_place(session: AsyncSession) -> tuple[CoreWorld, EntityRow, TickContext]:
    world = await seed_core_world(session)
    place = await entity(session, "The Old Shaft", EntityType.PLACE, PlaceStats(), world_id=world.world.id, location_id=world.regions[0].id)
    return world, place, await manual_context(session, "test", RULES)


def test_a_seal_bound_to_an_oath_power_or_line_names_it() -> None:
    assert missing_link(SealKind.PACT, SealLinks()) is not None
    assert missing_link(SealKind.PACT, SealLinks(oath_id=3)) is None
    assert missing_link(SealKind.POWER, SealLinks()) is not None and missing_link(SealKind.LIVING, SealLinks()) is not None
    assert missing_link(SealKind.STRUCTURE, SealLinks()) is None


async def test_the_seal_lever_refuses_a_pact_without_its_oath(session: AsyncSession) -> None:
    _, place, ctx = await sealed_place(session)
    with pytest.raises(ValidationFailedError):
        await seal(ctx, place.id, SealKind.PACT, 60)
    row = await seal(ctx, place.id, SealKind.STRUCTURE, 60)
    assert row.strength == 60 and row.kind is SealKind.STRUCTURE


async def test_a_broken_oath_breaks_its_pact_seal_and_those_below_remember(session: AsyncSession) -> None:
    world, place, ctx = await sealed_place(session)
    swearer = await mortal(session, "Ivar", world, world.regions[0].id)
    below = await mortal(session, "Below", world, world.regions[0].id)
    oath = OathRow(swearer_entity_id=swearer.id, recipient_node_id=below.id, kind=OathKind.SILENCE, status=OathStatus.BROKEN, sworn_epoch=1)
    session.add(oath)
    await session.flush()
    row = await seal_deep(ctx, place.id, SealKind.PACT, swearer.id, links=SealLinks(oath_id=oath.id))
    await try_seal(ctx, row)
    await session.flush()
    assert row.strength == 0 and row.broken_epoch == ctx.epoch
    assert "seal.pact_broken" in set(await session.scalars(select(IncidentRow.kind)))
    memory = await session.scalar(select(MemoryRow).where(MemoryRow.holder_node_id == below.id, MemoryRow.kind == MemoryKind.BROKE_OATH))
    assert memory is not None and memory.subject_node_id == swearer.id


async def test_a_seal_of_power_fails_when_its_power_is_gone(session: AsyncSession) -> None:
    world, place, ctx = await sealed_place(session)
    holder = await mortal(session, "Warder", world, world.regions[0].id)
    power = PowerRow(holder_node_id=holder.id, technique=next(iter(SpellTechnique)), form=next(iter(SpellForm)), state=PowerState.LOST, locked=[])
    session.add(power)
    await session.flush()
    row = await seal_deep(ctx, place.id, SealKind.POWER, None, links=SealLinks(power_id=power.id))
    await try_seal(ctx, row)
    assert row.strength == 0 and "seal.broken" in set(await session.scalars(select(IncidentRow.kind)))


async def test_a_living_seal_grows_while_its_line_is_fed_and_fails_when_it_escapes(session: AsyncSession) -> None:
    world, place, ctx = await sealed_place(session)
    line = LivingLineRow(name="the keeping roots", method=next(iter(CultivationMethod)), stability=60, owner_node_id=world.people.id, locked=[])
    session.add(line)
    await session.flush()
    fed = await seal_deep(ctx, place.id, SealKind.LIVING, None, strength=50, links=SealLinks(line_id=line.id))
    await try_seal(ctx, fed)
    assert fed.strength == 50 - (fed.decay - RULES.deep_seals.living_feed) and fed.strength > 50 - fed.decay
    line.escaped = True
    await try_seal(ctx, fed)
    assert fed.strength == 0 and fed.broken_epoch == ctx.epoch
    assert await session.scalar(select(DeepSealRow.id).where(DeepSealRow.broken_epoch.is_(None))) is None
