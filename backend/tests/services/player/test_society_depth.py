import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.ledger_undo import UndoRun
from aerona.db.tables.demography import CohortRow, LabourRow
from aerona.db.tables.polity import HouseMemberRow, PolityMemberRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.society_depth import ClassStandingRow, CommunityNeedRow, CorveeRow, DriftImpositionRow, MobilityEventRow, PolityLoyaltyRow
from aerona.domain.enums.demography import CohortCondition, Job
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.society_depth import DriftCause, MobilityEvent
from aerona.domain.models.entity_stats import PolityStats, SettlementStats
from aerona.services.ledger import changes_of
from aerona.services.ledger_narration import label_names, node_names
from aerona.services.player import society_depth
from aerona.services.player.catalog import ACTIONS_BY_ID
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld, changed_tables, make_entity

ACTIONS = (
    "needs:hold",
    "class:standing",
    "labour:set",
    "labour:corvee",
    "loyalty:edit",
    "drift:impose",
    "drift:edit",
    "drift:cancel",
    "mobility:ennoble",
    "mobility:ruin",
    "mobility:enslave",
    "mobility:manumit",
)


async def town_of(session: AsyncSession, world: PlayerWorld) -> int:
    town = await make_entity(
        session,
        "Ashford",
        EntityType.SETTLEMENT,
        world_id=world.world.id,
        location_id=world.region.id,
        stats=SettlementStats(population=3000, prosperity=50, defense=40, piety=50),
    )
    session.add(
        CommunitySocietyRow(
            entity_id=town.id,
            **{f"share_{item.value}": 10.0 for item in SocialClass},
            **{f"satisfaction_{item.value}": 50 for item in SocialClass},
            stock_food=100,
            stock_ore=100,
            stock_goods=100,
            price_food=100,
            price_ore=100,
            price_goods=100,
        )
    )
    await session.flush()
    return town.id


async def undo(session: AsyncSession, entry_id: int | None, epoch: int) -> list[str]:
    assert entry_id is not None
    changes = await changes_of(session, entry_id)
    report = await UndoRun(session, epoch, changes, label_names(changes, await node_names(session, changes))).run()
    return report.conflicts


def test_every_society_depth_lever_is_catalogued() -> None:
    assert [action for action in ACTIONS if action not in ACTIONS_BY_ID] == []


async def test_needs_and_standing_hold_and_release(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    town = await town_of(session, world)
    held = await society_depth.hold_need(
        scope, society_depth.HoldNeed(community_id=town, social_class=SocialClass.FARMER, commodity=CommodityKind.MEDICINE, held_pct=80)
    )
    assert held.ledger_entry_id is not None and "community_needs" in await changed_tables(session, held.ledger_entry_id)
    row = await session.get(CommunityNeedRow, (town, SocialClass.FARMER, CommodityKind.MEDICINE))
    assert row is not None and row.held_pct == 80
    await society_depth.hold_need(scope, society_depth.HoldNeed(community_id=town, social_class=SocialClass.FARMER, commodity=CommodityKind.MEDICINE))
    assert row.held_pct is None
    standing = await society_depth.edit_standing(
        scope, society_depth.EditStanding(community_id=town, social_class=SocialClass.NOBLE, values={"wealth": 5000, "fed_pct": 90})
    )
    stored = await session.get(ClassStandingRow, (town, SocialClass.NOBLE))
    assert stored is not None and stored.wealth == 5000 and set(stored.locked) == {"wealth", "fed_pct"}
    assert await undo(session, standing.ledger_entry_id, world.cosmos.epoch) == []
    with pytest.raises(ValidationFailedError):
        await society_depth.edit_standing(scope, society_depth.EditStanding(community_id=town, social_class=SocialClass.NOBLE, values={"color": 1}))


async def test_labour_allocation_and_corvee(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    town = await town_of(session, world)
    await society_depth.set_labour(scope, society_depth.SetLabour(community_id=town, job=Job.MINING, workers=120))
    labour = await session.get(LabourRow, (town, Job.MINING))
    assert labour is not None and labour.held and labour.workers == 120
    await society_depth.set_labour(scope, society_depth.SetLabour(community_id=town, job=Job.MINING))
    assert not labour.held
    imposed = await society_depth.set_corvee(scope, society_depth.SetCorvee(community_id=town, share_pct=30))
    corvee = await session.get(CorveeRow, town)
    assert corvee is not None and corvee.share_pct == 30 and imposed.ledger_entry_id is not None
    await society_depth.set_corvee(scope, society_depth.SetCorvee(community_id=town, share_pct=0))
    assert await session.get(CorveeRow, town) is None


async def test_loyalty_terms_hold(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    town = await town_of(session, world)
    realm = await make_entity(session, "Kingdom", EntityType.POLITY, world_id=world.world.id, stats=PolityStats(legitimacy=50, stability=50))
    with pytest.raises(NotFoundError):
        await society_depth.edit_loyalty(scope, society_depth.EditLoyalty(polity_id=realm.id, member_id=town, values={"grievances": 30}))
    session.add(PolityMemberRow(polity_entity_id=realm.id, member_entity_id=town))
    await session.flush()
    await society_depth.edit_loyalty(scope, society_depth.EditLoyalty(polity_id=realm.id, member_id=town, values={"grievances": 30, "loyalty": 20}))
    row = await session.get(PolityLoyaltyRow, (realm.id, town))
    assert row is not None and row.grievances == 30 and row.loyalty == 20 and set(row.locked) == {"grievances", "loyalty"}
    await society_depth.edit_loyalty(scope, society_depth.EditLoyalty(polity_id=realm.id, member_id=town, release=["loyalty"]))
    assert row.locked == ["grievances"]


async def test_drift_pressures_create_edit_cancel(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    town = await town_of(session, world)
    made = await society_depth.impose_drift(
        scope, society_depth.ImposeDrift(community_id=town, cause=DriftCause.FAMINE, axis=ValueAxis.KINSHIP, amount=8, epochs=3)
    )
    imposition = int(made.values["imposition_id"] or 0)
    await society_depth.edit_drift(scope, society_depth.EditDrift(imposition_id=imposition, amount=-4, axis=ValueAxis.MERCY))
    row = await session.get(DriftImpositionRow, imposition)
    assert row is not None and row.amount == -4 and row.axis is ValueAxis.MERCY
    await society_depth.cancel_drift(scope, society_depth.DriftTarget(imposition_id=imposition))
    assert await session.get(DriftImpositionRow, imposition) is None


async def test_mobility_levers_record_events(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    town = await town_of(session, world)
    hero = await make_entity(session, "Brann", EntityType.MORTAL, world_id=world.world.id, location_id=town)
    raised = await society_depth.ennoble(scope, society_depth.MortalTarget(mortal_id=hero.id))
    assert hero.social_class is SocialClass.NOBLE and raised.created_ids
    assert await session.scalar(select(HouseMemberRow.house_entity_id).where(HouseMemberRow.mortal_entity_id == hero.id)) == raised.created_ids[0]
    with pytest.raises(ValidationFailedError):
        await society_depth.ennoble(scope, society_depth.MortalTarget(mortal_id=hero.id))
    await society_depth.ruin(scope, society_depth.Ruin(mortal_id=hero.id, bondage=True))
    assert hero.social_class is SocialClass.SERF_OR_SLAVE
    chained = await society_depth.enslave(scope, society_depth.Enslave(community_id=town, count=50, source=SocialClass.FARMER))
    assert chained.values["moved"] == 50
    bound = await session.scalar(
        select(CohortRow.count).where(
            CohortRow.community_entity_id == town, CohortRow.social_class == SocialClass.SERF_OR_SLAVE, CohortRow.condition == CohortCondition.ENSLAVED
        )
    )
    assert bound
    loosed = await society_depth.manumit(scope, society_depth.Manumit(community_id=town, count=20))
    assert loosed.values["moved"] == 20
    events = [row.event for row in await session.scalars(select(MobilityEventRow).order_by(MobilityEventRow.id))]
    assert events == [MobilityEvent.ENNOBLED, MobilityEvent.RUINED, MobilityEvent.ENSLAVED, MobilityEvent.FREED]
    assert all(row.by_hand for row in await session.scalars(select(MobilityEventRow)))
