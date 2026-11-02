from aerona.constants.schema import NAME_MAX_LENGTH, SHORT_TEXT_MAX_LENGTH, TITLE_MAX_LENGTH
from aerona.db.tables.epochs import EpochRow, EpochWorldNarrativeRow
from aerona.db.tables.lore import ChronicleEntityRow, ChronicleRow, HistorianViewRow
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.migration.legacy.context import MigrationContext
from aerona.migration.legacy.idmap import LegacyKind
from aerona.migration.legacy.importers.cosmos import UNKNOWN_VALUE
from aerona.migration.legacy.source import LegacyRow
from aerona.migration.legacy.timestamps import legacy_time
from aerona.migration.legacy.values import as_dict, as_int, as_list, as_text, truncated


def _entity_ids(context: MigrationContext, row: LegacyRow) -> list[int]:
    found: list[int] = []
    missing = 0
    for value in as_list(row.json("entity_ids")):
        legacy = as_int(value)
        if legacy is None or legacy <= 0:
            continue
        new_id = context.entity(legacy)
        if new_id is None:
            missing += 1
        elif new_id not in found:
            found.append(new_id)
    if missing:
        context.report.convert("chronicle_links_to_missing_entities", missing)
    return found


async def import_chronicle(context: MigrationContext) -> None:
    hidden = context.vocabulary.enums["hidden_chronicle_kind"]
    created: list[tuple[int, ChronicleRow, list[int]]] = []
    for row in context.source.iterate("chronicle", ("id",)):
        legacy_id = row.integer("id") or 0
        raw_kind = row.text("kind")
        kind = context.vocabulary.decode_as("chronicle_kind", raw_kind, ChronicleKind)
        if kind is None:
            context.report.warn(UNKNOWN_VALUE, f"chronicle:{legacy_id}", f"kind {raw_kind!r} read as system")
            kind = ChronicleKind.SYSTEM
        text = row.text("text")
        if text is None:
            context.report.place_failed("chronicle", f"chronicle:{legacy_id}", "empty line")
            continue
        links = _entity_ids(context, row)
        first = context.facts(links[0]) if links else None
        year = row.integer("year")
        chronicle = ChronicleRow(
            epoch=max(1, row.integer("epoch") or 1),
            year=year if year is not None and year >= 0 else None,
            kind=kind,
            visible=raw_kind not in hidden,
            son_id=context.son(row.integer("son_id")),
            world_id=first.world_id if first is not None else None,
            text=text,
        )
        stamp = legacy_time(row.raw("created_at"))
        if stamp is not None:
            chronicle.created_at = stamp
        created.append((legacy_id, chronicle, links))
    context.session.add_all([chronicle for _, chronicle, _ in created])
    await context.session.flush()
    for legacy_id, chronicle, links in created:
        context.ids.put(LegacyKind.CHRONICLE, legacy_id, chronicle.id)
        for position, entity_id in enumerate(links):
            context.add(ChronicleEntityRow(chronicle_id=chronicle.id, entity_id=entity_id, position=position))
        await context.flush_if_full()
    await context.flush()
    legacy_links = context.source.count("chronicle_entities")
    context.report.convert("chronicle_links_legacy_table", legacy_links)


async def import_epochs(context: MigrationContext) -> None:
    for row in context.source.iterate("epochs", ("epoch",)):
        epoch = row.integer("epoch")
        if epoch is None:
            continue
        reference = f"epoch:{epoch}"
        start, end = row.integer("year_start"), row.integer("year_end")
        if start is not None and end is not None and end < start:
            start, end = end, start
        chronicler = as_dict(row.json("chronicler"))
        context.add(
            EpochRow(
                epoch=epoch,
                name=truncated(context.report, reference, "name", row.text("name"), NAME_MAX_LENGTH),
                narrative=row.text("narrative"),
                summary=row.text("summary"),
                year_start=start,
                year_end=end,
                closed_at=legacy_time(row.raw("closed_at")),
                chronicler_name=truncated(
                    context.report, reference, "chronicler", as_text(context.vocabulary.field("chronicler", chronicler, "name")), NAME_MAX_LENGTH
                ),
                chronicler_identity=truncated(
                    context.report, reference, "chronicler identity", as_text(context.vocabulary.field("chronicler", chronicler, "who")), SHORT_TEXT_MAX_LENGTH
                ),
            )
        )
    seen: set[tuple[int, int]] = set()
    for row in context.source.iterate("epoch_world_narratives", ("epoch", "world_id")):
        epoch, world_id = row.integer("epoch"), context.world(row.integer("world_id"))
        if epoch is None or world_id is None or (epoch, world_id) in seen:
            context.report.place_failed("world narrative", f"epoch:{epoch}", f"world {row.integer('world_id')} is missing")
            continue
        seen.add((epoch, world_id))
        context.add(EpochWorldNarrativeRow(epoch=epoch, world_id=world_id, narrative=row.text("narrative"), summary=row.text("summary")))
    views: set[tuple[int, int]] = set()
    for row in context.source.iterate("historian_views", ("id",)):
        epoch, people = row.integer("epoch"), context.entity(row.integer("people_id"))
        text = row.text("text")
        if epoch is None or people is None or text is None or (epoch, people) in views:
            context.report.place_failed("historian view", f"historian_view:{row.integer('id')}", "people missing or repeated")
            continue
        views.add((epoch, people))
        context.add(
            HistorianViewRow(
                epoch=epoch,
                people_entity_id=people,
                historian=truncated(context.report, f"historian_view:{row.integer('id')}", "historian", row.text("historian"), TITLE_MAX_LENGTH),
                text=text,
            )
        )
    await context.flush()
