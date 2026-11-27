from types import SimpleNamespace
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.culture import ItemHistoryRow, ItemProfileRow
from aerona.db.tables.demography import CohortRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.honours import NamedUnitRow, UnitHonourRow, VeteranGrantRow
from aerona.db.tables.military import ArmyUnitRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow
from aerona.db.tables.warfare import ArmyRow, WarRow, WarSideRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import ItemClass, ItemDeed
from aerona.domain.enums.demography import AgeBand, CohortCondition, SexKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.honours import UnitHonourKind, VeteranGrant
from aerona.domain.enums.military import UnitKind
from aerona.domain.enums.polity import DecisionRule, GovernmentKind
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.war import WarCause, WarSide
from aerona.domain.models.entity_stats import ArmyStats, EventStats, ItemStats, PolityStats
from aerona.engine.context import TickContext
from aerona.engine.honours.units import HonourTally, disband_units, esprit_morale, honour_battle
from aerona.engine.honours.veterans import VeteranTally, keep_veterans
from aerona.engine.military.battle import BattleResult
from aerona.engine.primitives.manual import manual_context
from tests.engine.core.factories import CoreWorld, bond, entity, settlement, tuned_rules


async def at(session: AsyncSession, epoch: int, **rules: dict[str, int]) -> TickContext:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.epoch = epoch
    await session.flush()
    return await manual_context(session, "honours", rules=tuned_rules(**rules))


async def crown(session: AsyncSession, world: CoreWorld, town: EntityRow) -> EntityRow:
    polity = await entity(session, f"Crown of {town.name}", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    session.add(
        PolityProfileRow(
            polity_entity_id=polity.id,
            government=GovernmentKind.MONARCHY,
            decision_rule=DecisionRule.AUTOCRATIC,
            capital_entity_id=town.id,
            core_entity_id=polity.id,
            treasury=5000,
            emblem={},
            legitimacy_parts={},
            locked=[],
        )
    )
    session.add(PolityMemberRow(polity_entity_id=polity.id, member_entity_id=town.id))
    await session.flush()
    return polity


def side(rows: list[ArmyUnitRow], lost: list[int], *, defending: bool) -> SimpleNamespace:
    stacks = [SimpleNamespace(row=row, start=row.count + gone, lost=gone) for row, gone in zip(rows, lost, strict=True)]
    return SimpleNamespace(defending=defending, stacks=stacks)


async def army_of(
    session: AsyncSession, world: CoreWorld, owner: EntityRow, origin: EntityRow, counts: list[int], *, name: str = "First Host"
) -> tuple[EntityRow, list[ArmyUnitRow]]:
    army = await entity(session, name, EntityType.ARMY, ArmyStats(), world_id=world.world.id, location_id=origin.location_id)
    session.add(ArmyRow(entity_id=army.id, owner_entity_id=owner.id, raised_epoch=1))
    rows = [ArmyUnitRow(army_entity_id=army.id, kind=UnitKind.LINE_INFANTRY, count=count, origin_entity_id=origin.id, locked=[]) for count in counts]
    session.add_all(rows)
    await session.flush()
    return army, rows


async def test_units_raised_from_one_land_take_a_name_win_honours_remember_massacres_and_steady_their_side(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Spearholm", world, world.regions[0])
    realm = await crown(session, world, town)
    army, rows = await army_of(session, world, realm, town, [80, 20])
    ctx = await at(session, 2)
    attacker = side(rows, [10, 60], defending=False)
    defender = side([], [], defending=True)
    result = cast(BattleResult, SimpleNamespace(attacker=attacker, defender=defender, winner=attacker))
    tally = HonourTally()
    await honour_battle(ctx, result, "the Ford of Reeds", tally)
    named = list(await session.scalars(select(NamedUnitRow).order_by(NamedUnitRow.id)))
    honours = {row.kind for row in await session.scalars(select(UnitHonourRow))}
    assert tally.named == 2 and len(named) == 2 and honours == {UnitHonourKind.VICTORY, UnitHonourKind.MASSACRE}
    brave, broken = named
    assert brave.esprit > ctx.rules.unit_honours.seed_esprit > broken.esprit and brave.battles == 1
    assert await esprit_morale(ctx, rows) > 0
    await disband_units(ctx, army.id, tally)
    assert brave.unit_id is None and brave.disbanded_epoch == 2 and tally.disbanded == 2
    _, again = await army_of(session, world, realm, town, [50], name="Second Host")
    await honour_battle(ctx, cast(BattleResult, SimpleNamespace(attacker=side(again, [0], defending=False), defender=defender, winner=None)), "the Hill", tally)
    assert tally.reconstituted == 1 and brave.unit_id == again[0].id


async def test_a_realm_grants_its_veterans_pensions_after_a_war_and_its_veterans_band_together(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Oldguard", world, world.regions[0])
    realm = await crown(session, world, town)
    session.add(
        CohortRow(
            community_entity_id=town.id,
            age_band=AgeBand.ADULT,
            sex_kind=SexKind.BEGETTER,
            social_class=SocialClass.WARRIOR,
            condition=CohortCondition.VETERAN,
            count=60,
        )
    )
    event = await entity(session, "The Long War", EntityType.EVENT, EventStats(), world_id=world.world.id)
    war = WarRow(event_entity_id=event.id, world_id=world.world.id, cause=WarCause.HOLY_WAR, started_epoch=1, ended_epoch=2)
    session.add(war)
    await session.flush()
    session.add(WarSideRow(war_id=war.id, entity_id=realm.id, side=WarSide.ATTACKER, joined_epoch=1))
    await session.flush()
    tally = VeteranTally()
    await keep_veterans(await at(session, 2, veterans={"association_from": 30}), tally)
    grant = await session.scalar(select(VeteranGrantRow).where(VeteranGrantRow.polity_entity_id == realm.id))
    association = await session.scalar(select(FactionProfileRow).where(FactionProfileRow.kind == FactionKind.VETERANS))
    assert grant is not None and grant.kind is VeteranGrant.PENSION and grant.veterans == 60 and tally.granted == 1
    assert association is not None and association.home_entity_id == town.id and tally.associations == 1
    profile = await session.get(PolityProfileRow, realm.id)
    assert profile is not None
    before = profile.treasury
    await keep_veterans(await at(session, 3), tally)
    assert profile.treasury < before and tally.pensions_paid >= 1


async def test_honours_are_borne_on_the_realm_s_standard_and_a_storied_unit_earns_a_nickname_in_its_land_s_tongue(
    session: AsyncSession, world: CoreWorld
) -> None:
    town = await settlement(session, "Bannerford", world, world.regions[0])
    await bond(session, town.id, world.language.id, BondKind.SPEAKS)
    realm = await crown(session, world, town)
    standard = await entity(session, "Standard of Bannerford", EntityType.ITEM, ItemStats(), world_id=world.world.id, location_id=town.id)
    session.add(ItemProfileRow(item_entity_id=standard.id, item_class=ItemClass.STANDARD, symbol=True, condition=100, renown=10, locked=[]))
    await bond(session, realm.id, standard.id, BondKind.OWNS)
    _, rows = await army_of(session, world, realm, town, [80])
    ctx = await at(session, 2)
    tally = HonourTally()
    for fight in range(3):
        attacker = side(rows, [5], defending=False)
        await honour_battle(
            ctx, cast(BattleResult, SimpleNamespace(attacker=attacker, defender=side([], [], defending=True), winner=attacker)), f"Field {fight}", tally
        )
    named = await session.scalar(select(NamedUnitRow))
    profile = await session.get(ItemProfileRow, standard.id)
    deeds = list(await session.scalars(select(ItemHistoryRow).where(ItemHistoryRow.item_entity_id == standard.id, ItemHistoryRow.deed == ItemDeed.BATTLE)))
    assert named is not None and named.nickname and tally.nicknamed == 1
    assert profile is not None and profile.renown == 10 + 3 * ctx.rules.unit_honours.standard_renown and len(deeds) == 3 and tally.borne == 3


async def test_veterans_are_granted_after_a_war_whose_sides_all_left_it_at_the_peace(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Peaceford", world, world.regions[0])
    realm = await crown(session, world, town)
    session.add(
        CohortRow(
            community_entity_id=town.id,
            age_band=AgeBand.ADULT,
            sex_kind=SexKind.BEGETTER,
            social_class=SocialClass.WARRIOR,
            condition=CohortCondition.VETERAN,
            count=40,
        )
    )
    event = await entity(session, "The Short War", EntityType.EVENT, EventStats(), world_id=world.world.id)
    war = WarRow(event_entity_id=event.id, world_id=world.world.id, cause=WarCause.HOLY_WAR, started_epoch=1, ended_epoch=2)
    session.add(war)
    await session.flush()
    session.add(WarSideRow(war_id=war.id, entity_id=realm.id, side=WarSide.ATTACKER, joined_epoch=1, left_epoch=2))
    await session.flush()
    tally = VeteranTally()
    await keep_veterans(await at(session, 2), tally)
    grant = await session.scalar(select(VeteranGrantRow).where(VeteranGrantRow.polity_entity_id == realm.id))
    assert grant is not None and grant.veterans == 40 and tally.granted == 1


async def test_a_realm_that_ended_two_wars_rewards_its_veterans_once(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Twicewar", world, world.regions[0])
    realm = await crown(session, world, town)
    session.add(
        CohortRow(
            community_entity_id=town.id,
            age_band=AgeBand.ADULT,
            sex_kind=SexKind.BEGETTER,
            social_class=SocialClass.WARRIOR,
            condition=CohortCondition.VETERAN,
            count=50,
        )
    )
    for title in ("The First War", "The Second War"):
        event = await entity(session, title, EntityType.EVENT, EventStats(), world_id=world.world.id)
        war = WarRow(event_entity_id=event.id, world_id=world.world.id, cause=WarCause.HOLY_WAR, started_epoch=1, ended_epoch=2)
        session.add(war)
        await session.flush()
        session.add(WarSideRow(war_id=war.id, entity_id=realm.id, side=WarSide.ATTACKER, joined_epoch=1))
    await session.flush()
    tally = VeteranTally()
    await keep_veterans(await at(session, 2), tally)
    grants = list(await session.scalars(select(VeteranGrantRow).where(VeteranGrantRow.polity_entity_id == realm.id)))
    assert len(grants) == 1 and tally.granted == 1
