from sqlalchemy import select

from aerona.agents.context.cycle_lines import named as name_of
from aerona.agents.context.scope import Scope
from aerona.catalog.means import AIDS, CONTAINERS, LIFTS, MEDIA
from aerona.core.grammar import plural, several
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.governance import OrgGovernanceRow
from aerona.db.tables.honours import HonourHeldRow, HonourKindRow, NamedUnitRow, VeteranGrantRow
from aerona.db.tables.households import HouseholdMemberRow
from aerona.db.tables.means import ContainerStockRow, NavigationKitRow, WaterLiftRow, WritingCustomRow
from aerona.db.tables.military import ArmyUnitRow
from aerona.db.tables.orders import EconomicOrderRow, OrderTransitionRow, SavingRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.warfare import ArmyRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.orders import TransitionStage
from aerona.engine.body.customs import people_id_of
from aerona.engine.honours.persons import head_of, holders_of
from aerona.engine.sacred.places import town_of

LIST_LINES = 3
LIVE = (TransitionStage.PROCLAIMED, TransitionStage.TRANSFERRING)


def spoken(value: str) -> str:
    return value.replace("_", " ")


async def realm_of_town(scope: Scope, town_id: int | None) -> int | None:
    if town_id is None:
        return None
    found = await scope.session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == town_id).limit(1))
    return int(found) if found is not None else None


async def town_means(scope: Scope, town: EntityRow) -> list[str]:
    session = scope.session
    found = []
    lifts = list(await session.scalars(select(WaterLiftRow).where(WaterLiftRow.settlement_entity_id == town.id, WaterLiftRow.count > 0)))
    if lifts:
        found.append(
            "water is lifted here by "
            + ", ".join(several(row.count, LIFTS[row.device].label.lower(), plural(LIFTS[row.device].label.lower())) for row in lifts)
        )
    kits = list(await session.scalars(select(NavigationKitRow).where(NavigationKitRow.holder_entity_id == town.id)))
    if kits:
        found.append("the pilots here use " + ", ".join(f"{AIDS[row.aid].label.lower()} of quality {row.quality}" for row in kits))
    stocks = list(await session.scalars(select(ContainerStockRow).where(ContainerStockRow.community_entity_id == town.id, ContainerStockRow.count > 0)))
    if stocks:
        found.append(
            "goods here are kept in "
            + ", ".join(several(row.count, CONTAINERS[row.kind].label.lower(), plural(CONTAINERS[row.kind].label.lower())) for row in stocks[:LIST_LINES])
        )
    folk = await people_id_of(session, town)
    custom = await session.get(WritingCustomRow, folk) if folk is not None else None
    if custom is not None:
        found.append(f"your people write on {MEDIA[custom.medium].label.lower()}")
    return found


async def order_lines(scope: Scope, realm_id: int) -> list[str]:
    session = scope.session
    found = []
    for order in await session.scalars(select(EconomicOrderRow).where(EconomicOrderRow.polity_entity_id == realm_id).order_by(EconomicOrderRow.id)):
        what = f"for {spoken(order.sector.value)}" if order.sector is not None else "for the realm"
        found.append(
            f"the economic order {what}: {spoken(order.ownership.value)} ownership, {spoken(order.allocation.value)} allocation, "
            f"{spoken(order.labour.value)} labour, shared {spoken(order.distribution.value)} (planning {order.planning_capacity})"
        )
    for row in await session.scalars(select(OrderTransitionRow).where(OrderTransitionRow.polity_entity_id == realm_id, OrderTransitionRow.stage.in_(LIVE))):
        found.append(f"a change of order by {spoken(row.kind.value)} stands at {spoken(row.stage.value)} (change {row.id}, resistance {row.resistance})")
    return found


async def mortal_means_lines(scope: Scope, me: EntityRow) -> list[str]:
    town = await town_of(scope.session, me)
    return await town_means(scope, town) if town is not None else []


async def mortal_economy_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    town = await town_of(session, me)
    realm = await realm_of_town(scope, town.id if town is not None else None)
    found = await order_lines(scope, realm) if realm is not None else []
    household = await session.scalar(select(HouseholdMemberRow.household_id).where(HouseholdMemberRow.member_node_id == me.id).limit(1))
    saving = await session.get(SavingRow, household) if household is not None else None
    if saving is not None:
        found.append(f"your household saves {saving.share_pct}% as {spoken(saving.form.value)}, {saving.saved} put by so far")
    return found


async def person_honour_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    found: list[str] = []
    for row in await session.scalars(
        select(HonourHeldRow).where(HonourHeldRow.holder_node_id == me.id, HonourHeldRow.revoked_epoch.is_(None)).order_by(HonourHeldRow.id)
    ):
        kind = await session.get(HonourKindRow, row.kind_id)
        if kind is not None:
            found.append(f"you hold {kind.name} of {await name_of(scope, kind.conferrer_node_id)}, rank {kind.rank}, worth {kind.worth}")
    conferrers = [node for node in await session.scalars(select(OrgGovernanceRow.org_node_id).where(OrgGovernanceRow.head_node_id == me.id))]
    town = await town_of(session, me)
    realm = await realm_of_town(scope, town.id if town is not None else None)
    if realm is not None and await head_of(session, realm) == me.id:
        conferrers.append(realm)
    for kind in await session.scalars(select(HonourKindRow).where(HonourKindRow.conferrer_node_id.in_(conferrers)).order_by(HonourKindRow.id)):
        holders = [row.id for row in await holders_of(session, kind.id)]
        found.append(f"honour {kind.id}, {kind.name}, is yours to confer; held as honours {', '.join(map(str, holders)) or 'by no one yet'}")
    return found


async def mortal_honours_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    found = await person_honour_lines(scope, me)
    town = await town_of(session, me)
    realm = await realm_of_town(scope, town.id if town is not None else None)
    if realm is None:
        return found
    armies = select(ArmyRow.entity_id).where(ArmyRow.owner_entity_id == realm, ArmyRow.disbanded_epoch.is_(None))
    units = select(ArmyUnitRow.id).where(ArmyUnitRow.army_entity_id.in_(armies))
    for named in await session.scalars(select(NamedUnitRow).where(NamedUnitRow.unit_id.in_(units)).order_by(NamedUnitRow.esprit.desc()).limit(LIST_LINES)):
        found.append(f"{named.name} serves your realm with esprit {named.esprit} after {several(named.battles, 'battle', 'battles')}")
    for grant in await session.scalars(
        select(VeteranGrantRow).where(VeteranGrantRow.polity_entity_id == realm).order_by(VeteranGrantRow.epoch.desc()).limit(LIST_LINES)
    ):
        found.append(f"your realm granted {several(grant.veterans, 'veteran', 'veterans')} {spoken(grant.kind.value)} in epoch {grant.epoch}")
    return found


async def son_economy_lines(scope: Scope, son: SonRow) -> list[str]:
    if son.current_world_id is None:
        return []
    session = scope.session
    found = []
    realms = await session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.POLITY, EntityRow.world_id == son.current_world_id).order_by(EntityRow.id).limit(LIST_LINES)
    )
    for realm in realms:
        for line in await order_lines(scope, realm.id):
            found.append(f"{realm.name} (realm {realm.id}): {line}")
    return found
