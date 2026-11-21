from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.divine_conceptions import DivineConceptionRow, GodReadingRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import CultTenetRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.divine_conceptions import CreatorPlace, DivineCount, DivineNearness, DivinePersonhood, GodReading
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faith import TenetKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import IncidentTier
from aerona.domain.models.entity_stats import CultStats
from aerona.engine.divine_conceptions.conception import conceive, syncretism_fit, theodicy_factor
from aerona.engine.divine_conceptions.tend import ConceptionTally, drift, tried_by_acts, tried_by_creator
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.queries import active_bonds
from tests.engine.core.factories import CoreWorld, bond, entity, settlement, son_draft, tuned_rules


async def faith_of(
    session: AsyncSession, world: CoreWorld, name: str, *gods: int, tenets: tuple[TenetKind, ...] = (), town: EntityRow | None = None
) -> EntityRow:
    cult = await entity(
        session, name, EntityType.CULT, CultStats(followers=100, zeal=50, influence=30), world_id=world.world.id, location_id=town.id if town else None
    )
    for god in gods:
        await bond(session, cult.id, god, BondKind.WORSHIPS)
    for tenet in tenets:
        session.add(CultTenetRow(cult_entity_id=cult.id, tenet=tenet))
    await session.flush()
    return cult


async def test_faiths_conceive_the_divine_from_their_gods_and_tenets_and_read_the_others(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "conceive", tuned_rules())
    other = await SonRepository(session).create(son_draft("Velmar", world.world.id))
    lone = await conceive(ctx, await faith_of(session, world, "The One Way", world.son.id, tenets=(TenetKind.EXCLUSIVITY,)))
    twin = await conceive(ctx, await faith_of(session, world, "The Open Way", world.son.id, tenets=(TenetKind.SYNCRETIC_OPENNESS,)))
    kin = await conceive(ctx, await faith_of(session, world, "The Kin Way", tenets=(TenetKind.ANCESTOR_VENERATION,)))
    assert lone.count is DivineCount.ONE and twin.count is DivineCount.MANY and kin.count is DivineCount.ALL_IS_DIVINE
    assert kin.nearness is DivineNearness.PRESENT and lone.nearness is DivineNearness.DISTANT
    doubted = await session.get(GodReadingRow, (lone.cult_entity_id, other.id))
    trusted = await session.get(GodReadingRow, (lone.cult_entity_id, world.son.id))
    assert doubted is not None and doubted.reading is GodReading.DEMON and trusted is not None and trusted.reading is GodReading.TRUE
    assert await theodicy_factor(session, lone.cult_entity_id) == 0.5
    assert await syncretism_fit(session, 50, lone.cult_entity_id, twin.cult_entity_id) == 0.5
    assert await syncretism_fit(session, 50, twin.cult_entity_id, kin.cult_entity_id) == 1.5


async def act_openly(session: AsyncSession, world: CoreWorld, god: int, town: EntityRow, epoch: int) -> None:
    incident = IncidentRow(kind="player.history", epoch=epoch, year=1, world_id=world.world.id, place_entity_id=town.id, tier=IncidentTier.STEPS, locked=[])
    session.add(incident)
    await session.flush()
    session.add(IncidentParticipantRow(incident_id=incident.id, node_id=god, role=IncidentRole.ACTOR, position=0))
    await session.flush()


async def test_a_doubted_god_acting_openly_strains_a_faith_until_it_yields(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "yield", tuned_rules(divine_conceptions={"denied_god_crisis_pct": 100, "split_pct": 0}))
    town = await settlement(session, "Shrineby", world, world.regions[0])
    other = await SonRepository(session).create(son_draft("Orrin", world.world.id))
    row = await conceive(ctx, await faith_of(session, world, "The Narrow Way", world.son.id, tenets=(TenetKind.EXCLUSIVITY,), town=town))
    await act_openly(session, world, other.id, town, ctx.epoch)
    tally = ConceptionTally()
    await tried_by_acts(ctx, row, [town.id], tally)
    reading = await session.get(GodReadingRow, (row.cult_entity_id, other.id))
    assert tally.tested == 1 and reading is not None and reading.reading is GodReading.SERVANT and row.count is DivineCount.ONE_ABOVE_MANY
    assert await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "faith.conception_changed")) is not None


async def test_a_strained_faith_may_split_and_its_sect_worships_the_god_it_could_not_deny(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "split", tuned_rules(divine_conceptions={"denied_god_crisis_pct": 100, "split_pct": 100}))
    town = await settlement(session, "Rifton", world, world.regions[0])
    other = await SonRepository(session).create(son_draft("Kesh", world.world.id))
    row = await conceive(ctx, await faith_of(session, world, "The Old Way", world.son.id, tenets=(TenetKind.EXCLUSIVITY,), town=town))
    await act_openly(session, world, other.id, town, ctx.epoch)
    tally = ConceptionTally()
    await tried_by_acts(ctx, row, [town.id], tally)
    sect = await session.scalar(select(DivineConceptionRow).where(DivineConceptionRow.cult_entity_id != row.cult_entity_id))
    assert tally.split == 1 and sect is not None and sect.count is DivineCount.MANY
    worship = await active_bonds(session, [BondKind.WORSHIPS], sources=[sect.cult_entity_id])
    assert [item.target_node_id for item in worship] == [other.id]


async def test_a_conception_drifts_one_step_on_one_axis(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "drift", tuned_rules(divine_conceptions={"drift_per_epoch_pct": 100}))
    row = await conceive(ctx, await faith_of(session, world, "The Turning Way", world.son.id))
    before = (row.count, row.nearness, row.personhood, row.creator_place)
    tally = ConceptionTally()
    await drift(ctx, row, tally)
    assert tally.shifted == 1 and (row.count, row.nearness, row.personhood, row.creator_place) != before


async def test_the_creator_acting_openly_is_acknowledged_by_the_unknowing_and_strains_those_who_deny_it(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "creator", tuned_rules(divine_conceptions={"denied_god_crisis_pct": 40}))
    town = await settlement(session, "Makerby", world, world.regions[0])
    open_row = await conceive(ctx, await faith_of(session, world, "The Seeking Way", world.son.id, town=town))
    denying = await conceive(ctx, await faith_of(session, world, "The Proud Way", world.son.id, town=town))
    denying.creator_place, denying.personhood = CreatorPlace.DENIED, DivinePersonhood.PRINCIPLE
    await act_openly(session, world, world.creator.id, town, ctx.epoch)
    tally = ConceptionTally()
    await tried_by_creator(ctx, open_row, [town.id], tally)
    await tried_by_creator(ctx, denying, [town.id], tally)
    assert open_row.creator_place is CreatorPlace.ACKNOWLEDGED and denying.strain == 10 and tally.tested == 1
