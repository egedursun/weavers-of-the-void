from dataclasses import dataclass
from typing import Any

from sqlalchemy import UniqueConstraint, func, select

from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import an
from aerona.db.base import Base
from aerona.db.tables.concealment import BreachRow, HiddenTruthRow, PublicKnowledgeRow, TruthKeeperRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.powers import (
    MagicSystemGrammarRow,
    MagicSystemLinkRow,
    MagicSystemRow,
    MagicSystemSourceRow,
    PowerRestrictionRow,
    PowerRow,
    PowerSourceCostRow,
    PowerSourceHazardRow,
    PowerSourceInteractionRow,
    PowerSourceResistanceRow,
    PowerSourceRow,
    PowerTriggerRow,
    SourceTideRow,
    SystemRestrictionRow,
)
from aerona.db.write_guard import held
from aerona.domain.enums.arcana import SpellForm, SpellTechnique
from aerona.domain.enums.concealment import BreachCause, ConcealScope, HiddenTruthKind, KeeperRole
from aerona.domain.enums.powers import (
    Learnability,
    PowerOrigin,
    PowerState,
    PowerStructure,
    PowerVisibility,
    SourceAccess,
    SourceLocus,
    SourceRenewal,
)
from aerona.engine.arcana.enchantments import pay_essence
from aerona.engine.concealment.truths import breach, knowledge
from aerona.engine.context import TickContext
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_int, clamp_percent

SOURCE_PARTS: dict[str, type[Base]] = {
    "cost": PowerSourceCostRow,
    "resistance": PowerSourceResistanceRow,
    "hazard": PowerSourceHazardRow,
    "interaction": PowerSourceInteractionRow,
    "tide": SourceTideRow,
}
SYSTEM_PARTS: dict[str, type[Base]] = {
    "source": MagicSystemSourceRow,
    "link": MagicSystemLinkRow,
    "grammar": MagicSystemGrammarRow,
    "restriction": SystemRestrictionRow,
}
POWER_PARTS: dict[str, type[Base]] = {"restriction": PowerRestrictionRow, "trigger": PowerTriggerRow}
TRUTH_METHODS = (
    "by_oath",
    "by_law",
    "by_memory_removal",
    "by_cover_story",
    "by_discrediting",
    "by_isolation",
    "by_passing",
    "by_silencing",
    "by_neglect",
    "by_nature",
)
OWNER_KEYS = {"source_id", "system_id", "power_id", "first_source_id", "first_system_id", "line_id", "bank_entity_id"}


@dataclass(frozen=True)
class SourceDraft:
    name: str
    scope_id: int | None
    locus: SourceLocus
    renewal: SourceRenewal
    access: SourceAccess
    visibility: PowerVisibility
    stability: int


@dataclass(frozen=True)
class SystemDraft:
    name: str
    scope_id: int
    structure: PowerStructure
    predictability: int
    prevalence: int
    cost_severity: int
    access: SourceAccess
    learnability: Learnability


@dataclass(frozen=True)
class PowerDraft:
    holder_id: int
    technique: SpellTechnique
    form: SpellForm
    strength: int
    control: int
    origin: PowerOrigin
    state: PowerState
    visibility: PowerVisibility
    source_id: int | None = None
    system_id: int | None = None
    granted_by_id: int | None = None


@dataclass(frozen=True)
class TruthDraft:
    title: str
    subject_id: int
    kind: HiddenTruthKind
    hidden_from: ConcealScope
    scope_id: int | None
    strength: int
    methods: tuple[str, ...]
    sanity_cost: int
    keeper_id: int | None


async def node_exists(ctx: TickContext, node_id: int | None, what: str) -> None:
    if node_id is not None and await ctx.session.get(NodeRow, node_id) is None:
        raise NotFoundError(f"No such {what}.")


async def source_of(ctx: TickContext, source_id: int) -> PowerSourceRow:
    row = await ctx.session.get(PowerSourceRow, source_id)
    if row is None:
        raise NotFoundError("No such source of power.")
    return row


async def create_source(ctx: TickContext, draft: SourceDraft) -> PowerSourceRow:
    await node_exists(ctx, draft.scope_id, "place for the source")
    if not draft.name.strip():
        raise ValidationFailedError("A source needs a name.")
    row = PowerSourceRow(
        name=draft.name.strip(),
        description="",
        scope_node_id=draft.scope_id,
        drawn_from=draft.locus,
        renewal=draft.renewal,
        access=draft.access,
        visibility=draft.visibility,
        stability=clamp_percent(draft.stability),
        built_in=None,
        founded_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await note(ctx, f"A source of power came to be: {row.name}.", key="source.created", ids=[draft.scope_id] if draft.scope_id is not None else [])
    return row


async def edit_fields(row: Any, values: dict[str, Any], hold: bool, release: list[str], allowed: set[str]) -> list[str]:
    unknown = sorted(set(values) - allowed)
    if unknown:
        raise ValidationFailedError(f"These cannot be set here: {', '.join(unknown)}.")
    locked = [field for field in (row.locked or []) if field not in release]
    for field, value in values.items():
        setattr(row, field, value)
        if hold and field not in locked:
            locked.append(field)
    row.locked = locked
    return sorted(values)


def part_table(kind: str, parts: dict[str, type[Base]]) -> type[Base]:
    if kind not in parts:
        raise ValidationFailedError(f"No part of kind {kind}.")
    return parts[kind]


async def add_part(ctx: TickContext, parts: dict[str, type[Base]], kind: str, owner_id: int, values: dict[str, Any]) -> Base:
    table = part_table(kind, parts)
    columns = {column.key for column in table.__table__.columns} - {"id", "locked"}
    owner_key = next(column for column in sorted(columns) if column in OWNER_KEYS)
    unknown = sorted(set(values) - columns)
    if unknown:
        raise ValidationFailedError(f"{an(kind, capital=True)} has no {', '.join(unknown)}.")
    fields = {owner_key: owner_id, **values}
    await refuse_duplicate(ctx, table, kind, fields)
    row = table(**fields, locked=[])
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def refuse_duplicate(ctx: TickContext, table: type[Base], kind: str, fields: dict[str, Any]) -> None:
    for constraint in table.metadata.tables[str(table.__tablename__)].constraints:
        if not isinstance(constraint, UniqueConstraint):
            continue
        keys = [column.key for column in constraint.columns]
        if not all(key in fields for key in keys):
            continue
        found = await ctx.session.scalar(select(func.count()).select_from(table).where(*(getattr(table, key) == fields[key] for key in keys)))
        if found:
            raise ValidationFailedError(f"It already has that {kind}.")


async def edit_part(ctx: TickContext, parts: dict[str, type[Base]], kind: str, part_id: int, values: dict[str, Any], *, hold: bool, release: list[str]) -> Base:
    table = part_table(kind, parts)
    row = await ctx.session.get(table, part_id)
    if row is None:
        raise NotFoundError(f"No such {kind}.")
    columns = {column.key for column in table.__table__.columns} - {"id", "locked"} - OWNER_KEYS
    await edit_fields(row, values, hold, release, columns)
    await ctx.session.flush()
    return row


async def delete_part(ctx: TickContext, parts: dict[str, type[Base]], kind: str, part_id: int) -> None:
    table = part_table(kind, parts)
    row = await ctx.session.get(table, part_id)
    if row is None:
        raise NotFoundError(f"No such {kind}.")
    await ctx.session.delete(row)
    await ctx.session.flush()


async def create_system(ctx: TickContext, draft: SystemDraft) -> MagicSystemRow:
    await node_exists(ctx, draft.scope_id, "world or realm for the system")
    if not draft.name.strip():
        raise ValidationFailedError("A system of power needs a name.")
    row = MagicSystemRow(
        name=draft.name.strip(),
        description="",
        scope_node_id=draft.scope_id,
        structure=draft.structure,
        predictability=clamp_percent(draft.predictability),
        prevalence=clamp_percent(draft.prevalence),
        cost_severity=clamp_percent(draft.cost_severity),
        access=draft.access,
        learnability=draft.learnability,
        founded_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await note(ctx, f"A system of power took shape: {row.name}.", key="magic_system.created", ids=[draft.scope_id])
    return row


async def system_of(ctx: TickContext, system_id: int) -> MagicSystemRow:
    row = await ctx.session.get(MagicSystemRow, system_id)
    if row is None:
        raise NotFoundError("No such system of power.")
    return row


async def power_of(ctx: TickContext, power_id: int) -> PowerRow:
    row = await ctx.session.get(PowerRow, power_id)
    if row is None:
        raise NotFoundError("No such power.")
    return row


async def create_power(ctx: TickContext, draft: PowerDraft) -> PowerRow:
    await node_exists(ctx, draft.holder_id, "holder")
    if held(draft.holder_id):
        raise ValidationFailedError("That one is held against the world.")
    if draft.source_id is not None:
        await source_of(ctx, draft.source_id)
    if draft.system_id is not None:
        await system_of(ctx, draft.system_id)
    row = PowerRow(
        holder_node_id=draft.holder_id,
        system_id=draft.system_id,
        source_id=draft.source_id,
        technique=draft.technique,
        form=draft.form,
        strength=clamp_int(draft.strength, 1, 10),
        control=clamp_percent(draft.control),
        origin=draft.origin,
        state=draft.state,
        visibility=draft.visibility,
        strain=0,
        strain_cap=30,
        granted_by_node_id=draft.granted_by_id,
        uses=0,
        gained_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def grant_power(ctx: TickContext, god_id: int, draft: PowerDraft) -> PowerRow:
    if not await pay_essence(ctx.session, ctx.rules, god_id, ctx.rules.powers.grant_cost):
        raise ValidationFailedError("The god has too little essence to grant a power.")
    row = await create_power(ctx, PowerDraft(**{**draft.__dict__, "origin": PowerOrigin.GRANTED, "granted_by_id": god_id, "state": PowerState.ACTIVE}))
    holder = await ctx.session.get(EntityRow, draft.holder_id)
    await note(ctx, f"A god gave {holder.name if holder is not None else 'a mortal'} a power.", key="power.granted", ids=[draft.holder_id])
    return row


async def revoke_power(ctx: TickContext, god_id: int, power_id: int) -> PowerRow:
    row = await power_of(ctx, power_id)
    if row.granted_by_node_id != god_id:
        raise ValidationFailedError("Only the god who granted a power can take it back.")
    if held(row.holder_node_id):
        raise ValidationFailedError("That one is held against the world.")
    row.state = PowerState.LOST
    await note(ctx, "A god took back a power it had given.", key="power.revoked", ids=[row.holder_node_id])
    return row


async def set_state(ctx: TickContext, power_id: int, state: PowerState) -> PowerRow:
    row = await power_of(ctx, power_id)
    if held(row.holder_node_id):
        raise ValidationFailedError("That one is held against the world.")
    row.state = state
    if state is PowerState.ACTIVE:
        row.strain = 0
    await ctx.session.flush()
    return row


async def create_truth(ctx: TickContext, draft: TruthDraft) -> HiddenTruthRow:
    await node_exists(ctx, draft.subject_id, "subject")
    await node_exists(ctx, draft.scope_id, "population or realm")
    known = {
        "by_oath",
        "by_law",
        "by_memory_removal",
        "by_cover_story",
        "by_discrediting",
        "by_isolation",
        "by_passing",
        "by_silencing",
        "by_neglect",
        "by_nature",
    }
    unknown = sorted(set(draft.methods) - known)
    if unknown:
        raise ValidationFailedError(f"No way of keeping a truth called {', '.join(unknown)}.")
    row = HiddenTruthRow(
        title=draft.title.strip() or "a hidden truth",
        description="",
        subject_node_id=draft.subject_id,
        kind=draft.kind,
        hidden_from=draft.hidden_from,
        scope_node_id=draft.scope_id,
        strength=clamp_percent(draft.strength),
        sanity_cost=clamp_percent(draft.sanity_cost),
        founded_epoch=ctx.epoch,
        tended_epoch=ctx.epoch,
        locked=[],
        **dict.fromkeys(draft.methods, True),
    )
    ctx.session.add(row)
    await ctx.session.flush()
    if draft.keeper_id is not None:
        await node_exists(ctx, draft.keeper_id, "keeper")
        ctx.session.add(TruthKeeperRow(truth_id=row.id, keeper_node_id=draft.keeper_id, role=KeeperRole.GUARDIAN, locked=[]))
        await ctx.session.flush()
    return row


async def truth_of(ctx: TickContext, truth_id: int) -> HiddenTruthRow:
    row = await ctx.session.get(HiddenTruthRow, truth_id)
    if row is None:
        raise NotFoundError("No such hidden truth.")
    return row


async def reveal(ctx: TickContext, truth_id: int, population_id: int) -> PublicKnowledgeRow:
    truth = await truth_of(ctx, truth_id)
    await node_exists(ctx, population_id, "population")
    row = await knowledge(ctx, truth.id, population_id)
    row.know_pct = row.believe_pct = PERCENT
    row.revealed_epoch = ctx.epoch
    await note(ctx, f"What was hidden was made known: {truth.title}.", key="truth.revealed_by_hand", ids=[truth.subject_node_id, population_id])
    await ctx.session.flush()
    return row


async def trigger_breach(ctx: TickContext, truth_id: int, cause: BreachCause, place_id: int | None) -> BreachRow:
    truth = await truth_of(ctx, truth_id)
    if truth.revealed:
        raise ValidationFailedError("That truth is already known to all it was hidden from.")
    row = await breach(ctx, truth, cause, place_id=place_id)
    if row is None:
        raise ValidationFailedError("That truth is held against the world.")
    return row


async def hide(ctx: TickContext, truth_id: int) -> HiddenTruthRow:
    truth = await truth_of(ctx, truth_id)
    truth.revealed = False
    for row in await ctx.session.scalars(select(PublicKnowledgeRow).where(PublicKnowledgeRow.truth_id == truth.id)):
        if not row.locked:
            row.know_pct = row.believe_pct = 0
            row.revealed_epoch = None
    await ctx.session.flush()
    return truth
