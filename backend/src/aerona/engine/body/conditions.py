from sqlalchemy import select

from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.body import SEVERITY_MAX, SEVERITY_MIN, ConditionRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.body import ConditionKind, HarmCause
from aerona.domain.enums.mind import ThoughtKind
from aerona.engine.body.book import Bearer
from aerona.engine.body.state import refresh
from aerona.engine.context import TickContext
from aerona.engine.interconnect.guards import blocked
from aerona.engine.lifecycle.aging import is_notable
from aerona.engine.mind.book import mind_of
from aerona.engine.mind.thoughts import think
from aerona.engine.mind.traits import condition_trait
from aerona.engine.notes import note
from aerona.engine.primitives.naming import seed_of

VISIBLE_CONDITIONS = frozenset(
    {
        ConditionKind.WITHERED_LIMB,
        ConditionKind.VOID_TAINT,
        ConditionKind.CHOSEN_MARK,
        ConditionKind.DIVINE_BRAND,
        ConditionKind.POSSESSION,
        ConditionKind.COMATOSE,
        ConditionKind.COGNITIVE_DECLINE,
    }
)

CONDITION_PHRASES: dict[ConditionKind, str] = {
    ConditionKind.CHRONIC_ILLNESS: "fell into a lingering illness",
    ConditionKind.PARANOIA: "grew paranoid",
    ConditionKind.VISIONS: "began to see visions",
    ConditionKind.RAGE: "was seized by fits of rage",
    ConditionKind.MELANCHOLY: "sank into melancholy",
    ConditionKind.ADDICTION: "fell into addiction",
    ConditionKind.AGE_BLINDNESS: "went blind with age",
    ConditionKind.AGE_DEAFNESS: "went deaf with age",
    ConditionKind.WITHERED_LIMB: "was left with a withered limb",
    ConditionKind.ENDLESS_HUNGER: "was cursed with an endless hunger",
    ConditionKind.POSSESSION: "was possessed by a spirit",
    ConditionKind.VOID_TAINT: "was tainted by the void",
    ConditionKind.CHOSEN_MARK: "bore the mark of the chosen",
    ConditionKind.DIVINE_BRAND: "bore a god's brand",
    ConditionKind.NIGHTMARES: "began to dream the same nightmare night after night",
    ConditionKind.COMATOSE: "fell into a sleep no one could wake them from",
    ConditionKind.COGNITIVE_DECLINE: "began to lose their memory and their reckoning",
    ConditionKind.MALNUTRITION: "began to waste from a poor diet",
}

END_PHRASES: dict[ConditionKind, str] = {
    ConditionKind.CHRONIC_ILLNESS: "recovered from a lingering illness",
    ConditionKind.PARANOIA: "was freed of paranoia",
    ConditionKind.VISIONS: "no longer sees visions",
    ConditionKind.RAGE: "mastered their rage",
    ConditionKind.MELANCHOLY: "came out of melancholy",
    ConditionKind.ADDICTION: "broke free of addiction",
    ConditionKind.POSSESSION: "was freed of the spirit that possessed them",
    ConditionKind.ENDLESS_HUNGER: "was freed of the endless hunger",
    ConditionKind.NIGHTMARES: "slept free of nightmares at last",
    ConditionKind.COMATOSE: "woke at last",
    ConditionKind.COGNITIVE_DECLINE: "came back to their wits",
    ConditionKind.MALNUTRITION: "was nourished back to strength",
}


ILLNESSES = frozenset({ConditionKind.CHRONIC_ILLNESS, ConditionKind.ENDLESS_HUNGER, ConditionKind.MALNUTRITION})


async def condition_of(ctx: TickContext, bearer_id: int, kind: ConditionKind) -> ConditionRow | None:
    statement = select(ConditionRow).where(ConditionRow.bearer_node_id == bearer_id, ConditionRow.kind == kind, ConditionRow.ended_epoch.is_(None))
    return await ctx.session.scalar(statement.limit(1))


async def _announce(ctx: TickContext, bearer: Bearer, phrase: str, kind: ConditionKind, verb: str) -> None:
    if not isinstance(bearer, EntityRow):
        return
    if not is_notable(ctx.rules, bearer, await EntityRepository(ctx.session).flags(bearer.id)):
        return
    await note(ctx, f"{bearer.name} {phrase}.", key=f"condition.{verb}.{kind.value}", ids=[bearer.id])


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
    if announce:
        await _announce(ctx, bearer, CONDITION_PHRASES[kind], kind, "gained")
    return row


async def end_condition(ctx: TickContext, bearer: Bearer, kind: ConditionKind, *, announce: bool = True) -> bool:
    row = await condition_of(ctx, bearer.id, kind)
    if row is None:
        return False
    row.ended_epoch = ctx.epoch
    await refresh(ctx.session, ctx.rules, bearer, ctx.epoch)
    if announce and kind in END_PHRASES:
        await _announce(ctx, bearer, END_PHRASES[kind], kind, "ended")
    return True
