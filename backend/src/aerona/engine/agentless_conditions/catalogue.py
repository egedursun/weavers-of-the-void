from sqlalchemy import select

from aerona.core.grammar import spoken
from aerona.core.total import total
from aerona.db.tables.agentless_conditions import AgentlessConditionRow
from aerona.db.tables.body import ConditionRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.write_guard import held
from aerona.domain.enums.agentless_conditions import ConditionCause, ConditionCourse
from aerona.domain.enums.body import ConditionKind, HarmCause
from aerona.domain.enums.body_systems import BodySystem
from aerona.engine.context import TickContext

C = ConditionCause
SEED_FIXUP = "agentless_conditions.seed"
COURSES = total(
    ConditionCause,
    {
        C.AGE: ConditionCourse.WORSENING,
        C.DIET: ConditionCourse.STABLE,
        C.EXPOSURE: ConditionCourse.WORSENING,
        C.HEREDITY: ConditionCourse.STABLE,
        C.INJURY_AFTERMATH: ConditionCourse.EPISODIC,
        C.STRAIN: ConditionCourse.EPISODIC,
        C.UNKNOWN: ConditionCourse.STABLE,
    },
)
ONSETS = total(ConditionCause, {C.AGE: 60, C.DIET: 0, C.EXPOSURE: 0, C.HEREDITY: 0, C.INJURY_AFTERMATH: 0, C.STRAIN: 0, C.UNKNOWN: 0})
SOURCES = total(
    ConditionCause,
    {
        C.AGE: HarmCause.AGE,
        C.DIET: HarmCause.BODY,
        C.EXPOSURE: HarmCause.EXPOSURE,
        C.HEREDITY: HarmCause.BODY,
        C.INJURY_AFTERMATH: HarmCause.BODY,
        C.STRAIN: HarmCause.BODY,
        C.UNKNOWN: HarmCause.BODY,
    },
)
SEED_WEIGHT = 50
SYSTEMS = tuple(system for system in BodySystem if system is not BodySystem.NONE)


def manifests_as(cause: ConditionCause, system: BodySystem) -> ConditionKind:
    return ConditionKind.COGNITIVE_DECLINE if cause is C.AGE and system is BodySystem.NERVES else ConditionKind.CHRONIC_ILLNESS


def seeded_kind(world_id: int, cause: ConditionCause, system: BodySystem) -> AgentlessConditionRow:
    return AgentlessConditionRow(
        world_id=world_id,
        name=f"{spoken(cause)} condition of the {spoken(system)}".capitalize(),
        cause=cause,
        system=system,
        manifests=manifests_as(cause, system),
        course=COURSES[cause],
        onset_pct=ONSETS[cause],
        severity=1,
        weight=SEED_WEIGHT,
        locked=[],
    )


async def seed_worlds(ctx: TickContext) -> int:
    kept = set(await ctx.session.scalars(select(AgentlessConditionRow.world_id).distinct()))
    made = 0
    for world in list(await ctx.session.scalars(select(WorldRow.id).order_by(WorldRow.id))):
        if world in kept or held(world):
            continue
        for cause in ConditionCause:
            for system in SYSTEMS:
                ctx.session.add(seeded_kind(world, cause, system))
                made += 1
    return made


async def legacy_causes(ctx: TickContext) -> None:
    if await ctx.session.get(AppliedFixupRow, SEED_FIXUP) is not None:
        return
    unknown = (ConditionRow.kind == ConditionKind.CHRONIC_ILLNESS, ConditionRow.cause.is_(None), ConditionRow.source_node_id.is_(None))
    marked = 0
    for row in list(await ctx.session.scalars(select(ConditionRow).where(*unknown).order_by(ConditionRow.id))):
        if not held(row.bearer_node_id):
            row.cause = C.UNKNOWN
            marked += 1
    ctx.session.add(AppliedFixupRow(key=SEED_FIXUP, result={"unknown": marked}))


async def seed_catalogue(ctx: TickContext) -> int:
    made = await seed_worlds(ctx)
    await legacy_causes(ctx)
    await ctx.session.flush()
    return made
