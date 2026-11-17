from typing import Any

from pydantic import Field
from sqlalchemy import delete, select

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.total import total
from aerona.db.kind_concepts.registry import CONCEPTS
from aerona.db.kind_concepts.spec import ConceptSpec
from aerona.db.tables.kinds import HOLDING_FIELDS, KIND_BASE_FIELDS, KindHoldingRow
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.kinds import KindConcept, KindSpread, KindStance
from aerona.engine.kinds.acts import filled
from aerona.engine.powers.control import edit_fields
from aerona.services.player.cosmography import Edited
from aerona.services.player.powers import typed
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

NAME = Field(min_length=1, max_length=120)
STANCE_WORDS = total(
    KindStance,
    {
        KindStance.MAKES: "makes",
        KindStance.USES: "uses",
        KindStance.FAVOURS: "favours",
        KindStance.FORBIDS: "forbids",
        KindStance.BLESSES: "blesses",
    },
)


class KindDraft(Command):
    concept: KindConcept
    name: str = NAME
    category: str
    world_id: int | None = None
    origin_node_id: int | None = None
    values: dict[str, Any] = Field(default_factory=dict)


class KindEdit(Edited):
    concept: KindConcept
    kind_id: int
    hold: bool = True


class KindTarget(Command):
    concept: KindConcept
    kind_id: int


class KindHold(KindTarget):
    hold: bool = True


class KindPass(KindTarget):
    holder_node_id: int
    stance: KindStance = KindStance.USES
    strength: int = Field(default=50, ge=0, le=100)


class KindRetire(KindTarget):
    retired: bool = True


def fields_of(spec: ConceptSpec) -> set[str]:
    return {*KIND_BASE_FIELDS, "category", *(item.column for item in spec.properties)}


def category_of(spec: ConceptSpec, value: str) -> Any:
    try:
        return spec.category(value)
    except ValueError as error:
        raise ValidationFailedError(f"{spec.label} has no category {value}.") from error


async def kind_of(scope: PlayerScope, concept: KindConcept, kind_id: int) -> Any:
    spec = CONCEPTS[concept]
    row = await scope.session.get(spec.table, kind_id)
    if row is None:
        raise NotFoundError(f"No such {spec.label.lower()}.")
    return row


@player_action("authored_kind:create", ActionKind.EDIT_RECORD)
async def kind_create(scope: PlayerScope, command: KindDraft) -> Effect:
    spec = CONCEPTS[command.concept]
    ctx = await scope.context("kind_create")
    row = spec.table(name=command.name, category=category_of(spec, command.category), world_id=command.world_id, origin_node_id=command.origin_node_id)
    row.created_epoch = ctx.epoch
    row.locked = []
    await edit_fields(row, typed(spec.table, command.values), False, [], fields_of(spec) - {"category", "name"})
    filled(spec, row)
    ctx.session.add(row)
    await ctx.session.flush()
    if command.origin_node_id is not None and await ctx.session.get(NodeRow, command.origin_node_id) is not None:
        ctx.session.add(
            KindHoldingRow(
                concept=command.concept,
                kind_id=row.id,
                holder_node_id=command.origin_node_id,
                stance=KindStance.MAKES,
                spread=KindSpread.DECREE,
                since_epoch=ctx.epoch,
                locked=[],
            )
        )
    return Effect(f"A new {spec.label.lower()}, {row.name}, is made.", command.origin_node_id, values={"kind_id": row.id})


@player_action("authored_kind:edit", ActionKind.EDIT_RECORD)
async def kind_edit(scope: PlayerScope, command: KindEdit) -> Effect:
    spec = CONCEPTS[command.concept]
    row = await kind_of(scope, command.concept, command.kind_id)
    values = typed(spec.table, command.values)
    if "category" in values:
        values["category"] = category_of(spec, str(values["category"]))
    changed = await edit_fields(row, values, command.hold, command.release, fields_of(spec))
    return Effect(f"{row.name}: {', '.join(changed) or 'nothing'} set.", row.origin_node_id)


@player_action("authored_kind:hold", ActionKind.EDIT_RECORD)
async def kind_hold(scope: PlayerScope, command: KindHold) -> Effect:
    spec = CONCEPTS[command.concept]
    row = await kind_of(scope, command.concept, command.kind_id)
    row.locked = sorted(fields_of(spec)) if command.hold else []
    return Effect(f"{row.name} is {'held against the world' if command.hold else 'free to change'}.", row.origin_node_id)


@player_action("authored_kind:retire", ActionKind.EDIT_RECORD)
async def kind_retire(scope: PlayerScope, command: KindRetire) -> Effect:
    row = await kind_of(scope, command.concept, command.kind_id)
    row.retired = command.retired
    locked = [field for field in row.locked if field != "retired"]
    row.locked = [*locked, "retired"]
    return Effect(f"{row.name} is {'retired' if command.retired else 'in use again'}.", row.origin_node_id)


@player_action("authored_kind:spread", ActionKind.EDIT_RECORD)
async def kind_spread(scope: PlayerScope, command: KindPass) -> Effect:
    row = await kind_of(scope, command.concept, command.kind_id)
    holder = await scope.session.get(NodeRow, command.holder_node_id)
    if holder is None:
        raise NotFoundError("No such holder.")
    ctx = await scope.context("kind_spread")
    found = await ctx.session.scalar(
        select(KindHoldingRow).where(KindHoldingRow.concept == command.concept, KindHoldingRow.kind_id == row.id, KindHoldingRow.holder_node_id == holder.id)
    )
    if found is None:
        found = KindHoldingRow(concept=command.concept, kind_id=row.id, holder_node_id=holder.id, since_epoch=ctx.epoch, locked=[])
        ctx.session.add(found)
    found.stance = command.stance
    found.strength = command.strength
    found.spread = KindSpread.DIVINE
    found.locked = [field for field in HOLDING_FIELDS if field != "spread"]
    return Effect(f"{holder.name} now {STANCE_WORDS[command.stance]} {row.name}.", holder.id)


@player_action("authored_kind:delete", ActionKind.EDIT_RECORD)
async def kind_delete(scope: PlayerScope, command: KindTarget) -> Effect:
    row = await kind_of(scope, command.concept, command.kind_id)
    await scope.session.execute(delete(KindHoldingRow).where(KindHoldingRow.concept == command.concept, KindHoldingRow.kind_id == row.id))
    await scope.session.delete(row)
    return Effect(f"{row.name} is gone from the world.", None)
