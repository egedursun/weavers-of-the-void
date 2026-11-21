from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.agentless_conditions import AgentlessConditionRow
from aerona.db.tables.body import SEVERITY_MAX, SEVERITY_MIN, ConditionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.agentless_conditions import ConditionCourse
from aerona.domain.enums.folk_knowledge import FolkDomain
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.agentless_conditions.arise import ConditionTally
from aerona.engine.body.conditions import CONDITION_KEY
from aerona.engine.body.state import refresh
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import shift_points
from aerona.engine.folk_knowledge.factor import folk_factor
from aerona.engine.gods.queries import community_of
from aerona.engine.interconnect.guards import blocked
from aerona.engine.primitives.knowledge import branch_level
from aerona.engine.primitives.stats import set_stats, stat_or
from aerona.engine.recording.record import FactInput, record


async def ease_chance(ctx: TickContext, bearer: EntityRow) -> float:
    table = ctx.rules.agentless_conditions
    community = await community_of(ctx.session, bearer)
    medicine = await branch_level(ctx.session, community.id, KnowledgeBranch.MEDICINE) if community is not None else 0
    return min(PERCENT, (table.ease_pct + table.medicine_ease_pct * medicine) * await folk_factor(ctx.session, ctx.rules, bearer, FolkDomain.BODY))


def named_of(row: ConditionRow, kind: AgentlessConditionRow | None) -> str:
    return kind.name if kind is not None else row.kind.value.replace("_", " ")


async def eased(
    ctx: TickContext, row: ConditionRow, bearer: EntityRow, kind: AgentlessConditionRow | None, tally: ConditionTally, *, by: int | None = None
) -> None:
    row.severity -= 1
    if row.severity < SEVERITY_MIN:
        row.severity, row.ended_epoch = SEVERITY_MIN, ctx.epoch
    roles = {IncidentRole.SUBJECT: bearer.id, IncidentRole.ACTOR: by}
    if row.ended_epoch is not None:
        await record(ctx, "body.condition_healed", roles=roles, facts={"condition": named_of(row, kind)}, place=bearer.location_id)
    else:
        facts: dict[str, FactInput] = {"condition": named_of(row, kind), "severity": row.severity}
        await record(ctx, "body.condition_eased", roles=roles, facts=facts, place=bearer.location_id)
    tally.eased += 1


async def worsened(ctx: TickContext, row: ConditionRow, bearer: EntityRow, kind: AgentlessConditionRow | None, tally: ConditionTally) -> None:
    row.severity = min(SEVERITY_MAX, row.severity + 1)
    facts: dict[str, FactInput] = {"condition": named_of(row, kind), "severity": row.severity}
    await record(ctx, "body.condition_worsened", roles={IncidentRole.SUBJECT: bearer.id}, facts=facts, place=bearer.location_id)
    tally.worsened += 1


async def burden(ctx: TickContext, row: ConditionRow, bearer: EntityRow) -> None:
    table = ctx.rules.agentless_conditions
    span = stat_or(bearer, "lifespan", 0)
    if span:
        set_stats(bearer, lifespan=max(stat_or(bearer, "age", 0), span - table.lifespan_cost * row.severity))
    await shift_points(ctx.session, bearer, -table.care_cost * row.severity)


async def run_course(ctx: TickContext, row: ConditionRow, tally: ConditionTally) -> None:
    bearer = await ctx.session.get(EntityRow, row.bearer_node_id)
    if bearer is None or held(bearer.id) or blocked(bearer.id, CONDITION_KEY):
        return
    kind = await ctx.session.get(AgentlessConditionRow, row.kind_id) if row.kind_id is not None else None
    course = kind.course if kind is not None else ConditionCourse.STABLE
    rng = ctx.rng(f"agentless.course.{row.id}.{ctx.epoch}")
    if rng.chance(await ease_chance(ctx, bearer)):
        await eased(ctx, row, bearer, kind, tally)
    elif (course is ConditionCourse.WORSENING and rng.chance(ctx.rules.agentless_conditions.worsen_pct)) or (
        course is ConditionCourse.EPISODIC and rng.chance(ctx.rules.agentless_conditions.worsen_pct)
    ):
        await worsened(ctx, row, bearer, kind, tally)
    if row.ended_epoch is None:
        await burden(ctx, row, bearer)
    await refresh(ctx.session, ctx.rules, bearer, ctx.epoch)


async def tend_courses(ctx: TickContext, tally: ConditionTally) -> None:
    query = select(ConditionRow).where(ConditionRow.ended_epoch.is_(None), ConditionRow.cause.is_not(None)).order_by(ConditionRow.id)
    for row in list(await ctx.session.scalars(query)):
        await run_course(ctx, row, tally)
