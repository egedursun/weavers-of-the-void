from enum import StrEnum
from typing import Any

from sqlalchemy import inspect, select

from aerona.core.total import total
from aerona.db.kind_concepts.registry import CONCEPTS
from aerona.db.kind_concepts.spec import ConceptSpec
from aerona.db.tables.kinds import KindHoldingRow, KindRow
from aerona.domain.enums.kinds import KindConcept, KindSpread, KindStance
from aerona.engine.context import TickContext


def spec_of(concept: KindConcept) -> ConceptSpec | None:
    return CONCEPTS.get(concept)


def category_named(spec: ConceptSpec, key: str) -> StrEnum | None:
    folded = key.strip().casefold().replace(" ", "_")
    for member in spec.category:
        if folded in (member.value, spec.category_labels[member.value].casefold().replace(" ", "_")):
            return member
    return None


def categories_told(spec: ConceptSpec) -> str:
    return ", ".join(sorted(spec.category_labels))


async def kind_of(ctx: TickContext, spec: ConceptSpec, kind_id: int) -> KindRow | None:
    row = await ctx.session.get(spec.table, kind_id)
    return row if row is not None and not row.retired else None


def filled(spec: ConceptSpec, row: KindRow) -> None:
    columns = inspect(spec.table).columns
    for item in spec.properties:
        column = columns[item.column]
        if getattr(row, item.column) is not None or column.nullable or column.default is not None or column.server_default is not None:
            continue
        enum_class = getattr(column.type, "enum_class", None)
        if enum_class is not None and item.options:
            setattr(row, item.column, enum_class(next(iter(item.options))))
        else:
            setattr(row, item.column, item.low)


async def make_kind(ctx: TickContext, spec: ConceptSpec, values: dict[str, Any]) -> KindRow:
    row = spec.table(**values)
    filled(spec, row)
    row.created_epoch = ctx.epoch
    row.locked = []
    ctx.session.add(row)
    await ctx.session.flush()
    return row


HOLDINGS = "kind_holding_index"


async def holding_index(ctx: TickContext) -> dict[tuple[KindConcept, int, int], KindHoldingRow]:
    index: dict[tuple[KindConcept, int, int], KindHoldingRow] | None = ctx.session.info.get(HOLDINGS)
    if index is None:
        rows = await ctx.session.scalars(select(KindHoldingRow))
        index = {(row.concept, row.kind_id, row.holder_node_id): row for row in rows}
        ctx.session.info[HOLDINGS] = index
    return index


async def hold_kind(
    ctx: TickContext, concept: KindConcept, kind_id: int, holder_id: int, *, stance: KindStance, strength: int, spread: KindSpread
) -> KindHoldingRow:
    index = await holding_index(ctx)
    found = index.get((concept, kind_id, holder_id))
    if found is not None and found not in ctx.session:
        found = None
    if found is None:
        found = KindHoldingRow(concept=concept, kind_id=kind_id, holder_node_id=holder_id, since_epoch=ctx.epoch, locked=[])
        ctx.session.add(found)
        index[(concept, kind_id, holder_id)] = found
    if "stance" not in found.locked:
        found.stance = stance
    if "strength" not in found.locked:
        found.strength = strength
    found.spread = spread
    await ctx.session.flush()
    return found


STANCE_TOLD = total(
    KindStance,
    {
        KindStance.MAKES: "make",
        KindStance.USES: "use",
        KindStance.FAVOURS: "favour",
        KindStance.FORBIDS: "forbid",
        KindStance.BLESSES: "bless",
    },
)
