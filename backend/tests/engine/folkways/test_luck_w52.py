from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life.folkways import CHARM_EFFECTS, SIGN_WEIGHTS
from aerona.db.tables.afflictions import AfflictionRow
from aerona.db.tables.folkways import AccusationRow, CharmRow, LuckBeliefRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.justice import CrimeCaseRow
from aerona.db.tables.law_depth import OutlawRow
from aerona.domain.enums.affliction import PackageKind
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.folkways import AccusationOutcome, CharmPower, LuckReach, LuckSign
from aerona.domain.enums.justice import Verdict
from aerona.domain.enums.kind_crafts import ColourFocus
from aerona.domain.enums.mortal import CrimeKind
from aerona.domain.models.entity_stats import ItemStats, PeopleStats
from aerona.engine.folkways.fed import real_charm
from aerona.engine.folkways.luck import read_luck
from aerona.engine.folkways.mishaps import bind_affection
from aerona.engine.folkways.witchcraft import WitchTally, before_judgement
from aerona.engine.primitives.stats import stat_or
from tests.engine.core.factories import CoreWorld, bond, entity, mortal, settlement
from tests.engine.core.test_sacred_w25 import at


async def test_a_reading_of_luck_in_trade_sways_the_town_and_signs_carry_their_creature_or_colour(session: AsyncSession, world: CoreWorld) -> None:
    folk = await entity(session, "Readers of Signs", EntityType.PEOPLE, PeopleStats(population=500), world_id=world.world.id)
    town = await settlement(session, "Luckhaven", world, world.regions[0], prosperity=40)
    session.add(
        LuckBeliefRow(
            people_entity_id=folk.id,
            sign=LuckSign.ANIMAL,
            reach=LuckReach.TRADE,
            lucky=True,
            name="A lucky creature",
            species_entity_id=world.species.id,
            locked=[],
        )
    )
    session.add(
        LuckBeliefRow(
            people_entity_id=folk.id, sign=LuckSign.COLOUR, reach=LuckReach.TRADE, lucky=True, name="A lucky colour", colour=ColourFocus.BLUE, locked=[]
        )
    )
    await session.flush()
    ctx = await at(session, 3, luck={"read_chance": 100})
    assert await read_luck(ctx, town, folk)
    assert stat_or(town, "prosperity", 0) == 40 + ctx.rules.luck.trade_pct
    assert await session.scalar(select(IncidentRow).where(IncidentRow.kind == "luck.read")) is not None
    assert all(SIGN_WEIGHTS[sign](ctx.rules) >= 0 for sign in LuckSign)


async def test_a_real_charm_of_love_binds_the_beloved_and_a_charm_of_travel_scales_with_its_force(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Rosewick", world, world.regions[0])
    lover = await mortal(session, "Ivo", world, town.id)
    beloved = await mortal(session, "Mira", world, town.id)
    await bond(session, lover.id, beloved.id, BondKind.LOVES)
    ctx = await at(session, 3, charms={"love_effect": 100})
    await bind_affection(ctx, lover.id, (True, 100))
    charm = await session.scalar(select(AfflictionRow).where(AfflictionRow.bearer_node_id == beloved.id))
    assert charm is not None and charm.package is PackageKind.CHARM and charm.source_node_id == lover.id
    token = await entity(session, "Road Token", EntityType.ITEM, ItemStats(), world_id=world.world.id, location_id=town.id)
    await bond(session, lover.id, token.id, BondKind.OWNS)
    session.add(CharmRow(item_entity_id=token.id, power=CharmPower.TRAVEL, real=True, strength=60, locked=[]))
    await session.flush()
    expected = round(60 * CHARM_EFFECTS[CharmPower.TRAVEL](ctx.rules) / 50)
    assert await real_charm(session, ctx.rules, lover.id, frozenset({CharmPower.TRAVEL})) == expected


async def accusation(session: AsyncSession, town_id: int, accused_id: int, *, guilty: bool) -> tuple[AccusationRow, CrimeCaseRow]:
    case = CrimeCaseRow(settlement_entity_id=town_id, crime=CrimeKind.WITCHCRAFT, accused_entity_id=accused_id, locked=[])
    session.add(case)
    await session.flush()
    row = AccusationRow(settlement_entity_id=town_id, accused_node_id=accused_id, case_id=case.id, guilty_in_truth=guilty, opened_epoch=1, locked=[])
    session.add(row)
    await session.flush()
    return row, case


async def test_an_accused_may_confess_before_judgement_or_flee_and_be_outlawed(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Ashgrove", world, world.regions[0])
    guilty = await mortal(session, "Corvin", world, town.id)
    innocent = await mortal(session, "Elda", world, town.id)
    confessed, confessed_case = await accusation(session, town.id, guilty.id, guilty=True)
    ctx = await at(session, 3, hunts={"true_confession_pct": 100, "confession_spread_pct": 0})
    await before_judgement(ctx, confessed, confessed_case, WitchTally())
    assert confessed.outcome is AccusationOutcome.CONFESSED and confessed_case.verdict is Verdict.GUILTY
    fled, fled_case = await accusation(session, town.id, innocent.id, guilty=False)
    ctx = await at(session, 3, hunts={"flight_pct": 100}, persuasion={"false_confession_pct": 0})
    await before_judgement(ctx, fled, fled_case, WitchTally())
    assert fled.outcome is AccusationOutcome.FLED and fled_case.verdict is Verdict.FLED
    assert await session.get(OutlawRow, innocent.id) is not None
    assert await session.scalar(select(IncidentRow).where(IncidentRow.kind == "hunt.accusation")) is not None
