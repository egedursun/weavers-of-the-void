from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.war_w52 import AGENT_STATES, MOTIVES, OPERATIONS, PEACE_OPERATIONS, WAR_OPERATIONS
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.intrigue import BeliefRow
from aerona.db.tables.military import SpyAgentRow, SpyNetworkRow
from aerona.db.tables.relations import RelationshipRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.law_depth import RecruitMotive
from aerona.domain.enums.military import AgentStatus, SpyCover, SpyOperation
from aerona.engine.military.spies_w52 import disinform, infiltrate, inside, keep_motive, motive_by_heart, watch_agents
from tests.engine.warfare.factories import make, make_ctx


def test_every_operation_motive_and_state_has_its_catalogue_entry() -> None:
    assert set(OPERATIONS) == set(SpyOperation) and set(MOTIVES) == set(RecruitMotive) and set(AGENT_STATES) == set(AgentStatus)
    assert SpyOperation.DISINFORM in WAR_OPERATIONS and SpyOperation.INFILTRATE in PEACE_OPERATIONS


async def network_between(session: AsyncSession, world_id: int) -> tuple[SpyNetworkRow, int, int]:
    owner = await make(session, "Iron Crown", EntityType.SETTLEMENT, world_id, population=3000, defense=30)
    target = await make(session, "Highwall", EntityType.SETTLEMENT, world_id, population=3000, defense=40)
    network = SpyNetworkRow(
        owner_entity_id=owner.id, target_entity_id=target.id, agent_ids=[], depth=60, cover=SpyCover.MERCHANT, since_epoch=1, revealed_aims=[], locked=[]
    )
    session.add(network)
    await session.flush()
    return network, owner.id, target.id


async def test_a_placed_agent_widens_access_and_false_beliefs_reach_the_rival(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    network, owner_id, target_id = await network_between(session, world_id)
    target = await session.get(EntityRow, target_id)
    master = await session.get(EntityRow, owner_id)
    assert target is not None and master is not None
    assert inside(ctx, network, 100) == 100
    await infiltrate(ctx, master, target, network)
    assert network.institution_entity_id == target.id
    assert inside(ctx, network, 100) == 100 + ctx.rules.espionage.infiltrate_access_pct
    await disinform(ctx, master, target, network)
    assert await session.scalar(select(BeliefRow).where(BeliefRow.holder_node_id == target_id)) is not None


async def test_love_wins_an_agent_who_turns_cold_when_the_bond_breaks_and_exposure_is_watched(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    network, owner_id, target_id = await network_between(session, world_id)
    recruit = await make(session, "Ilse", EntityType.MORTAL, world_id, location_id=target_id)
    bond = RelationshipRow(holder_node_id=recruit.id, subject_node_id=owner_id, romance=90, kinds=[], since_epoch=1, last_epoch=1, locked=[])
    session.add(bond)
    await session.flush()
    assert await motive_by_heart(ctx, network, recruit) is RecruitMotive.LOVE
    agent = SpyAgentRow(
        network_id=network.id,
        mortal_entity_id=recruit.id,
        motive=RecruitMotive.LOVE,
        loyalty=75,
        exposure=90,
        status=AgentStatus.ACTIVE,
        since_epoch=1,
        locked=[],
    )
    session.add(agent)
    await session.flush()
    assert await keep_motive(ctx, network, agent) == ctx.rules.spy_depth.love_double_risk / 100 and agent.loyalty == 75
    bond.romance = 0
    await keep_motive(ctx, network, agent)
    assert agent.loyalty == ctx.rules.spy_depth.broken_bond_loyalty
    assert await watch_agents(ctx, network) == 1
    assert agent.status in {AgentStatus.EXPOSED, AgentStatus.MISSING}
