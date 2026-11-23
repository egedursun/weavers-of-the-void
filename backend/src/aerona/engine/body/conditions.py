from sqlalchemy import select

from aerona.catalog.conditions import VISIBLE_CONDITIONS
from aerona.catalog.incident_kinds.body_lines import CONDITION_PHRASES, END_PHRASES, ILLNESSES
from aerona.core.total import partial
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.body import SEVERITY_MAX, SEVERITY_MIN, ConditionRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.body import ConditionKind, HarmCause
from aerona.domain.enums.mind import ThoughtKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import FactUnit, StepAction
from aerona.engine.body.book import Bearer
from aerona.engine.body.state import refresh
from aerona.engine.context import TickContext
from aerona.engine.interconnect.guards import blocked
from aerona.engine.lifecycle.aging import is_notable
from aerona.engine.mind.book import mind_of
from aerona.engine.mind.thoughts import think
from aerona.engine.mind.traits import condition_trait
from aerona.engine.primitives.naming import seed_of
from aerona.engine.recording.record import StepDraft, record

GAINED_KEYS = partial(
    ConditionKind,
    {
        ConditionKind.CHRONIC_ILLNESS: "condition.gained.chronic_illness",
        ConditionKind.PARANOIA: "condition.gained.paranoia",
        ConditionKind.VISIONS: "condition.gained.visions",
        ConditionKind.RAGE: "condition.gained.rage",
        ConditionKind.MELANCHOLY: "condition.gained.melancholy",
        ConditionKind.ADDICTION: "condition.gained.addiction",
        ConditionKind.AGE_BLINDNESS: "condition.gained.age_blindness",
        ConditionKind.AGE_DEAFNESS: "condition.gained.age_deafness",
        ConditionKind.WITHERED_LIMB: "condition.gained.withered_limb",
        ConditionKind.ENDLESS_HUNGER: "condition.gained.endless_hunger",
        ConditionKind.POSSESSION: "condition.gained.possession",
        ConditionKind.VOID_TAINT: "condition.gained.void_taint",
        ConditionKind.CHOSEN_MARK: "condition.gained.chosen_mark",
        ConditionKind.DIVINE_BRAND: "condition.gained.divine_brand",
        ConditionKind.NIGHTMARES: "condition.gained.nightmares",
        ConditionKind.COMATOSE: "condition.gained.comatose",
        ConditionKind.COGNITIVE_DECLINE: "condition.gained.cognitive_decline",
        ConditionKind.MALNUTRITION: "condition.gained.malnutrition",
        ConditionKind.PARALYSIS: "condition.gained.paralysis",
        ConditionKind.INFERTILITY: "condition.gained.infertility",
        ConditionKind.CHRONIC_PAIN: "condition.gained.chronic_pain",
    },
    without=tuple(kind for kind in ConditionKind if kind not in CONDITION_PHRASES),
)
ENDED_KEYS = partial(
    ConditionKind,
    {
        ConditionKind.CHRONIC_ILLNESS: "condition.ended.chronic_illness",
        ConditionKind.PARANOIA: "condition.ended.paranoia",
        ConditionKind.VISIONS: "condition.ended.visions",
        ConditionKind.RAGE: "condition.ended.rage",
        ConditionKind.MELANCHOLY: "condition.ended.melancholy",
        ConditionKind.ADDICTION: "condition.ended.addiction",
        ConditionKind.ENDLESS_HUNGER: "condition.ended.endless_hunger",
        ConditionKind.POSSESSION: "condition.ended.possession",
        ConditionKind.NIGHTMARES: "condition.ended.nightmares",
        ConditionKind.COMATOSE: "condition.ended.comatose",
        ConditionKind.COGNITIVE_DECLINE: "condition.ended.cognitive_decline",
        ConditionKind.MALNUTRITION: "condition.ended.malnutrition",
    },
    without=tuple(kind for kind in ConditionKind if kind not in END_PHRASES),
)


async def condition_of(ctx: TickContext, bearer_id: int, kind: ConditionKind) -> ConditionRow | None:
    statement = select(ConditionRow).where(ConditionRow.bearer_node_id == bearer_id, ConditionRow.kind == kind, ConditionRow.ended_epoch.is_(None))
    return await ctx.session.scalar(statement.limit(1))


async def _announce(ctx: TickContext, bearer: Bearer, row: ConditionRow, key: str, action: StepAction) -> None:
    if not isinstance(bearer, EntityRow):
        return
    if not is_notable(ctx.rules, bearer, await EntityRepository(ctx.session).flags(bearer.id)):
        return
    steps = (
        (
            StepDraft(
                action,
                actor=row.source_node_id if action is StepAction.FALL_ILL else None,
                target=bearer.id,
                amount=float(row.severity),
                unit=FactUnit.SEVERITY,
                record_table=ConditionRow.__tablename__,
                record_key=str(row.id),
            ),
        )
        if row.kind in ILLNESSES
        else ()
    )
    await record(ctx, key, roles={IncidentRole.PATIENT: bearer.id}, facts={"condition": row.kind, "severity": row.severity}, steps=steps)


CONDITION_KEY = "conditions"


async def gain_condition(
    ctx: TickContext,
    bearer: Bearer,
    kind: ConditionKind,
    source: HarmCause,
    *,
    chance: float | None = None,
    severity: int = SEVERITY_MIN,
    part: str | None = None,
    source_node_id: int | None = None,
    announce: bool = True,
) -> ConditionRow | None:
    if blocked(bearer.id, CONDITION_KEY):
        return None
    if chance is not None and not ctx.rng(seed_of("condition", bearer.id, kind.value)).chance(chance):
        return None
    existing = await condition_of(ctx, bearer.id, kind)
    if existing is not None:
        existing.severity = min(SEVERITY_MAX, max(existing.severity, severity))
        await refresh(ctx.session, ctx.rules, bearer, ctx.epoch)
        return existing
    row = ConditionRow(
        bearer_node_id=bearer.id,
        kind=kind,
        severity=max(SEVERITY_MIN, min(SEVERITY_MAX, severity)),
        part=part,
        source=source,
        source_node_id=source_node_id,
        since_epoch=ctx.epoch,
        visible=kind in VISIBLE_CONDITIONS,
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await refresh(ctx.session, ctx.rules, bearer, ctx.epoch)
    if await mind_of(ctx.session, bearer.id) is not None:
        await condition_trait(ctx, bearer.id, kind)
    if kind in ILLNESSES:
        await think(ctx.session, ctx.rules, bearer.id, ThoughtKind.FELL_ILL, ctx.epoch, subject_id=source_node_id)
    if announce and kind in GAINED_KEYS:
        await _announce(ctx, bearer, row, GAINED_KEYS[kind], StepAction.FALL_ILL)
    return row


async def end_condition(ctx: TickContext, bearer: Bearer, kind: ConditionKind, *, announce: bool = True) -> bool:
    row = await condition_of(ctx, bearer.id, kind)
    if row is None:
        return False
    row.ended_epoch = ctx.epoch
    await refresh(ctx.session, ctx.rules, bearer, ctx.epoch)
    if announce and kind in ENDED_KEYS:
        await _announce(ctx, bearer, row, ENDED_KEYS[kind], StepAction.RECOVER)
    return True
