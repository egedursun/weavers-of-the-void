from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.grammar import an, fact_word, spoken
from aerona.db.tables.tellings import IncidentNameRow, RumourDistortionRow
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import InstrumentKind, RumourDistortion, StepLocus
from aerona.engine.lore.tellings import node_names, telling_of, told_text
from aerona.engine.recording.accounts import Account, AccountChange, AccountFact, AccountStep, HistoryEntry, account_of, history_of
from aerona.prompts import PromptId, render
from aerona.prompts.contexts.accounts import AccountFactLine, AccountRole, AccountStepLine, EventAccountContext, EventRecordsContext, RecordLine

SEEN = {"saw": "saw it", "heard": "heard of it nearby", "took_part": "took part", "was_told": "was told of it"}


def number_text(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(round(value, 2))


def fact_text(fact: AccountFact) -> str:
    if fact.node_id is not None:
        return fact.node_name or "someone"
    if fact.number is not None:
        unit = f" {spoken(fact.unit)}" if fact.unit is not None and spoken(fact.unit) not in {"none", "count"} else ""
        return f"{number_text(fact.number)}{unit}"
    if fact.enum_value is not None:
        return fact_word(fact.enum_name, fact.enum_value)
    return fact.name or ""


def step_text(step: AccountStep) -> str:
    parts = [step.actor_name or "someone", spoken(step.action)]
    if step.target_name:
        parts.append(step.target_name)
    if step.locus_kind is not StepLocus.NONE and (step.locus_name or step.locus_key):
        parts.append(f"at the {step.locus_name or spoken(step.locus_key or '')}")
    if step.instrument_kind is not InstrumentKind.NONE and (step.instrument_name or step.instrument_key):
        parts.append(f"with {step.instrument_name or spoken(step.instrument_key or '')}")
    text = " ".join(parts)
    if step.amount is not None:
        unit = f" {spoken(step.unit)}" if step.unit is not None else ""
        text += f", {number_text(step.amount)}{unit}"
    if step.damage_type is not None:
        text += f", {spoken(step.damage_type)}"
    if step.outcome is not None:
        text += f": {spoken(step.outcome)}"
    if step.states:
        text += " (" + ", ".join(f"{state.node_name or 'someone'} {spoken(state.state)}" for state in step.states) + ")"
    return text


def change_text(change: AccountChange) -> str:
    field = spoken(change.field) if change.field else spoken(change.table_name)
    before = change.before_node_name or (number_text(change.before_number) if change.before_number is not None else change.before_text)
    after = change.after_node_name or (number_text(change.after_number) if change.after_number is not None else change.after_text)
    if change.field is None:
        return f"{spoken(change.operation)} of {an(field)} record"
    return f"{field} {before if before is not None else 'nothing'} to {after if after is not None else 'nothing'}"


def change_reason(change: AccountChange) -> str | None:
    if not change.terms:
        return None
    return ", ".join(f"{spoken(term.term.split('.')[-1])} {number_text(term.amount)}" for term in change.terms[:3])


def difference_text(row: RumourDistortionRow, names: dict[int, str]) -> str:
    told = (
        names.get(row.told_node_id or 0)
        or (number_text(row.told_number) if row.told_number is not None else None)
        or (f"year {row.told_year}" if row.told_year is not None else None)
        or (spoken(row.told_action) if row.told_action is not None else None)
        or (spoken(row.told_outcome) if row.told_outcome is not None else None)
        or (spoken(row.told_enum_value) if row.told_enum_value is not None else None)
        or ("another happening" if row.told_incident_id is not None else None)
    )
    target = spoken(row.role) if row.role is not None else spoken(row.fact_key) if row.fact_key is not None else "a step"
    if row.distortion is RumourDistortion.STEP_DROPPED:
        return "a step was left out"
    return f"{spoken(row.distortion)}: {target} told as {told}" if told else f"{spoken(row.distortion)}: {target}"


async def account_context(
    session: AsyncSession, incident_id: int, *, step_offset: int, step_limit: int, distortions: Sequence[RumourDistortionRow] = (), fidelity: int | None = None
) -> EventAccountContext:
    account: Account = await account_of(session, incident_id)
    named = await session.get(IncidentNameRow, incident_id)
    told = None
    differences: list[str] = []
    if distortions:
        telling = await telling_of(session, incident_id)
        told = await told_text(session, telling, distortions) if telling is not None else None
        names = await node_names(session, [row.told_node_id for row in distortions])
        differences = [difference_text(row, names) for row in distortions]
    hidden_steps = {row.step_id for row in distortions if row.distortion is RumourDistortion.STEP_DROPPED}
    steps = [step for step in account.steps if step.id not in hidden_steps]
    shown = steps[step_offset : step_offset + step_limit]
    roles = [
        AccountRole(role=spoken(item.role), name=item.name or "someone", id=item.node_id, seen=SEEN.get(item.witness_mode.value) if item.witness_mode else None)
        for item in account.participants
        if item.role is not IncidentRole.WITNESS
    ]
    return EventAccountContext(
        id=account.id,
        name=named.name if named is not None else None,
        epoch=account.moment.epoch,
        year=account.moment.year,
        place=account.place_name,
        line=account.line or account.retold,
        told=told,
        fidelity=fidelity,
        differences=differences,
        roles=roles,
        facts=[AccountFactLine(key=spoken(fact.key), value=fact_text(fact)) for fact in account.facts],
        steps=[AccountStepLine(position=step_offset + index, round=step.round, text=step_text(step)) for index, step in enumerate(shown)],
        step_offset=step_offset,
        more_steps=max(0, len(steps) - step_offset - len(shown)),
        cause=account.causes[-1].text if account.causes and account.causes[-1].text else None,
        effects=[link.text for link in account.effects if link.text],
        witnesses=len(account.witnesses),
    )


async def account_text(
    session: AsyncSession, incident_id: int, *, step_offset: int, step_limit: int, distortions: Sequence[RumourDistortionRow] = (), fidelity: int | None = None
) -> str:
    context = await account_context(session, incident_id, step_offset=step_offset, step_limit=step_limit, distortions=distortions, fidelity=fidelity)
    return render(PromptId.EVENT_ACCOUNT, context)


def entry_line(entry: HistoryEntry) -> RecordLine:
    how = ", ".join(spoken(role) for role in entry.roles) or None
    return RecordLine(id=entry.incident_id, age=entry.moment.epoch, text=entry.line or spoken(entry.kind), how=how)


async def records_text(session: AsyncSession, node_id: int, *, title: str, tool: str, limit: int) -> str:
    page = await history_of(session, node_id, limit=limit)
    context = EventRecordsContext(
        title=title,
        accounts=[entry_line(entry) for entry in page.incidents],
        more_accounts=max(0, page.total_incidents - len(page.incidents)),
        steps=[RecordLine(id=step.incident_id, age=step.moment.epoch, text=step_text(step)) for step in page.steps],
        more_steps=max(0, page.total_steps - len(page.steps)),
        changes=[RecordLine(id=change.id, age=change.moment.epoch, text=change_text(change), how=change_reason(change)) for change in page.changes],
        more_changes=max(0, page.total_changes - len(page.changes)),
        tool=tool,
    )
    return render(PromptId.EVENT_RECORDS, context)
