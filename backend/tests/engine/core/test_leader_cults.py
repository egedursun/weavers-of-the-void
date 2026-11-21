from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.belonging import SatireRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.collective import AccountRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.leader_cults import LeaderCultRow
from aerona.db.tables.polity import OathRow, OfficeRow, PolityMemberRow, PolityProfileRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.leader_cults import CultFate, CultInstrument
from aerona.domain.enums.polity import DecisionRule, GovernmentKind, OfficeKind
from aerona.domain.enums.reckoning import ReckoningMeasure
from aerona.domain.models.entity_stats import PolityStats
from aerona.engine.context import TickContext
from aerona.engine.leader_cults.cults import CultTally, add_instrument, begin, raise_cults, tend_cults, tend_living
from aerona.engine.primitives.manual import manual_context
from aerona.engine.reckoning.book import ReckoningTally
from aerona.engine.reckoning.opening import open_reckoning
from tests.engine.core.factories import CoreWorld, entity, mortal, settlement, tuned_rules


async def ruled(session: AsyncSession, world: CoreWorld, *, stability: int = 60) -> tuple[EntityRow, EntityRow, EntityRow]:
    capital = await settlement(session, "Cultholm", world, world.regions[0], population=4000)
    realm = await entity(session, "The Venerating Crown", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    session.add(
        PolityProfileRow(
            polity_entity_id=realm.id,
            government=next(iter(GovernmentKind)),
            decision_rule=next(iter(DecisionRule)),
            core_entity_id=capital.id,
            capital_entity_id=capital.id,
            treasury=500,
            legitimacy=40,
            stability=stability,
        )
    )
    session.add(PolityMemberRow(polity_entity_id=realm.id, member_entity_id=capital.id))
    leader = await mortal(session, "Saro Vael", world, capital.id)
    officer = await mortal(session, "Ilm Doran", world, capital.id)
    session.add(OfficeRow(polity_entity_id=realm.id, kind=OfficeKind.RULER, holder_entity_id=leader.id, since_epoch=0, powers=[]))
    session.add(OfficeRow(polity_entity_id=realm.id, kind=OfficeKind.MARSHAL, holder_entity_id=officer.id, since_epoch=0, powers=[]))
    await session.flush()
    return realm, leader, officer


async def test_instruments_write_the_official_life_and_bind_the_officers_by_oath(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    realm, leader, officer = await ruled(session, world)
    tally = CultTally()
    cult = await begin(ctx, leader, [officer.id], tally)
    assert cult.polity_entity_id == realm.id and tally.begun == 1
    await add_instrument(ctx, cult, CultInstrument.OFFICIAL_BIOGRAPHY, tally)
    await add_instrument(ctx, cult, CultInstrument.OATHS_OF_LOYALTY, tally)
    assert await session.scalar(select(AccountRow.id).where(AccountRow.subject_node_id == leader.id)) is not None
    oath = await session.scalar(select(OathRow).where(OathRow.swearer_entity_id == officer.id))
    assert oath is not None and oath.recipient_node_id == leader.id and tally.added == 2


async def test_a_cult_climbs_lends_legitimacy_costs_the_treasury_and_wears_sincerity_when_it_runs_ahead(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "climb", tuned_rules(leader_cults={"intensity_step": 50}))
    realm, leader, _officer = await ruled(session, world, stability=10)
    tally = CultTally()
    cult = await begin(ctx, leader, [], tally)
    for instrument in (CultInstrument.IMAGES_IN_PUBLIC, CultInstrument.STAGED_GATHERINGS, CultInstrument.HOLIDAYS):
        await add_instrument(ctx, cult, instrument, tally)
    profile = await session.get(PolityProfileRow, realm.id)
    assert profile is not None
    before_treasury, before_sincerity = profile.treasury, cult.sincerity
    await tend_living(ctx, cult, tally)
    assert cult.intensity == 40 and profile.treasury == before_treasury - 3 * ctx.rules.leader_cults.cost_per_instrument
    assert profile.legitimacy > 40 and cult.sincerity < before_sincerity


async def test_a_ban_on_criticism_punishes_mockery_of_the_leader(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    realm, leader, officer = await ruled(session, world)
    tally = CultTally()
    cult = await begin(ctx, leader, [], tally)
    await add_instrument(ctx, cult, CultInstrument.BAN_ON_CRITICISM, tally)
    satire = SatireRow(satirist_entity_id=officer.id, target_entity_id=leader.id, polity_entity_id=realm.id, epoch=ctx.epoch, locked=[])
    session.add(satire)
    await session.flush()
    await tend_living(ctx, cult, tally)
    assert satire.punished and not satire.tolerated and tally.punished == 1


async def test_a_dead_leaders_cult_passes_to_the_heir_or_becomes_a_faith(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "death", tuned_rules(leader_cults={"apotheosis_chance_pct": 100}))
    realm, leader, officer = await ruled(session, world)
    cult = await begin(ctx, leader, [], CultTally())
    cult.intensity = 80
    leader.status, leader.end_epoch = EntityStatus.DEAD, ctx.epoch
    ruler = await session.scalar(select(OfficeRow).where(OfficeRow.polity_entity_id == realm.id, OfficeRow.kind == OfficeKind.RULER))
    assert ruler is not None
    ruler.holder_entity_id = officer.id
    tally = await tend_cults(ctx)
    assert cult.fate is CultFate.PASSED_ON and tally.passed == 1
    heirs = await session.scalar(select(LeaderCultRow).where(LeaderCultRow.leader_node_id == officer.id))
    assert heirs is not None and heirs.intensity == 40
    heirs.intensity = 100
    officer.status, officer.end_epoch = EntityStatus.DEAD, ctx.epoch
    ruler.holder_entity_id = None
    tally = await tend_cults(ctx)
    assert heirs.fate is CultFate.BECAME_FAITH and heirs.faith_entity_id is not None
    worship = await session.scalar(select(BondRow).where(BondRow.source_node_id == heirs.faith_entity_id, BondRow.kind == BondKind.WORSHIPS))
    assert worship is not None and worship.target_node_id == officer.id


async def test_a_reckoning_with_the_fallen_tears_down_their_cult_and_rulers_raise_new_ones(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "reckon", tuned_rules(leader_cults={"start_chance_pct": 100}))
    realm, leader, _officer = await ruled(session, world)
    tally = CultTally()
    await raise_cults(ctx, tally)
    cult = await session.scalar(select(LeaderCultRow).where(LeaderCultRow.leader_node_id == leader.id))
    assert cult is not None and tally.begun == 1 and CultInstrument.IMAGES_IN_PUBLIC.value in cult.instruments
    await open_reckoning(ctx, realm, leader.id, [(ReckoningMeasure.MEMORIAL, 50)], by=None, fallen_epoch=ctx.epoch, tally=ReckoningTally())
    assert cult.fate is CultFate.TORN_DOWN
