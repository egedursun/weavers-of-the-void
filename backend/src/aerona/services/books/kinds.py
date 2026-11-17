from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.kinds.holding_labels import SPREAD_LABELS, STANCE_LABELS
from aerona.db.kind_concepts.registry import CONCEPTS
from aerona.db.kind_concepts.spec import ConceptSpec, KindProperty
from aerona.db.tables.kinds import KindHoldingRow, KindRow
from aerona.services.books.typed import RecordTable, TypedIndex, TypedSection

WAYS_OF_LIFE = "Ways of life"
KINDS_MADE = "Kinds made"
KINDS_FOUND = "Kinds found here"
YES, NO = "yes", "no"
REGISTRY_HEADERS = ("Name", "Category", "World", "Made by", "Derived from", "Built in", "Retired", "Since epoch")


def kind_title(spec: ConceptSpec, kind: KindRow) -> str:
    return f"{kind.name} ({spec.label.lower()}, {spec.category_labels[kind.category_key()].lower()})"


def told(item: KindProperty, kind: KindRow) -> str:
    number, _, label = item.shown(getattr(kind, item.column))
    return (label or "") if item.options is not None else str(number)


def properties_of(spec: ConceptSpec, kind: KindRow) -> list[str]:
    return [f"{item.label.lower()}: {text}" for item in spec.properties if (text := told(item, kind))]


def named(names: dict[int, str], node_id: int | None) -> str:
    return names.get(node_id, "") if node_id is not None else ""


async def add_kind_sections(session: AsyncSession, index: TypedIndex) -> int:
    names = index.names
    added = 0
    held: dict[int, list[str]] = defaultdict(list)
    made: dict[int, list[str]] = defaultdict(list)
    found: dict[int, list[str]] = defaultdict(list)
    holdings = list(await session.scalars(select(KindHoldingRow).order_by(KindHoldingRow.concept, KindHoldingRow.kind_id, KindHoldingRow.id)))
    for spec in CONCEPTS.values():
        kinds = {kind.id: kind for kind in await session.scalars(select(spec.table).order_by(spec.table.id))}
        holders: dict[int, list[str]] = defaultdict(list)
        for item in holdings:
            kind = kinds.get(item.kind_id) if item.concept is spec.concept else None
            if kind is None:
                continue
            holders[kind.id].append(f"{named(names, item.holder_node_id)} ({STANCE_LABELS[item.stance].lower()}, {item.strength})")
            held[item.holder_node_id].append(
                f"{kind_title(spec, kind)} · stance: {STANCE_LABELS[item.stance].lower()} · strength: {item.strength} · "
                f"spread: {SPREAD_LABELS[item.spread].lower()} · since epoch {item.since_epoch}"
            )
        table = RecordTable(
            f"{spec.plural} of the cosmos",
            [*REGISTRY_HEADERS, *(item.label for item in spec.properties), "Held by"],
        )
        for kind in kinds.values():
            parent = kinds.get(kind.derived_from_id) if kind.derived_from_id is not None else None
            facts = " · ".join(properties_of(spec, kind))
            lineage = f" · derived from {parent.name}" if parent is not None else ""
            line = f"{kind_title(spec, kind)} · {facts}{lineage}{' · retired' if kind.retired else ''}"
            if kind.origin_node_id is not None:
                made[kind.origin_node_id].append(line)
            if kind.world_id is not None:
                found[kind.world_id].append(line)
            table.rows.append(
                [
                    kind.name,
                    spec.category_labels[kind.category_key()],
                    named(names, kind.world_id),
                    named(names, kind.origin_node_id),
                    parent.name if parent is not None else "",
                    YES if kind.built_in else NO,
                    YES if kind.retired else NO,
                    str(kind.created_epoch),
                    *(told(item, kind) for item in spec.properties),
                    ", ".join(holders.get(kind.id, [])),
                ]
            )
        if table.rows:
            index.records.append(table)
            added += 1
    for title, lines in ((WAYS_OF_LIFE, held), (KINDS_MADE, made), (KINDS_FOUND, found)):
        for node_id, rows in lines.items():
            index.sections[node_id].append(TypedSection(title, rows=rows))
            added += 1
    return added
