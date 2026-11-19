from dataclasses import replace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.commerce import ShopGoodRow, ShopRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow
from aerona.db.tables.settlement import SettlementInfrastructureRow, SettlementProfileRow
from aerona.db.tables.works import PublicWorksRow, StateEnterpriseRow
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.polity import DecisionRule, GovernmentKind
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.enums.works import EnterpriseForm, EnterpriseManagement, LabourRegime, WorksKind, WorksStatus
from aerona.domain.models.entity_stats import FactionStats, PolityStats
from aerona.engine.context import TickContext
from aerona.engine.works.building import keep_works
from aerona.engine.works.enterprise import keep_enterprises
from aerona.engine.works.seed import seed_works
from tests.engine.core.factories import CoreWorld, entity, mortal, settlement, tuned_rules


async def realm_with_town(session: AsyncSession, world: CoreWorld, treasury: int = 1000) -> tuple[EntityRow, EntityRow]:
    town = await settlement(session, "Ardun", world, world.regions[0])
    session.add(SettlementProfileRow(settlement_entity_id=town.id, size_tier=SizeTier.TOWN, unrest=10, sanitation=20, locked=[], foreigners={}))
    session.add(SettlementInfrastructureRow(settlement_entity_id=town.id, roads=0, locked=[]))
    realm = await entity(session, "Crown of Ardun", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    session.add(
        PolityProfileRow(
            polity_entity_id=realm.id, government=GovernmentKind.MONARCHY, decision_rule=DecisionRule.AUTOCRATIC, treasury=treasury, locked=[], emblem={}
        )
    )
    session.add(PolityMemberRow(polity_entity_id=realm.id, member_entity_id=town.id))
    await session.flush()
    return realm, town


def tuned(ctx: TickContext, family: str, **values: int) -> TickContext:
    return replace(ctx, environment=replace(ctx.environment, rules=tuned_rules(**{family: values})))


async def kinds_of(session: AsyncSession) -> list[str]:
    return list(
        await session.scalars(select(IncidentRow.kind).where(IncidentRow.kind.like("works.%") | IncidentRow.kind.like("enterprise.%")).order_by(IncidentRow.id))
    )


async def test_paid_works_advance_stage_by_stage_and_finish_into_roads(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    realm, town = await realm_with_town(session, world)
    works = PublicWorksRow(polity_entity_id=realm.id, place_node_id=town.id, kind=WorksKind.ROAD, stages=2, quality=80, locked=[])
    session.add(works)
    await session.flush()
    for _ in range(2):
        await keep_works(tuned(ctx, "public_works", labour_per_stage=100))
    infrastructure = await session.get(SettlementInfrastructureRow, town.id)
    profile = await session.get(PolityProfileRow, realm.id)
    assert works.status is WorksStatus.FINISHED and infrastructure is not None and infrastructure.roads == 1
    assert profile is not None and profile.treasury == 800
    assert {"works.stage_done", "works.finished"} <= set(await kinds_of(session))


async def test_unpaid_works_wait_and_pressed_labour_breeds_grievance(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    realm, town = await realm_with_town(session, world, treasury=0)
    waiting = PublicWorksRow(polity_entity_id=realm.id, place_node_id=town.id, kind=WorksKind.SEWER, labour=LabourRegime.PAID, locked=[])
    pressed = PublicWorksRow(polity_entity_id=realm.id, place_node_id=town.id, kind=WorksKind.WALLS, labour=LabourRegime.CORVEE, locked=[])
    session.add_all([waiting, pressed])
    await session.flush()
    tally = await keep_works(tuned(ctx, "public_works", labour_grievance=5, collapse_pct=0))
    profile = await session.get(SettlementProfileRow, town.id)
    assert waiting.stage == 0 and pressed.stage == 1 and tally.delayed == 1
    assert profile is not None and profile.unrest == 15


async def test_neglected_works_decay_into_ruin(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    realm, town = await realm_with_town(session, world, treasury=0)
    works = PublicWorksRow(
        polity_entity_id=realm.id,
        place_node_id=town.id,
        kind=WorksKind.SEWER,
        stages=1,
        stage=1,
        budget=1000,
        condition=10,
        status=WorksStatus.FINISHED,
        locked=[],
    )
    session.add(works)
    await session.flush()
    tally = await keep_works(tuned(ctx, "public_works", decay_per_neglected_epoch=10))
    assert tally.neglected == 1 and works.status is WorksStatus.FAILED
    assert {"works.neglected", "works.failed"} <= set(await kinds_of(session))


async def test_a_monopoly_earns_starves_rivals_and_is_skimmed_then_sold(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    realm, town = await realm_with_town(session, world, treasury=0)
    manager = await mortal(session, "Dun", world, town.id)
    rival = await mortal(session, "Iro", world, town.id)
    shop = ShopRow(settlement_entity_id=town.id, keeper_node_id=rival.id, stock=10, locked=[])
    session.add(shop)
    await session.flush()
    session.add(ShopGoodRow(shop_id=shop.id, commodity=CommodityKind.TOOLS, keeper_node_id=rival.id, locked=[]))
    company = await entity(session, "Ardun Company", EntityType.FACTION, FactionStats(), world_id=world.world.id, location_id=town.id)
    session.add(FactionProfileRow(faction_entity_id=company.id, kind=FactionKind.CHARTERED_COMPANY, locked=[]))
    enterprise = StateEnterpriseRow(
        polity_entity_id=realm.id, sector=CommodityKind.TOOLS, form=EnterpriseForm.MONOPOLY, manager_node_id=manager.id, output=10, corruption=50, locked=[]
    )
    session.add(enterprise)
    await session.flush()
    tally = await keep_enterprises(tuned(ctx, "state_enterprise", skim_chance_pct=100, privatise_debt=100000))
    assert shop.stock < 10 and tally.skimmed > 0 and tally.revenue > 0
    assert enterprise.management is EnterpriseManagement.COMPANY and enterprise.manager_node_id == company.id
    assert {"enterprise.skimmed", "enterprise.privatised"} <= set(await kinds_of(session))


async def test_infrastructure_becomes_finished_works(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    realm, town = await realm_with_town(session, world)
    infrastructure = await session.get(SettlementInfrastructureRow, town.id)
    assert infrastructure is not None
    infrastructure.roads, infrastructure.sewers = 2, True
    await session.flush()
    assert await seed_works(ctx) == 2
    kinds = set(await session.scalars(select(PublicWorksRow.kind).where(PublicWorksRow.place_node_id == town.id)))
    assert kinds == {WorksKind.ROAD, WorksKind.SEWER}
    builder = await session.scalar(select(PublicWorksRow.polity_entity_id).where(PublicWorksRow.place_node_id == town.id).limit(1))
    assert builder == realm.id
