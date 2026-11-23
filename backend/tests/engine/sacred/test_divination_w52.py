from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.sacred import DIVINATION_ACCURACY
from aerona.db.tables.faith import SpiritProfileRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.sacred import DivinationSystemRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faith import AfterlifeState
from aerona.domain.enums.mind import ValueAxis, ValueHolder
from aerona.domain.enums.sacred import DivinationKind, DivinationQuestion, DivinationValidity, OmenVerdict
from aerona.domain.models.entity_stats import PeopleStats, SpiritStats
from aerona.engine.mind.book import write_values
from aerona.engine.sacred import control
from aerona.engine.sacred.foresight import question_for, validity_of
from tests.engine.core.factories import CoreWorld, bond, entity, mortal, settlement
from tests.engine.core.test_sacred_w25 import at, ruled_realm


async def test_asking_the_dead_reads_true_where_restless_dead_dwell_and_every_kind_has_its_accuracy(session: AsyncSession, world: CoreWorld) -> None:
    folk = await entity(session, "Askers of the Dead", EntityType.PEOPLE, PeopleStats(population=500), world_id=world.world.id)
    town = await settlement(session, "Hollowcairn", world, world.regions[0])
    await bond(session, town.id, folk.id, BondKind.DESCENDS_FROM)
    system = DivinationSystemRow(people_entity_id=folk.id, kind=DivinationKind.SPIRIT_CONSULTATION, locked=[])
    session.add(system)
    await session.flush()
    ctx = await at(session, 3)
    assert await validity_of(ctx, system) is DivinationValidity.NOISE
    ghost = await entity(session, "Restless One", EntityType.SPIRIT, SpiritStats(), world_id=world.world.id, location_id=town.id)
    session.add(SpiritProfileRow(spirit_entity_id=ghost.id, state=AfterlifeState.WANDERING, locked=[]))
    await session.flush()
    assert await validity_of(ctx, system) is DivinationValidity.NATURAL_LAW
    assert {kind: DIVINATION_ACCURACY[kind](ctx.rules) for kind in DivinationKind}[DivinationKind.SCRYING] == ctx.rules.divination.scrying_accuracy


async def test_a_sick_ruler_asks_about_the_illness_and_a_heeded_omen_sways_its_care(session: AsyncSession, world: CoreWorld) -> None:
    folk = await entity(session, "Court Folk", EntityType.PEOPLE, PeopleStats(population=500), world_id=world.world.id)
    town = await settlement(session, "Palehall", world, world.regions[0])
    await bond(session, town.id, folk.id, BondKind.DESCENDS_FROM)
    ruler = await mortal(session, "Aurel", world, town.id)
    session.add(MortalProfileRow(entity_id=ruler.id, health=30, locked=[]))
    await write_values(session, ValueHolder.PERSONAL, ruler.id, {ValueAxis.SUPERSTITION: 90})
    realm = await ruled_realm(session, world, town, ruler)
    system = DivinationSystemRow(people_entity_id=folk.id, kind=DivinationKind.EARTH_SIGNS, diviners=2, locked=[])
    session.add(system)
    await session.flush()
    ctx = await at(session, 3)
    assert await question_for(ctx, realm.id, ruler) is DivinationQuestion.ILLNESS
    reading = await control.read_omens(ctx, realm.id, DivinationQuestion.ILLNESS, verdict=OmenVerdict.AUSPICIOUS, swayed_by=None, system_id=system.id)
    profile = await session.get(MortalProfileRow, ruler.id)
    assert reading.heeded and profile is not None and profile.health == 30 + ctx.rules.divination.illness_health
