from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.law_depth import MOTIVE_LOYALTY
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.intrigue import SecretRow
from aerona.db.tables.law_depth import DefectionRow, RegistryRow, SpyCellRow
from aerona.db.tables.military import SpyAgentRow, SpyNetworkRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.law_depth import RecruitMotive, RegistryKind
from aerona.domain.enums.military import AgentStatus
from aerona.domain.enums.mind import TraitKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mortal import DeathCause
from aerona.domain.enums.polity import OfficeKind
from aerona.engine.context import TickContext
from aerona.engine.intrigue.favours import hook_on
from aerona.engine.intrigue.secrets import learn
from aerona.engine.military.spies_w52 import keep_motive, motive_by_heart
from aerona.engine.mind.book import traits_of, values_for
from aerona.engine.mortal.standing import add_infamy, add_renown
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.recording.record import record
from aerona.engine.records import death_path

VAIN = frozenset({TraitKind.PROUD, TraitKind.AMBITIOUS, TraitKind.VENGEFUL})
STATUS = "status"


@dataclass
class CellTally:
    cells: int = 0
    crossed: int = 0
    reprisals: int = 0


async def values_close(ctx: TickContext, first: int, second: int) -> bool:
    mine, theirs = await values_for(ctx.session, first), await values_for(ctx.session, second)
    shared = set(mine) & set(theirs)
    if not shared:
        return False
    gap = sum(abs(mine[axis] - theirs[axis]) for axis in shared) / len(shared)
    return gap <= ctx.rules.spy_depth.belief_fit


async def in_debt(ctx: TickContext, mortal_id: int) -> bool:
    owed = await ctx.session.scalar(
        select(RegistryRow.id).where(RegistryRow.counterparty_entity_id == mortal_id, RegistryRow.kind == RegistryKind.DEBT, RegistryRow.amount > 0).limit(1)
    )
    return owed is not None


async def grieved_by_lord(ctx: TickContext, mortal_id: int) -> bool:
    mortal = await ctx.session.get(EntityRow, mortal_id)
    town = mortal.location_id if mortal is not None else None
    realm = await ctx.session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == town).limit(1)) if town else None
    if realm is None:
        return False
    lord = await ctx.session.scalar(
        select(OfficeRow.holder_entity_id)
        .where(OfficeRow.polity_entity_id == realm, OfficeRow.kind == OfficeKind.RULER, OfficeRow.holder_entity_id.is_not(None))
        .limit(1)
    )
    if lord is None or lord == mortal_id:
        return False
    grudge = await ctx.session.scalar(
        select(MemoryRow.id).where(MemoryRow.holder_node_id == mortal_id, MemoryRow.subject_node_id == lord, MemoryRow.magnitude < 0).limit(1)
    )
    return grudge is not None


async def motive_for(ctx: TickContext, network: SpyNetworkRow, mortal: EntityRow) -> RecruitMotive:
    recruiter = network.spymaster_entity_id or network.owner_entity_id
    if await hook_on(ctx, recruiter, mortal.id) is not None:
        return RecruitMotive.COMPROMISE
    heart = await motive_by_heart(ctx, network, mortal)
    if heart is not None:
        return heart
    if await values_close(ctx, network.owner_entity_id, mortal.id):
        return RecruitMotive.IDEOLOGY
    traits = await traits_of(ctx.session, mortal.id)
    if TraitKind.GREEDY in traits or await in_debt(ctx, mortal.id):
        return RecruitMotive.MONEY
    if traits & VAIN or await grieved_by_lord(ctx, mortal.id):
        return RecruitMotive.EGO
    return RecruitMotive.MONEY


def loyalty_for(ctx: TickContext, motive: RecruitMotive) -> int:
    return int(getattr(ctx.rules.spy_depth, MOTIVE_LOYALTY[motive]))


async def motivate(ctx: TickContext, network: SpyNetworkRow, agent: SpyAgentRow, mortal: EntityRow) -> None:
    agent.motive = await motive_for(ctx, network, mortal)
    agent.loyalty = loyalty_for(ctx, agent.motive)


async def cells_of(ctx: TickContext, network_id: int) -> list[SpyCellRow]:
    return list(await ctx.session.scalars(select(SpyCellRow).where(SpyCellRow.network_id == network_id).order_by(SpyCellRow.id)))


async def safe_house(ctx: TickContext, network: SpyNetworkRow) -> int | None:
    towns = select(PolityMemberRow.member_entity_id).where(PolityMemberRow.polity_entity_id == network.target_entity_id)
    rows = await ctx.session.scalars(
        select(StructureProfileRow.structure_entity_id)
        .where((StructureProfileRow.host_entity_id == network.target_entity_id) | StructureProfileRow.host_entity_id.in_(towns))
        .order_by(StructureProfileRow.structure_entity_id)
        .limit(1)
    )
    return rows.first()


async def organise(ctx: TickContext, network: SpyNetworkRow, tally: CellTally) -> None:
    size = ctx.rules.spy_depth.cell_size
    agents = [
        row
        for row in await ctx.session.scalars(
            select(SpyAgentRow).where(SpyAgentRow.network_id == network.id, SpyAgentRow.status == AgentStatus.ACTIVE).order_by(SpyAgentRow.id)
        )
        if "cell_id" not in row.locked
    ]
    if len(agents) <= size:
        return
    cells = {cell.id: cell for cell in await cells_of(ctx, network.id)}
    filled = {cell_id: sum(1 for row in agents if row.cell_id == cell_id) for cell_id in cells}
    for agent in agents:
        if agent.cell_id in cells:
            continue
        open_cell = next((cell_id for cell_id, count in filled.items() if count < size), None)
        if open_cell is None:
            cell = SpyCellRow(
                network_id=network.id, handler_entity_id=agent.mortal_entity_id, safe_house_entity_id=await safe_house(ctx, network), dead_drops=1, locked=[]
            )
            ctx.session.add(cell)
            await ctx.session.flush()
            cells[cell.id], filled[cell.id] = cell, 0
            open_cell = cell.id
            tally.cells += 1
        agent.cell_id = open_cell
        filled[open_cell] += 1
    await ctx.session.flush()


async def topology_pct(ctx: TickContext, network: SpyNetworkRow) -> int:
    return PERCENT if await cells_of(ctx, network.id) else PERCENT + ctx.rules.spy_depth.flat_speed_pct


async def compromise(ctx: TickContext, network: SpyNetworkRow, caught: SpyAgentRow) -> int:
    table = ctx.rules.spy_depth
    cell = await ctx.session.get(SpyCellRow, caught.cell_id) if caught.cell_id is not None else None
    statement = select(SpyAgentRow).where(SpyAgentRow.network_id == network.id, SpyAgentRow.status == AgentStatus.ACTIVE, SpyAgentRow.id != caught.id)
    if cell is not None:
        statement = statement.where(SpyAgentRow.cell_id == cell.id)
        amount = max(0, table.cell_exposure - (table.safe_house_relief if cell.safe_house_entity_id is not None else 0))
    else:
        amount = table.flat_exposure
    touched = 0
    for agent in await ctx.session.scalars(statement.order_by(SpyAgentRow.id)):
        if "exposure" in agent.locked or held(agent.mortal_entity_id):
            continue
        agent.exposure = clamp_int(agent.exposure + amount, 0, PERCENT)
        touched += 1
    return touched


async def realm_secrets(ctx: TickContext, realm_id: int) -> list[SecretRow]:
    members = select(PolityMemberRow.member_entity_id).where(PolityMemberRow.polity_entity_id == realm_id)
    return list(
        await ctx.session.scalars(
            select(SecretRow)
            .where((SecretRow.holder_node_id == realm_id) | SecretRow.holder_node_id.in_(members))
            .order_by(SecretRow.severity.desc(), SecretRow.id)
        )
    )


async def shelters(ctx: TickContext, side_id: int) -> bool:
    keeper = await ctx.session.scalar(
        select(OfficeRow.holder_entity_id)
        .where(OfficeRow.polity_entity_id == side_id, OfficeRow.kind == OfficeKind.SPYMASTER, OfficeRow.holder_entity_id.is_not(None))
        .limit(1)
    )
    return keeper is not None


async def defect(ctx: TickContext, defector: EntityRow, from_id: int | None, to_id: int | None, *, protected: bool | None = None) -> DefectionRow | None:
    table = ctx.rules.defections
    if held(defector.id) or to_id is None:
        return None
    if protected is None:
        protected = await shelters(ctx, to_id)
    carried = 0
    for secret in (await realm_secrets(ctx, from_id))[: table.secrets] if from_id is not None else []:
        if await learn(ctx, secret, to_id):
            carried += 1
    await add_infamy(ctx.session, defector.id, table.traitor_infamy, ctx.epoch, rules=ctx.rules)
    await add_renown(ctx.session, defector.id, table.hero_renown, ctx.epoch, rules=ctx.rules)
    row = DefectionRow(
        defector_entity_id=defector.id, from_entity_id=from_id, to_entity_id=to_id, secrets=carried, protected=protected, epoch=ctx.epoch, locked=[]
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await record(
        ctx,
        "espionage.defected",
        roles={
            IncidentRole.SUBJECT: defector.id,
            **({IncidentRole.OPPONENT: from_id} if from_id is not None else {}),
            **({IncidentRole.RECEIVER: to_id} if to_id is not None else {}),
        },
        facts={"secrets": carried},
    )
    return row


async def cross_sides(ctx: TickContext, network: SpyNetworkRow, tally: CellTally) -> None:
    table = ctx.rules.spy_depth
    for agent in list(
        await ctx.session.scalars(
            select(SpyAgentRow).where(SpyAgentRow.network_id == network.id, SpyAgentRow.status == AgentStatus.ACTIVE).order_by(SpyAgentRow.id)
        )
    ):
        mortal = await living_entity(ctx.session, agent.mortal_entity_id) if agent.mortal_entity_id is not None else None
        if mortal is None or held(mortal.id) or STATUS in agent.locked:
            continue
        risk = await keep_motive(ctx, network, agent)
        if not ctx.rng(f"espionage.cross.{agent.id}.{ctx.epoch}").chance(round_half_up(table.double_cross_pct * risk * (PERCENT - agent.loyalty) / PERCENT)):
            continue
        agent.status, agent.ended_epoch = AgentStatus.TURNED, ctx.epoch
        if "exposure" not in network.locked:
            network.exposure = clamp_int(network.exposure + table.cell_exposure, 0, PERCENT)
        await defect(ctx, mortal, network.owner_entity_id, network.target_entity_id)
        tally.crossed += 1


async def reprisals(ctx: TickContext, tally: CellTally) -> None:
    rows = await ctx.session.scalars(select(DefectionRow).where(DefectionRow.protected.is_(False), DefectionRow.epoch < ctx.epoch).order_by(DefectionRow.id))
    for row in list(rows):
        defector = await living_entity(ctx.session, row.defector_entity_id)
        if defector is None or held(defector.id, row.from_entity_id):
            continue
        if ctx.rng(f"espionage.reprisal.{row.id}.{ctx.epoch}").chance(ctx.rules.defections.reprisal_pct):
            await death_path(ctx, defector, "killed by the realm they betrayed", row.from_entity_id, "reprisal", forced=True, manner=DeathCause.MURDER)
            tally.reprisals += 1


async def tend_cells(ctx: TickContext, tally: CellTally) -> None:
    for network in list(await ctx.session.scalars(select(SpyNetworkRow).order_by(SpyNetworkRow.id))):
        if held(network.owner_entity_id, network.target_entity_id):
            continue
        await organise(ctx, network, tally)
        await cross_sides(ctx, network, tally)
    await reprisals(ctx, tally)
