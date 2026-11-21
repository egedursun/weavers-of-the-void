from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interpretation import InterpretationRow
from aerona.db.tables.mind import SkillRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.interpretation import InterpretationFault, InterpretedEvent
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.lore.language import intelligibility, tongues_of
from aerona.engine.mortal.standing import shift_standing
from aerona.engine.primitives.folk import homes_for, present_among
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.recording.record import record

IF = InterpretationFault
HONEST_FAULTS = (IF.LOST_MEANING, IF.WRONG_TERM, IF.SOFTENED, IF.HARDENED, IF.INVENTED)
PARAM_FACTOR = total(
    InterpretationFault,
    {IF.NONE: 1.0, IF.LOST_MEANING: 0.5, IF.WRONG_TERM: 0.5, IF.SOFTENED: 0.5, IF.HARDENED: 2.0, IF.SLANTED: 0.5, IF.INVENTED: 0.5},
)
SKILL_GAIN = 1
SKILL_MAX = 100


@dataclass(frozen=True)
class Reader:
    node_id: int
    skill: int


async def reader_for(ctx: TickContext, first: int, second: int, tongues: set[int]) -> Reader | None:
    mortals = select(EntityRow.id).where(
        EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, await present_among(ctx.session, (first, second))
    )
    subject = SkillRow.subject_node_id.is_(None) | SkillRow.subject_node_id.in_(sorted(tongues))
    query = (
        select(SkillRow)
        .where(SkillRow.skill == SkillKind.LANGUAGES, SkillRow.level >= ctx.rules.interpreters.interpreter_skill, SkillRow.holder_node_id.in_(mortals), subject)
        .order_by(SkillRow.level.desc(), SkillRow.holder_node_id)
    )
    found = await ctx.session.scalar(query.limit(1))
    return Reader(found.holder_node_id, found.level) if found is not None else None


async def side_of(ctx: TickContext, reader: int, first: int, second: int) -> int | None:
    holder = await ctx.session.get(EntityRow, reader)
    home = holder.location_id if holder is not None else None
    ours, theirs = await homes_for(ctx.session, [first]), await homes_for(ctx.session, [second])
    if home in ours and home not in theirs:
        return first
    if home in theirs and home not in ours:
        return second
    return None


async def standing_reading(ctx: TickContext, event: InterpretedEvent, first: int, second: int, event_node: int | None) -> InterpretationRow | None:
    node = InterpretationRow.event_node_id.is_(None) if event_node is None else InterpretationRow.event_node_id == event_node
    same = (InterpretationRow.event == event, InterpretationRow.first_party_id == first, InterpretationRow.second_party_id == second, node)
    return await ctx.session.scalar(select(InterpretationRow).where(*same).order_by(InterpretationRow.id.desc()).limit(1))


def settled(ctx: TickContext, row: InterpretationRow) -> bool:
    hidden = row.fault is not IF.NONE and not row.found
    return row.epoch == ctx.epoch or hidden or "fault" in (row.locked or [])


async def interpret(ctx: TickContext, event: InterpretedEvent, first: int, second: int, *, event_node: int | None = None) -> InterpretationRow | None:
    ours, theirs = await tongues_of(ctx.session, first), await tongues_of(ctx.session, second)
    if first == second or not ours or not theirs or ours & theirs:
        return None
    pairs = [(await intelligibility(ctx.session, ctx.rules, one, other, ctx.epoch), one, other) for one in sorted(ours) for other in sorted(theirs)]
    best, mine, yours = max(pairs)
    if best >= PERCENT:
        return None
    existing = await standing_reading(ctx, event, first, second, event_node)
    if (existing is not None and settled(ctx, existing)) or held(first) or held(second):
        return existing
    reader = await reader_for(ctx, first, second, ours | theirs)
    if reader is None:
        return existing
    table = ctx.rules.interpreters
    distance = PERCENT - best
    fidelity = clamp_int(reader.skill * (PERCENT - distance // 2) // PERCENT, 0, PERCENT)
    chance = min(PERCENT, (table.fault_base_pct + table.fault_per_distance_pct * distance / PERCENT) * 2 * (PERCENT - fidelity) / PERCENT)
    loyal_to = await side_of(ctx, reader.node_id, first, second)
    rng = ctx.rng(f"interpret.{event.value}.{first}.{second}.{event_node or 0}.{ctx.epoch}")
    fault = IF.NONE
    if loyal_to is not None and fidelity >= table.slant_loyalty_threshold and rng.chance(chance * 2):
        fault = IF.SLANTED
    elif rng.chance(chance):
        fault = rng.pick(list(HONEST_FAULTS))
    row = existing or InterpretationRow(event=event, event_node_id=event_node, first_party_id=first, second_party_id=second, locked=[])
    row.interpreter_node_id, row.first_language_id, row.second_language_id = reader.node_id, mine, yours
    row.fidelity, row.fault, row.found, row.epoch = fidelity, fault, False, ctx.epoch
    row.favoured_party_id = loyal_to if fault is IF.SLANTED else None
    if existing is None:
        ctx.session.add(row)
        await ctx.session.flush()
    await told(ctx, row)
    return row


def reach_of(ctx: TickContext, row: InterpretationRow | None) -> float:
    if row is None or row.fault is IF.NONE:
        return 1.0
    floor = ctx.rules.interpreters.barrier_floor_pct / PERCENT
    return floor + (1 - floor) * row.fidelity / PERCENT


def slant_of(row: InterpretationRow | None, first: int, second: int) -> int:
    if row is None or row.fault is not IF.SLANTED:
        return 0
    return 1 if row.favoured_party_id == first else -1 if row.favoured_party_id == second else 0


async def told(ctx: TickContext, row: InterpretationRow) -> None:
    roles = {IncidentRole.ACTOR: row.interpreter_node_id, IncidentRole.SUBJECT: row.first_party_id, IncidentRole.TARGET: row.second_party_id}
    if row.fault is IF.SLANTED:
        await record(
            ctx, "tongue.slanted", roles={**roles, IncidentRole.BENEFICIARY: row.favoured_party_id}, facts={"event": row.event, "fidelity": row.fidelity}
        )
    elif row.fault is not IF.NONE:
        await record(ctx, "tongue.mistranslated", roles=roles, facts={"event": row.event, "fault": row.fault, "fidelity": row.fidelity})
    elif row.interpreter_node_id is not None and not held(row.interpreter_node_id):
        await reward(ctx, row.interpreter_node_id)


async def reward(ctx: TickContext, reader: int) -> None:
    skill = await ctx.session.scalar(select(SkillRow).where(SkillRow.holder_node_id == reader, SkillRow.skill == SkillKind.LANGUAGES).limit(1))
    if skill is not None:
        skill.level = min(SKILL_MAX, skill.level + SKILL_GAIN)
    holder = await ctx.session.get(EntityRow, reader)
    if holder is not None:
        await shift_standing(ctx.session, holder, "renown", SKILL_GAIN, ctx.epoch)
