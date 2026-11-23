from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.arcana import CONDITIONAL_DURATIONS, SUSTAINED_DURATIONS
from aerona.core.total import total
from aerona.db.tables.arcana import RiteGrammarRow
from aerona.db.tables.body import InjuryRow
from aerona.db.tables.culture import CastingRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.renown import DeedRow
from aerona.db.write_guard import held
from aerona.domain.enums.arcana import RiteCondition, RiteEnd
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.primitives.queries import living_entity
from aerona.engine.recording.record import record


@dataclass
class EndingTally:
    ended: int = 0


@dataclass(frozen=True)
class Watch:
    ctx: TickContext
    casting: CastingRow
    grammar: RiteGrammarRow
    target: EntityRow | None


async def by_act(watch: Watch) -> bool:
    if watch.target is None or watch.grammar.condition_act is None:
        return False
    found = await watch.ctx.session.scalar(
        select(DeedRow.id)
        .where(DeedRow.doer_node_id == watch.target.id, DeedRow.act == watch.grammar.condition_act, DeedRow.epoch >= watch.casting.epoch)
        .limit(1)
    )
    return found is not None


async def by_time(watch: Watch) -> bool:
    return watch.grammar.condition_epoch is not None and watch.ctx.epoch >= watch.grammar.condition_epoch


async def by_word(watch: Watch) -> bool:
    if watch.casting.caster_entity_id is None or watch.casting.target_entity_id is None:
        return False
    grudge = await watch.ctx.session.scalar(
        select(MemoryRow.id)
        .where(
            MemoryRow.holder_node_id == watch.casting.caster_entity_id,
            MemoryRow.subject_node_id == watch.casting.target_entity_id,
            MemoryRow.magnitude < 0,
        )
        .limit(1)
    )
    return grudge is None


async def by_deed(watch: Watch) -> bool:
    if watch.target is None or watch.grammar.condition_act is None or watch.target.location_id is None:
        return False
    found = await watch.ctx.session.scalar(
        select(DeedRow.id)
        .where(
            DeedRow.act == watch.grammar.condition_act,
            DeedRow.epoch >= watch.casting.epoch,
            DeedRow.place_node_id == watch.target.location_id,
            DeedRow.doer_node_id != watch.target.id,
        )
        .limit(1)
    )
    return found is not None


MET: Mapping[RiteCondition, Callable[[Watch], Awaitable[bool]]] = total(
    RiteCondition,
    {RiteCondition.ACT: by_act, RiteCondition.TIME: by_time, RiteCondition.WORD: by_word, RiteCondition.DEED: by_deed},
)


async def struck(watch: Watch, caster: EntityRow) -> bool:
    wound = await watch.ctx.session.scalar(select(InjuryRow.id).where(InjuryRow.bearer_node_id == caster.id, InjuryRow.epoch >= watch.ctx.epoch - 1).limit(1))
    stream = f"rite.struck.{watch.casting.id}.{watch.ctx.epoch}"
    return wound is not None and watch.ctx.rng(stream).chance(watch.ctx.rules.arcana.sustained_struck_pct)


async def end_of(watch: Watch) -> RiteEnd | None:
    if watch.grammar.duration in SUSTAINED_DURATIONS:
        caster = await living_entity(watch.ctx.session, watch.casting.caster_entity_id) if watch.casting.caster_entity_id is not None else None
        if caster is None:
            return RiteEnd.CASTER_GONE
        return RiteEnd.CASTER_STRUCK if await struck(watch, caster) else None
    if watch.grammar.condition is not None and await MET[watch.grammar.condition](watch):
        return RiteEnd.CONDITION_MET
    return None


async def end_rites(ctx: TickContext, tally: EndingTally) -> None:
    lasting = sorted(SUSTAINED_DURATIONS | CONDITIONAL_DURATIONS)
    rows = await ctx.session.execute(
        select(CastingRow, RiteGrammarRow)
        .join(RiteGrammarRow, RiteGrammarRow.rite_entity_id == CastingRow.rite_entity_id)
        .where(CastingRow.succeeded.is_(True), CastingRow.ended_epoch.is_(None), RiteGrammarRow.duration.in_(lasting))
        .order_by(CastingRow.id)
    )
    for casting, grammar in list(rows):
        if held(casting.caster_entity_id, casting.target_entity_id):
            continue
        target = await ctx.session.get(EntityRow, casting.target_entity_id) if casting.target_entity_id is not None else None
        end = await end_of(Watch(ctx, casting, grammar, target))
        if end is None:
            continue
        casting.ended_epoch, casting.end = ctx.epoch, end
        tally.ended += 1
        await record(
            ctx,
            "rite.ended",
            roles={IncidentRole.SUBJECT: casting.rite_entity_id, IncidentRole.TARGET: casting.target_entity_id},
            facts={"end": end},
        )
    await ctx.session.flush()
