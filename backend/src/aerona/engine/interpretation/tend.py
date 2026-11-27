from dataclasses import dataclass

from sqlalchemy import select

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interpretation import InterpretationRow
from aerona.db.tables.polity import TreatyClauseRow
from aerona.db.write_guard import held
from aerona.domain.enums.interpretation import InterpretationFault
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.interpretation.work import PARAM_FACTOR
from aerona.engine.mortal.standing import shift_standing
from aerona.engine.recording.record import record
from aerona.engine.services.community_relations import change_relation


@dataclass
class InterpretationTally:
    found: int = 0
    mended: int = 0


MARKS = frozenset({"misread", "interpretation"})


def restored(value: int | str | bool, undo: float) -> int | str | bool:
    return round(value * undo) if isinstance(value, int) and not isinstance(value, bool) else value


async def mend_clauses(ctx: TickContext, row: InterpretationRow, tally: InterpretationTally) -> None:
    factor = PARAM_FACTOR[row.fault]
    sides = [row.first_party_id, row.second_party_id]
    query = select(TreatyClauseRow).where(TreatyClauseRow.obligor_node_id.in_(sides), TreatyClauseRow.beneficiary_node_id.in_(sides))
    for clause in list(await ctx.session.scalars(query.order_by(TreatyClauseRow.id))):
        params = dict(clause.params or {})
        if params.get("interpretation") != row.id or not params.get("misread"):
            continue
        undo = factor if row.fault is InterpretationFault.SLANTED and row.favoured_party_id == clause.beneficiary_node_id else 1 / factor
        clause.params = {key: restored(value, undo) for key, value in params.items() if key not in MARKS}
        tally.mended += 1


def wronged(row: InterpretationRow) -> tuple[int, int]:
    if row.fault is InterpretationFault.SLANTED and row.favoured_party_id == row.first_party_id:
        return row.second_party_id, row.first_party_id
    return row.first_party_id, row.second_party_id


async def come_to_light(ctx: TickContext, row: InterpretationRow, tally: InterpretationTally) -> None:
    row.found = True
    tally.found += 1
    victim, other = wronged(row)
    await change_relation(
        ctx,
        victim,
        other,
        -ctx.rules.interpreters.found_grievance,
        MemoryKind.BETRAYED_ME,
        note="words carried wrongly between us",
        reverse_note="words carried wrongly between us",
    )
    if row.fault is InterpretationFault.SLANTED and row.interpreter_node_id is not None:
        reader = await ctx.session.get(EntityRow, row.interpreter_node_id)
        if reader is not None and not held(reader.id):
            await shift_standing(ctx.session, reader, "renown", -ctx.rules.interpreters.found_grievance, ctx.epoch)
    await mend_clauses(ctx, row, tally)
    await record(
        ctx,
        "tongue.fault_found",
        roles={IncidentRole.ACTOR: row.interpreter_node_id, IncidentRole.SUBJECT: row.first_party_id, IncidentRole.TARGET: row.second_party_id},
        facts={"event": row.event, "fault": row.fault},
    )


async def tend_interpretations(ctx: TickContext) -> InterpretationTally:
    tally = InterpretationTally()
    query = (
        select(InterpretationRow).where(InterpretationRow.found.is_(False), InterpretationRow.fault != InterpretationFault.NONE).order_by(InterpretationRow.id)
    )
    for row in list(await ctx.session.scalars(query)):
        if held(row.first_party_id) or held(row.second_party_id) or "found" in (row.locked or []):
            continue
        if ctx.rng(f"interpret.found.{row.id}.{ctx.epoch}").chance(ctx.rules.interpreters.fault_found_pct):
            await come_to_light(ctx, row, tally)
    return tally
