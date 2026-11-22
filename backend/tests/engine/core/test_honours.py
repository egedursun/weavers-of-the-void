from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.honours import HonourHeldRow, HonourKindRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow, PolityProfileRow
from aerona.db.tables.renown import DeedRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.honours import HonourPrivilege
from aerona.domain.enums.mind import ActKind
from aerona.domain.enums.polity import DecisionRule, GovernmentKind, OfficeKind
from aerona.domain.enums.renown import ReputationAxis
from aerona.domain.models.entity_stats import PolityStats
from aerona.engine.economy.purse import points_of
from aerona.engine.honours.persons import HonourTally, confer, immune, revoke, tend_person_honours
from aerona.engine.mortal.standing import standing_of
from aerona.engine.primitives.manual import manual_context
from tests.engine.core.factories import CoreWorld, bond, entity, mortal, settlement, tuned_rules

P = HonourPrivilege


async def crown(session: AsyncSession, world: CoreWorld, name: str) -> tuple[EntityRow, EntityRow, EntityRow]:
    town = await settlement(session, f"{name}ton", world, world.regions[0])
    polity = await entity(session, f"Crown of {name}", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    profile = {
        "government": GovernmentKind.MONARCHY,
        "decision_rule": DecisionRule.AUTOCRATIC,
        "legitimacy": 50,
        "stability": 50,
        "emblem": {},
        "legitimacy_parts": {},
    }
    session.add(PolityProfileRow(polity_entity_id=polity.id, capital_entity_id=town.id, core_entity_id=polity.id, treasury=4000, locked=[], **profile))
    session.add(PolityMemberRow(polity_entity_id=polity.id, member_entity_id=town.id))
    ruler = await mortal(session, f"Ruler of {name}", world, town.id)
    session.add(OfficeRow(polity_entity_id=polity.id, kind=OfficeKind.RULER, holder_entity_id=ruler.id, since_epoch=0, powers=[], locked=[]))
    await session.flush()
    return polity, town, ruler


def order_of(polity: EntityRow, *privileges: HonourPrivilege, **values: object) -> HonourKindRow:
    return HonourKindRow(conferrer_node_id=polity.id, name="Order of the Wall", rank=1, privileges=[item.value for item in privileges], locked=[], **values)


def deed_at(town: EntityRow, doer: EntityRow, axis: ReputationAxis, magnitude: int, epoch: int) -> DeedRow:
    return DeedRow(doer_node_id=doer.id, act=ActKind.RAIDING, axis=axis, place_node_id=town.id, magnitude=magnitude, epoch=epoch, locked=[])


async def renown(session: AsyncSession, being: EntityRow) -> int:
    return await standing_of(session, being, "renown") or 0


async def test_a_realm_honours_a_great_deed_with_renown_land_a_seat_a_title_and_a_pension(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "deed", tuned_rules(honours={"deed_floor": 30, "land_points": 10, "pension_points": 2}))
    polity, town, _ruler = await crown(session, world, "Ardent")
    kind = order_of(polity, P.LAND, P.SEAT, P.TITLE, P.PENSION)
    session.add(kind)
    hero = await mortal(session, "Brave Teo", world, town.id)
    session.add(DeedRow(doer_node_id=hero.id, axis=ReputationAxis.HEROISM, place_node_id=town.id, magnitude=60, epoch=ctx.epoch, locked=[]))
    await session.flush()
    tally = await tend_person_honours(ctx)
    held = await session.scalar(select(HonourHeldRow).where(HonourHeldRow.holder_node_id == hero.id))
    assert tally.conferred == 1 and held is not None and tally.pensions == 1
    assert await renown(session, hero) > 0 and await points_of(session, hero) == 12
    assert hero.title == "Order of the Wall" and (hero.importance or 0) == 1
    assert await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "honour.conferred")) is not None


async def test_an_honour_sold_to_a_favourite_loses_worth_and_one_taken_back_shames(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "sale", tuned_rules(honours={"favour_pct": 100, "sale_worth_loss_pct": 20, "revoke_infamy": 15}))
    polity, town, _ruler = await crown(session, world, "Gilded")
    kind = order_of(polity, P.TITLE)
    session.add(kind)
    rich = await mortal(session, "Rich Oda", world, town.id)
    await session.flush()
    tally = await tend_person_honours(ctx)
    held = await session.scalar(select(HonourHeldRow).where(HonourHeldRow.sold.is_(True)))
    assert tally.sold == 1 and held is not None and kind.worth == 80
    await revoke(ctx, held, HonourTally())
    assert held.revoked_epoch == ctx.epoch and (await standing_of(session, rich, "infamy") or 0) > 0
    assert rich.title is None or held.holder_node_id != rich.id


async def test_an_honour_with_immunity_shields_its_holder_in_the_conferrers_courts(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "immune", tuned_rules())
    polity, town, _ruler = await crown(session, world, "Shield")
    kind = order_of(polity, P.IMMUNITY)
    session.add(kind)
    favourite = await mortal(session, "Safe Ivo", world, town.id)
    await session.flush()
    assert not await immune(session, favourite.id, polity.id)
    await confer(ctx, kind, favourite, tally=HonourTally(), by=None)
    assert await immune(session, favourite.id, polity.id) and not await immune(session, favourite.id, None)


async def test_a_hereditary_honour_passes_to_the_heir_and_a_limited_one_stays_within_its_limit(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "heir", tuned_rules(honours={"deed_floor": 10}))
    polity, town, _ruler = await crown(session, world, "Lineage")
    kind = order_of(polity, P.PRECEDENCE, hereditary=True, holder_limit=2)
    session.add(kind)
    elder, child = await mortal(session, "Old Mara", world, town.id), await mortal(session, "Young Mara", world, town.id)
    await bond(session, elder.id, child.id, BondKind.PARENT_OF)
    await session.flush()
    await confer(ctx, kind, elder, tally=HonourTally(), by=None)
    elder.status, elder.end_epoch = EntityStatus.DEAD, ctx.epoch
    for index in range(3):
        doer = await mortal(session, f"Doer {index}", world, town.id)
        session.add(DeedRow(doer_node_id=doer.id, axis=ReputationAxis.HEROISM, place_node_id=town.id, magnitude=90, epoch=ctx.epoch, locked=[]))
    await session.flush()
    tally = await tend_person_honours(ctx)
    heirs = await session.scalar(select(HonourHeldRow).where(HonourHeldRow.holder_node_id == child.id, HonourHeldRow.inherited.is_(True)))
    live = list(await session.scalars(select(HonourHeldRow).where(HonourHeldRow.kind_id == kind.id, HonourHeldRow.revoked_epoch.is_(None))))
    assert heirs is not None and tally.inherited == 1 and len(live) == 2


async def test_a_ruled_realm_founds_its_first_honour_for_a_deed_its_people_praise_and_confers_it(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "found", tuned_rules(honours={"deed_floor": 10, "favour_pct": 0}))
    polity, town, _ruler = await crown(session, world, "Founding")
    scoundrel = await mortal(session, "Sly Pell", world, town.id)
    session.add(
        DeedRow(doer_node_id=scoundrel.id, act=ActKind.RAIDING, axis=ReputationAxis.CRUELTY, place_node_id=town.id, magnitude=40, epoch=ctx.epoch, locked=[])
    )
    await session.flush()
    assert (await tend_person_honours(ctx)).founded == 0
    hero = await mortal(session, "Bold Asa", world, town.id)
    session.add(
        DeedRow(doer_node_id=hero.id, act=ActKind.RAIDING, axis=ReputationAxis.HEROISM, place_node_id=town.id, magnitude=12, epoch=ctx.epoch, locked=[])
    )
    await session.flush()
    tally = await tend_person_honours(ctx)
    kind = await session.scalar(select(HonourKindRow).where(HonourKindRow.conferrer_node_id == polity.id))
    assert tally.founded == 1 and kind is not None and kind.rank == 1 and kind.privileges == [P.PRECEDENCE.value]
    holders = set(await session.scalars(select(HonourHeldRow.holder_node_id).where(HonourHeldRow.kind_id == kind.id)))
    assert holders == {hero.id}
    assert (await tend_person_honours(ctx)).founded == 0
