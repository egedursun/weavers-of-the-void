from sqlalchemy import select

from aerona.catalog.war_w52 import MOTIVES, OPERATIONS, WORKING_STATES
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.military import SpyAgentRow, SpyNetworkRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.warfare import ArmyRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.intrigue import BeliefSource
from aerona.domain.enums.law_depth import RecruitMotive
from aerona.domain.enums.military import AgentStatus, SpyOperation
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.intrigue.beliefs import believe
from aerona.engine.mind.book import skill_level
from aerona.engine.mind.opinion import mortal_rulers
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import stat
from aerona.engine.recording.record import record
from aerona.engine.relations.book import relation

SOLDIERS = "soldiers"
STATUS = "status"


async def succeeds(ctx: TickContext, network: SpyNetworkRow, operation: SpyOperation) -> bool:
    difficulty = int(getattr(ctx.rules.espionage, OPERATIONS[operation].difficulty_rule))
    skill = await skill_level(ctx.session, network.spymaster_entity_id, SkillKind.INTRIGUE) if network.spymaster_entity_id is not None else 0
    edge = (network.depth + skill) / 2
    chance = clamp_int(PERCENT - difficulty + round_half_up(edge * difficulty / PERCENT), 0, PERCENT)
    return ctx.rng(f"spy.try.{network.id}.{operation.value}.{ctx.epoch}").chance(chance)


def inside(ctx: TickContext, network: SpyNetworkRow, amount: float) -> float:
    if network.institution_entity_id is None:
        return amount
    return amount * (PERCENT + ctx.rules.espionage.infiltrate_access_pct) / PERCENT


async def institution_in(ctx: TickContext, target: EntityRow) -> EntityRow:
    found = await ctx.session.scalar(
        select(EntityRow)
        .join(FactionProfileRow, FactionProfileRow.faction_entity_id == EntityRow.id)
        .where(FactionProfileRow.home_entity_id == target.id, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
        .limit(1)
    )
    return found or target


async def infiltrate(ctx: TickContext, spymaster: EntityRow, target: EntityRow, network: SpyNetworkRow) -> str | None:
    if "institution_entity_id" in network.locked:
        return None
    place = await institution_in(ctx, target)
    network.institution_entity_id = place.id
    written = await record(
        ctx,
        "spy.operation",
        roles={IncidentRole.ACTOR: spymaster.id, IncidentRole.TARGET: target.id, IncidentRole.PLACE: place.id},
        facts={"operation": SpyOperation.INFILTRATE},
        place=target.id,
    )
    return written.text


async def exfiltrate(ctx: TickContext, spymaster: EntityRow, target: EntityRow, network: SpyNetworkRow) -> str | None:
    agents = [
        row
        for row in await ctx.session.scalars(
            select(SpyAgentRow).where(SpyAgentRow.network_id == network.id, SpyAgentRow.status.in_(list(WORKING_STATES))).order_by(SpyAgentRow.id)
        )
        if STATUS not in row.locked and not held(row.mortal_entity_id)
    ]
    if not agents:
        return None
    agent = max(agents, key=lambda row: (row.exposure, row.id))
    mortal = await living_entity(ctx.session, agent.mortal_entity_id) if agent.mortal_entity_id is not None else None
    caught = ctx.rng(f"spy.exfiltrate.{agent.id}.{ctx.epoch}").chance(ctx.rules.espionage.exfiltrate_capture_pct)
    agent.status, agent.ended_epoch = (AgentStatus.CAUGHT if caught else AgentStatus.RETIRED), ctx.epoch
    if not caught and mortal is not None:
        mortal.location_id = spymaster.location_id if spymaster.location_id is not None else spymaster.id
    network.agent_ids = [item for item in network.agent_ids if item != agent.mortal_entity_id]
    if "agents" not in network.locked:
        network.agents = max(0, network.agents - 1)
    roles = {IncidentRole.ACTOR: spymaster.id, IncidentRole.TARGET: target.id, **({IncidentRole.SUBJECT: mortal.id} if mortal is not None else {})}
    if caught and mortal is not None:
        written = await record(ctx, "spy.exfiltrate_caught", roles=roles, place=target.id)
    else:
        written = await record(ctx, "spy.operation", roles=roles, facts={"operation": SpyOperation.EXFILTRATE}, place=target.id)
    return written.text


async def disinform(ctx: TickContext, spymaster: EntityRow, target: EntityRow, network: SpyNetworkRow) -> str | None:
    confidence = round_half_up(ctx.rules.espionage.disinform_confidence * max(network.depth, PERCENT // 4) / PERCENT)
    army = await ctx.session.scalar(
        select(ArmyRow).where(ArmyRow.owner_entity_id == network.owner_entity_id, ArmyRow.disbanded_epoch.is_(None)).order_by(ArmyRow.entity_id).limit(1)
    )
    host = await living_entity(ctx.session, army.entity_id) if army is not None else None
    if host is not None:
        planted = await believe(
            ctx, target.id, host.id, SOLDIERS, (stat(host, "size") or 0) * 2, source=BeliefSource.DECEPTION, confidence=confidence, false=True
        )
    else:
        planted = await believe(
            ctx, target.id, spymaster.id, "defense", (stat(spymaster, "defense") or 0) * 2, source=BeliefSource.DECEPTION, confidence=confidence, false=True
        )
    if planted is None:
        return None
    written = await record(
        ctx,
        "spy.operation",
        roles={IncidentRole.ACTOR: spymaster.id, IncidentRole.TARGET: target.id},
        facts={"operation": SpyOperation.DISINFORM},
        place=target.id,
    )
    return written.text


async def motive_by_heart(ctx: TickContext, network: SpyNetworkRow, mortal: EntityRow) -> RecruitMotive | None:
    recruiter = network.spymaster_entity_id or network.owner_entity_id
    bond = await relation(ctx.session, mortal.id, recruiter)
    if bond is not None and bond.romance >= ctx.rules.spy_depth.love_from:
        return RecruitMotive.LOVE
    rulers = await mortal_rulers(ctx.session, network.target_entity_id)
    foes = [network.target_entity_id, *rulers]
    grudge = await ctx.session.scalar(
        select(MemoryRow.id).where(MemoryRow.holder_node_id == mortal.id, MemoryRow.subject_node_id.in_(foes), MemoryRow.magnitude < 0).limit(1)
    )
    return RecruitMotive.REVENGE if grudge is not None else None


async def bond_holds(ctx: TickContext, network: SpyNetworkRow, agent: SpyAgentRow) -> bool:
    spec = MOTIVES[agent.motive]
    if spec.bonded and agent.mortal_entity_id is not None:
        bond = await relation(ctx.session, agent.mortal_entity_id, network.spymaster_entity_id or network.owner_entity_id)
        return bond is not None and bond.romance >= ctx.rules.spy_depth.love_from
    if spec.vengeful:
        return await living_entity(ctx.session, network.target_entity_id) is not None and bool(await mortal_rulers(ctx.session, network.target_entity_id))
    return True


async def keep_motive(ctx: TickContext, network: SpyNetworkRow, agent: SpyAgentRow) -> float:
    spec = MOTIVES[agent.motive]
    if "loyalty" not in agent.locked and not await bond_holds(ctx, network, agent):
        table = ctx.rules.spy_depth
        agent.loyalty = min(agent.loyalty, table.broken_bond_loyalty if spec.bonded else table.fallen_target_loyalty)
    return int(getattr(ctx.rules.spy_depth, spec.double_risk_rule)) / PERCENT


async def watch_agents(ctx: TickContext, network: SpyNetworkRow) -> int:
    table = ctx.rules.espionage
    changed = 0
    for agent in list(await ctx.session.scalars(select(SpyAgentRow).where(SpyAgentRow.network_id == network.id).order_by(SpyAgentRow.id))):
        if STATUS in agent.locked or held(agent.mortal_entity_id):
            continue
        rng = ctx.rng(f"spy.watch.{agent.id}.{ctx.epoch}")
        before = agent.status
        if agent.status is AgentStatus.ACTIVE and agent.exposure >= table.exposed_at:
            agent.status = AgentStatus.MISSING if rng.chance(table.missing_pct) else AgentStatus.EXPOSED
        elif agent.status is AgentStatus.MISSING and rng.chance(table.found_pct):
            agent.status = AgentStatus.ACTIVE
        if agent.status is before:
            continue
        changed += 1
        key = "spy.missing" if agent.status is AgentStatus.MISSING else "spy.exposed" if agent.status is AgentStatus.EXPOSED else "spy.found"
        roles = {IncidentRole.ACTOR: network.owner_entity_id, IncidentRole.TARGET: network.target_entity_id}
        if agent.mortal_entity_id is not None:
            roles[IncidentRole.SUBJECT] = agent.mortal_entity_id
        await record(ctx, key, roles=roles)
    return changed


async def feed_false(ctx: TickContext, network: SpyNetworkRow) -> int:
    exposed = await ctx.session.scalar(select(SpyAgentRow.id).where(SpyAgentRow.network_id == network.id, SpyAgentRow.status == AgentStatus.EXPOSED).limit(1))
    target = await living_entity(ctx.session, network.target_entity_id)
    if exposed is None or target is None or not ctx.rng(f"spy.feed.{network.id}.{ctx.epoch}").chance(ctx.rules.espionage.exposed_feed_pct):
        return 0
    truth = stat(target, "defense") or 0
    planted = await believe(
        ctx,
        network.owner_entity_id,
        target.id,
        "defense",
        truth // 2,
        source=BeliefSource.DECEPTION,
        confidence=ctx.rules.belief_state.deception_confidence,
        false=True,
    )
    return int(planted is not None)
