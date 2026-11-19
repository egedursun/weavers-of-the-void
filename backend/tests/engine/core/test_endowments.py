from dataclasses import replace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.customs import WelfareRow
from aerona.db.tables.endowments import EndowmentRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.domain.enums.endowments import EndowmentPurpose, EndowmentState, EndowmentTerms
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.polity import DecisionRule, GovernmentKind
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.models.entity_stats import FactionStats, PolityStats, StructureStats
from aerona.engine.context import TickContext
from aerona.engine.endowments.seed import seed_endowments
from aerona.engine.endowments.trust import EndowmentTally, endowed, keep_endowments
from tests.engine.core.factories import CoreWorld, entity, mortal, settlement, tuned_rules


def tuned(ctx: TickContext, **values: int) -> TickContext:
    return replace(ctx, environment=replace(ctx.environment, rules=tuned_rules(endowments=values)))


async def town_with_founder(session: AsyncSession, world: CoreWorld) -> tuple[EntityRow, EntityRow]:
    town = await settlement(session, "Almsford", world, world.regions[0])
    session.add(SettlementProfileRow(settlement_entity_id=town.id, size_tier=SizeTier.TOWN, unrest=40, sanitation=20, locked=[], foreigners={}))
    founder = await mortal(session, "Giver", world, town.id)
    session.add(MortalProfileRow(entity_id=founder.id, renown=10, wealth=50, locked=[]))
    await session.flush()
    return town, founder


async def kinds_of(session: AsyncSession) -> list[str]:
    return list(await session.scalars(select(IncidentRow.kind).where(IncidentRow.kind.startswith("endowment.")).order_by(IncidentRow.id)))


async def test_an_endowment_pays_its_purpose_and_honours_its_founder(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    town, founder = await town_with_founder(session, world)
    row = EndowmentRow(
        founder_node_id=founder.id, beneficiary_node_id=town.id, trustee_node_id=founder.id, purpose=EndowmentPurpose.HEALTH, capital=400, locked=[]
    )
    session.add(row)
    await session.flush()
    tally = EndowmentTally()
    await keep_endowments(tuned(ctx, income_pct=10, effect_per_income=10, renown_per_epoch=2, skim_chance_pct=0), tally)
    profile = await session.get(SettlementProfileRow, town.id)
    giver = await session.get(MortalProfileRow, founder.id)
    assert row.income == 40 and tally.paid == 1
    assert profile is not None and profile.sanitation == 24
    assert giver is not None and giver.renown == 12
    assert await endowed(session, town.id)
    assert "endowment.paid" in await kinds_of(session)


async def test_a_trustee_skims_and_a_faction_trustee_captures(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    town, founder = await town_with_founder(session, world)
    keeper = await mortal(session, "Keeper", world, town.id)
    session.add(MortalProfileRow(entity_id=keeper.id, wealth=0, locked=[]))
    guild = await entity(session, "Guild of Keys", EntityType.FACTION, FactionStats(), world_id=world.world.id, location_id=town.id)
    skimmed = EndowmentRow(founder_node_id=founder.id, beneficiary_node_id=town.id, trustee_node_id=keeper.id, capital=400, locked=[])
    seized = EndowmentRow(founder_node_id=founder.id, beneficiary_node_id=town.id, trustee_node_id=guild.id, capital=400, locked=[])
    session.add_all([skimmed, seized])
    await session.flush()
    tally = EndowmentTally()
    await keep_endowments(tuned(ctx, income_pct=10, skim_chance_pct=100, skim_share_pct=50), tally)
    assert skimmed.skimmed == 20 and tally.skimmed == 1
    assert seized.state is EndowmentState.CAPTURED and tally.captured == 1
    assert {"endowment.skimmed", "endowment.captured"} <= set(await kinds_of(session))


async def test_a_realm_in_debt_confiscates_and_terms_end_endowments(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    town, founder = await town_with_founder(session, world)
    realm = await entity(session, "Crown of Alms", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    session.add(
        PolityProfileRow(
            polity_entity_id=realm.id, government=GovernmentKind.MONARCHY, decision_rule=DecisionRule.AUTOCRATIC, treasury=-50, locked=[], emblem={}
        )
    )
    session.add(PolityMemberRow(polity_entity_id=realm.id, member_entity_id=town.id))
    taken = EndowmentRow(founder_node_id=founder.id, beneficiary_node_id=town.id, capital=300, locked=[])
    kept = EndowmentRow(
        founder_node_id=founder.id, beneficiary_node_id=town.id, capital=300, sheltered=True, terms=EndowmentTerms.FOR_A_TERM, ends_epoch=0, locked=[]
    )
    session.add_all([taken, kept])
    await session.flush()
    tally = EndowmentTally()
    await keep_endowments(tuned(ctx, confiscation_risk_pct=100), tally)
    profile = await session.get(PolityProfileRow, realm.id)
    assert taken.state is EndowmentState.CONFISCATED and profile is not None and profile.treasury == 250
    assert kept.state is EndowmentState.ENDED
    assert {"endowment.confiscated", "endowment.ended"} <= set(await kinds_of(session))


async def test_an_endowment_outlives_its_founder_and_patrons_of_welfare_houses_become_founders(
    session: AsyncSession, world: CoreWorld, ctx: TickContext
) -> None:
    town, founder = await town_with_founder(session, world)
    house = await entity(session, "House of Rest", EntityType.STRUCTURE, StructureStats(), world_id=world.world.id, location_id=town.id)
    session.add(WelfareRow(structure_entity_id=house.id, patron_node_id=founder.id, upkeep=10, locked=[]))
    await session.flush()
    assert await seed_endowments(ctx) == 1
    founder.status, founder.end_epoch = EntityStatus.DEAD, ctx.epoch
    await session.flush()
    tally = EndowmentTally()
    await keep_endowments(tuned(ctx, skim_chance_pct=0), tally)
    row = await session.scalar(select(EndowmentRow).where(EndowmentRow.beneficiary_node_id == house.id))
    assert row is not None and row.capital == 200 and row.outlived and tally.outlived == 1
    assert "endowment.outlived_founder" in await kinds_of(session)
