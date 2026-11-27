import json
import re
from collections import defaultdict
from collections.abc import Callable, Collection, Iterable, Mapping, Sequence
from functools import cache
from itertools import batched
from typing import Any

from pydantic import BaseModel
from sqlalchemy import ColumnElement, Select, and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapper
from sqlalchemy.sql.elements import KeyedColumnElement

from aerona.catalog.season_positions import SeasonPosition
from aerona.core.grammar import spoken
from aerona.db.base import Base
from aerona.db.ledger_capture import UNCAPTURED_TABLES, jsonable, key_text
from aerona.db.profile_guard import shape_of_table, table_name
from aerona.db.repositories.chronicle import shown_lines
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.culture import RumourRow
from aerona.db.tables.divine_will import DivineWillArtifactNodeRow, DivineWillArtifactRow, DivineWillArtifactVersionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.epochs import EpochRow, EpochWorldNarrativeRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.job import JobRow
from aerona.db.tables.lore import ChronicleEntityRow, ChronicleRow, CouncilRow, LexemeRow, MessageRow
from aerona.db.tables.meta import MapNoteRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.records import IncidentFactRow, IncidentStepRow, IncidentStepStateRow, IncidentTermRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.tellings import IncidentNameRow, RumourDistortionRow
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.divine_will import ArtifactFormat, ChunkSource
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.environment import WorldLink
from aerona.services.books.records import LEDGER_TITLES, Ledger
from aerona.services.books.typed import (
    NAMED_TABLES,
    REFERENCE_LABELS,
    REFERENCE_LISTS,
    SKIPPED_COLUMNS,
    SKIPPED_TABLES,
    TypedIndex,
    TypedSection,
    _named_label,
    _owner,
    _rows,
    attribute_of,
    title_of,
    words,
)
from aerona.services.divine_will.chunking import PARAGRAPH_BREAK, Passage

IDENTIFIER = re.compile(r"[a-z0-9]+(?:_[a-z0-9]+)+")
TAGS = re.compile(r"<[^>]+>")
FACT_SEPARATOR = " · "
TITLE_SEPARATOR = " — "
LIST_SEPARATOR = "; "
DIVINE_WILL_PREFIX = "divine_will_"
YES = "yes"
NO = "no"
RECORDS_HEADING = "Records of the Cosmos"
KEY_SEPARATOR = ":"
LOOKUP_BATCH = 500
DIVINE_WILL_TITLES = frozenset(title_of(table.name) for table in Base.metadata.sorted_tables if table.name.startswith(DIVINE_WILL_PREFIX))
UNREAD_TABLES = frozenset({JobRow.__tablename__})
UNREAD_TITLES = DIVINE_WILL_TITLES | LEDGER_TITLES | frozenset(title_of(table) for table in UNREAD_TABLES)
NODE_REF = "n"
ROW_REF = "r"
SEASON_REF = "s"
WORLD_REF = "w"
LINE_REF = "c"

PassageKey = tuple[ChunkSource, str]
RowKey = dict[str, Any]


def node_ref(node_id: int) -> str:
    return f"{NODE_REF}:{node_id}"


def row_ref(table: str, row_id: int) -> str:
    return f"{ROW_REF}:{table}:{row_id}"


def season_ref(world_id: int) -> str:
    return f"{SEASON_REF}:{world_id}"


def world_ref(entity_id: int) -> str:
    return f"{WORLD_REF}:{entity_id}"


def line_ref(chronicle_id: int) -> str:
    return f"{LINE_REF}:{chronicle_id}"


class TracedNames(dict[int, str]):
    def __init__(self, names: Mapping[int, str]) -> None:
        super().__init__(names)
        self.seen: set[str] = set()

    def get(self, key: Any, default: Any = None) -> Any:
        if isinstance(key, int) and not isinstance(key, bool):
            self.seen.add(node_ref(key))
        return super().get(key, default)

    def __getitem__(self, key: int) -> str:
        self.seen.add(node_ref(key))
        return super().__getitem__(key)

    def taken(self) -> frozenset[str]:
        found = frozenset(self.seen)
        self.seen.clear()
        return found


class TracedLabels(dict[int, str]):
    def __init__(self, table: str, seen: set[str], labels: Mapping[int, str], refs: Mapping[int, frozenset[str]]) -> None:
        super().__init__(labels)
        self.table = table
        self.seen = seen
        self.refs = dict(refs)

    def get(self, key: Any, default: Any = None) -> Any:
        if isinstance(key, int) and not isinstance(key, bool):
            self.seen.add(row_ref(self.table, key))
            self.seen.update(self.refs.get(key, frozenset()))
        return super().get(key, default)


class TracedTypedIndex(TypedIndex):
    def __init__(self, names: TracedNames) -> None:
        super().__init__(names)
        self.traced = names

    def season_name(self, position: SeasonPosition, row: Any, value: int) -> str:
        through = getattr(row, position.through, None)
        if isinstance(through, int):
            if position.link is WorldLink.WORLD:
                self.traced.seen.add(season_ref(through))
            else:
                self.traced.seen.add(world_ref(through))
                world = self.worlds_of.get(through)
                if world is not None:
                    self.traced.seen.add(season_ref(world))
        return super().season_name(position, row, value)

    async def load_referenced(self, session: AsyncSession, groups: list[tuple[list[KeyedColumnElement[Any]], list[Any]]]) -> None:
        wanted: dict[str, set[int]] = defaultdict(set)
        for columns, rows in groups:
            for column in columns:
                listed = REFERENCE_LISTS.get(column.key)
                target = listed or next((foreign.column.table.name for foreign in column.foreign_keys), None)
                if target is None or target in NAMED_TABLES:
                    continue
                for row in rows:
                    value = attribute_of(row, column)
                    items = value if listed is not None and isinstance(value, list) else [value]
                    wanted[target].update(item for item in items if isinstance(item, int) and not isinstance(item, bool))
        for target, ids in sorted(wanted.items()):
            mapper = mapper_of(target)
            label = (REFERENCE_LABELS.get(target) or _named_label(mapper)) if mapper is not None else None
            if mapper is None or label is None or not ids:
                continue
            known = self.references.get(target)
            labels = dict(known) if known is not None else {}
            refs = dict(known.refs) if isinstance(known, TracedLabels) else {}
            missing = sorted(ids - set(labels))
            key = mapper.primary_key[0]
            for part in batched(missing, LOOKUP_BATCH, strict=False):
                for row in await session.scalars(select(mapper.class_).where(key.in_(part))):
                    self.traced.seen.clear()
                    labels[row.id] = label(row, self.names)
                    refs[row.id] = self.traced.taken()
            self.references[target] = TracedLabels(target, self.traced.seen, labels, refs)

    def reference(self, column: KeyedColumnElement[Any], value: int) -> str:
        target = next((foreign.column.table.name for foreign in column.foreign_keys), None)
        if target is not None and target not in NAMED_TABLES:
            self.traced.seen.add(row_ref(target, value))
        return super().reference(column, value)

    def row_section(self, table: str, columns: list[KeyedColumnElement[Any]], row: Any, single: bool) -> TypedSection:
        return self._section(table, columns, [row], single)


@cache
def mappers() -> dict[str, Mapper[Any]]:
    return {table_name(mapper): mapper for mapper in Base.registry.mappers}


def mapper_of(table: str) -> Mapper[Any] | None:
    return mappers().get(table)


@cache
def indexed_tables() -> tuple[str, ...]:
    return tuple(
        sorted(table for table in mappers() if table not in SKIPPED_TABLES and table not in UNCAPTURED_TABLES and title_of(table) not in UNREAD_TITLES)
    )


@cache
def indexed_set() -> frozenset[str]:
    return frozenset(indexed_tables())


def scalar(value: Any) -> str | None:
    if value is None:
        return ""
    if isinstance(value, bool):
        return YES if value else NO
    if isinstance(value, float):
        return f"{value:g}"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        text = value.strip()
        return text.replace("_", " ") if IDENTIFIER.fullmatch(text) else text
    return None


def plain(value: Any) -> str:
    simple = scalar(value)
    if simple is not None:
        return simple
    if isinstance(value, BaseModel):
        return plain(value.model_dump(mode="json", exclude_none=True))
    if isinstance(value, Mapping):
        parts = [f"{words(str(key))}: {text}" for key, item in value.items() if not str(key).endswith("_id") and (text := plain(item))]
        return ", ".join(parts)
    if isinstance(value, Iterable):
        return LIST_SEPARATOR.join(text for item in value if (text := plain(item)))
    return plain(getattr(value, "value", str(value)))


def labelled(value: Any) -> list[str]:
    data = value.model_dump(mode="json", exclude_none=True) if isinstance(value, BaseModel) else value
    if not isinstance(data, Mapping):
        text = plain(data)
        return [text] if text else []
    paragraphs: list[str] = []
    for key, item in data.items():
        if str(key) == "id" or str(key).endswith("_id"):
            continue
        label = words(str(key))
        if isinstance(item, list | tuple) and any(isinstance(entry, Mapping) for entry in item):
            paragraphs.extend(f"{label}: {text}" for entry in item if (text := plain(entry)))
            continue
        text = plain(item)
        if text:
            paragraphs.append(f"{label}: {text}")
    return paragraphs


def fields(*pairs: tuple[str, Any]) -> list[str]:
    return [f"{label}: {text}" for label, value in pairs if (text := plain(value))]


def body_of(*groups: Iterable[str]) -> str:
    return PARAGRAPH_BREAK.join(paragraph for group in groups for paragraph in group if paragraph)


def heading(name: str, *details: str) -> str:
    shown = [detail for detail in details if detail]
    return f"{name}{TITLE_SEPARATOR}{' '.join(shown)}" if shown else name


def named(names: Mapping[int, str], node_id: int | None) -> str:
    return names.get(node_id, "") if node_id is not None else ""


def numbers(keys: Collection[str]) -> list[int]:
    return sorted({int(key) for key in keys if key.isdigit()})


def restricted(statement: Any, column: Any, ids: list[int] | None) -> list[Any]:
    if ids is None:
        return [statement]
    return [statement.where(column.in_(part)) for part in batched(ids, LOOKUP_BATCH, strict=False)]


async def scalars_of(session: AsyncSession, statement: Select[Any], column: Any, ids: list[int] | None) -> list[Any]:
    found: list[Any] = []
    for part in restricted(statement, column, ids):
        found.extend(await session.scalars(part))
    return found


async def node_names(session: AsyncSession) -> TracedNames:
    return TracedNames({node_id: name for node_id, name in await session.execute(select(NodeRow.id, NodeRow.name).order_by(NodeRow.id))})


def traced(names: TracedNames, source: ChunkSource, source_id: str, title: str, body: str, *, node_id: int | None = None) -> Passage:
    return Passage(source, source_id, title, body, node_id=node_id, refs=names.taken())


async def entity_passages(session: AsyncSession, names: TracedNames, ids: list[int] | None = None) -> list[Passage]:
    found: list[Passage] = []
    statement = select(EntityRow).where(EntityRow.status != EntityStatus.REJECTED).order_by(EntityRow.id)
    for entity in await scalars_of(session, statement, EntityRow.id, ids):
        names.taken()
        names.seen.add(node_ref(entity.id))
        kind = spoken(entity.entity_type) + (f" ({entity.subtype})" if entity.subtype else "")
        body = body_of(
            fields(
                ("Title", entity.title),
                ("Status", None if entity.status is EntityStatus.CANON else spoken(entity.status)),
                ("World", named(names, entity.world_id)),
                ("Place", named(names, entity.location_id)),
            ),
            [entity.description],
            fields(("Fate", entity.fate_note)),
            labelled(entity.depth) if entity.depth is not None else [],
        )
        found.append(traced(names, ChunkSource.ENTITY, str(entity.id), heading(entity.name, kind), body, node_id=entity.id))
        if entity.private_note:
            names.seen.add(node_ref(entity.id))
            found.append(
                traced(names, ChunkSource.NOTE, f"entity{KEY_SEPARATOR}{entity.id}", heading(entity.name, "note"), entity.private_note, node_id=entity.id)
            )
    return found


async def son_passages(session: AsyncSession, names: TracedNames, ids: list[int] | None = None) -> list[Passage]:
    found: list[Passage] = []
    for son in await scalars_of(session, select(SonRow).order_by(SonRow.id), SonRow.id, ids):
        names.taken()
        names.seen.add(node_ref(son.id))
        body = body_of(
            fields(
                ("Domains", f"{spoken(son.domain_primary)}, {spoken(son.domain_secondary)}"),
                ("Rarity", spoken(son.rarity)),
                ("Status", spoken(son.status)),
                ("World", named(names, son.current_world_id)),
                ("Standing order", son.standing_order),
                ("Plan", son.plan),
                ("Reputation", spoken(son.reputation_label) if son.reputation_label is not None else None),
                ("Death", spoken(son.death_cause) if son.death_cause is not None else None),
            ),
            fields(("Personality", son.personality)),
            fields(("Existence", son.existence_profile)),
            labelled(son.epic) if son.epic is not None else [],
        )
        found.append(traced(names, ChunkSource.SON, str(son.id), heading(son.name, son.title), body, node_id=son.id))
    return found


async def foreign_god_passages(session: AsyncSession, names: TracedNames, ids: list[int] | None = None) -> list[Passage]:
    found: list[Passage] = []
    for god in await scalars_of(session, select(ForeignGodRow).order_by(ForeignGodRow.id), ForeignGodRow.id, ids):
        names.taken()
        names.seen.add(node_ref(god.id))
        domains = ", ".join(spoken(domain) for domain in (god.domain_primary, god.domain_secondary) if domain is not None)
        body = body_of(
            fields(("Domains", domains), ("Status", spoken(god.status)), ("World", named(names, god.world_id))),
            [god.description or ""],
            fields(("Personality", god.personality), ("Existence", god.existence_profile)),
            labelled(god.depth) if god.depth is not None else [],
        )
        found.append(traced(names, ChunkSource.FOREIGN_GOD, str(god.id), heading(god.name, god.title or ""), body, node_id=god.id))
    return found


async def world_body_passages(session: AsyncSession, names: TracedNames, ids: list[int] | None = None) -> list[Passage]:
    found: list[Passage] = []
    for world in await scalars_of(session, select(WorldRow).order_by(WorldRow.id), WorldRow.id, ids):
        names.taken()
        names.seen.add(node_ref(world.id))
        body = body_of(
            fields(
                ("Moon of", named(names, world.parent_world_id)),
                ("Star", named(names, world.star_id)),
                ("Age", spoken(world.age_stage)),
                ("Climate era", spoken(world.climate_era) if world.climate_era is not None else None),
            ),
            [world.description or ""],
            fields(("Cosmology", world.cosmology)),
            labelled(world.depth) if world.depth is not None else [],
        )
        found.append(traced(names, ChunkSource.WORLD, str(world.id), heading(world.name, spoken(world.world_type)), body, node_id=world.id))
    return found


async def star_passages(session: AsyncSession, names: TracedNames, ids: list[int] | None = None) -> list[Passage]:
    found: list[Passage] = []
    for star in await scalars_of(session, select(StarRow).order_by(StarRow.id), StarRow.id, ids):
        names.taken()
        names.seen.add(node_ref(star.id))
        body = body_of(
            fields(("Age", spoken(star.age_stage)), ("Galactic zone", spoken(star.galactic_zone))),
            [star.description or ""],
            labelled(star.depth) if star.depth is not None else [],
        )
        found.append(traced(names, ChunkSource.STAR, str(star.id), heading(star.name, spoken(star.star_type)), body, node_id=star.id))
    return found


async def creator_passages(session: AsyncSession, names: TracedNames, ids: list[int] | None = None) -> list[Passage]:
    found: list[Passage] = []
    for creator in await scalars_of(session, select(CreatorRow).order_by(CreatorRow.id), CreatorRow.id, ids):
        names.taken()
        names.seen.add(node_ref(creator.id))
        body = body_of(
            fields(("Appearance", creator.appearance), ("Temperament", creator.temperament), ("Note", creator.note)),
            [f"Passion: {text}" for passion in creator.passions if (text := plain(passion))],
            labelled(creator.depth) if creator.depth is not None else [],
            labelled(creator.epic) if creator.epic is not None else [],
        )
        found.append(traced(names, ChunkSource.CREATOR, str(creator.id), heading(creator.name, creator.title or ""), body, node_id=creator.id))
    return found


async def word_passages(session: AsyncSession, names: TracedNames, ids: list[int] | None = None) -> list[Passage]:
    found: list[Passage] = []
    for word in await scalars_of(session, select(LexemeRow).order_by(LexemeRow.id), LexemeRow.id, ids):
        names.taken()
        language = named(names, word.language_entity_id)
        body = body_of(
            fields(
                ("Meaning", word.meaning),
                ("Part of speech", spoken(word.part_of_speech) if word.part_of_speech is not None else None),
                ("Register", spoken(word.register)),
                ("Etymology", word.etymology),
                ("Example", word.example),
                ("Older form", word.proto_word),
            )
        )
        title = heading(word.word, f"word of {language}" if language else "word")
        found.append(traced(names, ChunkSource.WORD, str(word.id), title, body, node_id=word.language_entity_id))
    return found


def epoch_keys(keys: Collection[str] | None) -> tuple[list[int] | None, list[tuple[int, int]] | None]:
    if keys is None:
        return None, None
    whole = sorted({int(key) for key in keys if key.isdigit()})
    pairs = sorted({(int(epoch), int(world)) for key in keys if KEY_SEPARATOR in key for epoch, world in [key.split(KEY_SEPARATOR, 1)]})
    return whole, pairs


async def epoch_passages(session: AsyncSession, names: TracedNames, keys: Collection[str] | None = None) -> list[Passage]:
    found: list[Passage] = []
    whole, pairs = epoch_keys(keys)
    for epoch in await scalars_of(session, select(EpochRow).order_by(EpochRow.epoch), EpochRow.epoch, whole):
        names.taken()
        body = body_of(fields(("Summary", epoch.summary), ("Narrative", epoch.narrative), ("Chronicler", epoch.chronicler_name)))
        found.append(traced(names, ChunkSource.EPOCH, str(epoch.epoch), heading(f"Epoch {epoch.epoch}", epoch.name or ""), body))
    narrative = EpochWorldNarrativeRow
    statements = [select(narrative).order_by(narrative.epoch, narrative.world_id)]
    if pairs is not None:
        statements = [
            select(narrative).where(or_(*(and_(narrative.epoch == epoch, narrative.world_id == world) for epoch, world in part)))
            for part in batched(pairs, LOOKUP_BATCH, strict=False)
        ]
    for statement in statements:
        for row in await session.scalars(statement):
            names.taken()
            body = body_of(fields(("Summary", row.summary), ("Narrative", row.narrative)))
            title = heading(f"Epoch {row.epoch}", f"on {named(names, row.world_id)}")
            found.append(traced(names, ChunkSource.EPOCH, f"{row.epoch}{KEY_SEPARATOR}{row.world_id}", title, body, node_id=row.world_id))
    return found


async def chronicle_passages(session: AsyncSession, names: TracedNames, ids: list[int] | None = None) -> list[Passage]:
    subjects: dict[int, int] = {}
    link = ChronicleEntityRow
    for part in restricted(select(link.chronicle_id, link.entity_id).order_by(link.chronicle_id, link.position), link.chronicle_id, ids):
        for chronicle_id, entity_id in await session.execute(part):
            subjects.setdefault(chronicle_id, entity_id)
    found: list[Passage] = []
    statement = select(ChronicleRow).where(ChronicleRow.kind != ChronicleKind.SYSTEM, shown_lines()).order_by(ChronicleRow.id)
    for line in await scalars_of(session, statement, ChronicleRow.id, ids):
        names.taken()
        moment = f"epoch {line.epoch}" + (f", year {line.year}" if line.year is not None else "")
        node = subjects.get(line.id) or line.son_id or line.world_id
        found.append(traced(names, ChunkSource.CHRONICLE, str(line.id), heading("Chronicle", moment), line.text, node_id=node))
    return found


async def shown_texts(session: AsyncSession, ids: list[int]) -> dict[int, str]:
    statement = select(ChronicleRow.id, ChronicleRow.text).where(ChronicleRow.kind != ChronicleKind.SYSTEM, shown_lines())
    found: dict[int, str] = {}
    for part in batched(ids, LOOKUP_BATCH, strict=False):
        found.update({line_id: text for line_id, text in await session.execute(statement.where(ChronicleRow.id.in_(part)))})
    return found


async def incident_ledger(session: AsyncSession, names: TracedNames, ids: list[int] | None) -> tuple[Ledger, dict[int, str]]:
    ledger = Ledger(names)
    wanted = await scalars_of(session, select(IncidentRow).order_by(IncidentRow.epoch, IncidentRow.id), IncidentRow.id, ids)
    for row in wanted:
        ledger.incidents[row.id] = row
    told = ids if ids is not None else None
    for participant in await scalars_of(
        session,
        select(IncidentParticipantRow).order_by(IncidentParticipantRow.incident_id, IncidentParticipantRow.position),
        IncidentParticipantRow.incident_id,
        told,
    ):
        ledger.participants[participant.incident_id].append(participant)
    for fact in await scalars_of(
        session, select(IncidentFactRow).order_by(IncidentFactRow.incident_id, IncidentFactRow.key, IncidentFactRow.position), IncidentFactRow.incident_id, told
    ):
        ledger.facts[fact.incident_id].append(fact)
    for step in await scalars_of(
        session, select(IncidentStepRow).order_by(IncidentStepRow.incident_id, IncidentStepRow.position, IncidentStepRow.id), IncidentStepRow.incident_id, told
    ):
        ledger.steps[step.incident_id].append(step)
    step_ids = sorted(step.id for steps in ledger.steps.values() for step in steps) if told is not None else None
    for state in await scalars_of(
        session, select(IncidentStepStateRow).order_by(IncidentStepStateRow.step_id, IncidentStepStateRow.node_id), IncidentStepStateRow.step_id, step_ids
    ):
        ledger.states[state.step_id].append(state)
    for term in await scalars_of(
        session, select(IncidentTermRow).order_by(IncidentTermRow.incident_id, IncidentTermRow.position), IncidentTermRow.incident_id, told
    ):
        ledger.terms[term.incident_id].append(term)
    for name in await scalars_of(session, select(IncidentNameRow).order_by(IncidentNameRow.incident_id), IncidentNameRow.incident_id, told):
        ledger.named[name.incident_id] = name
    for rumour in await scalars_of(session, select(RumourRow).order_by(RumourRow.incident_id, RumourRow.epoch, RumourRow.id), RumourRow.incident_id, told):
        ledger.rumours[rumour.incident_id].append(rumour)
    rumour_ids = sorted(rumour.id for rumours in ledger.rumours.values() for rumour in rumours) if told is not None else None
    for distortion in await scalars_of(
        session, select(RumourDistortionRow).order_by(RumourDistortionRow.rumour_id, RumourDistortionRow.position), RumourDistortionRow.rumour_id, rumour_ids
    ):
        ledger.distortions[distortion.rumour_id].append(distortion)
    referenced = {row.cause_incident_id for row in wanted if row.cause_incident_id is not None}
    referenced.update(term.source_incident_id for terms in ledger.terms.values() for term in terms if term.source_incident_id is not None)
    referenced.update(row.told_incident_id for rows in ledger.distortions.values() for row in rows if row.told_incident_id is not None)
    missing = sorted(referenced - set(ledger.incidents))
    for row in await scalars_of(session, select(IncidentRow).order_by(IncidentRow.id), IncidentRow.id, missing):
        ledger.incidents[row.id] = row
    line_ids = sorted({row.chronicle_id for row in ledger.incidents.values() if row.chronicle_id is not None})
    for part in restricted(select(ChronicleRow.id, ChronicleRow.text).order_by(ChronicleRow.id), ChronicleRow.id, line_ids if told is not None else None):
        for chronicle_id, text in await session.execute(part):
            ledger.lines[chronicle_id] = text
    own_lines = sorted({row.chronicle_id for row in wanted if row.chronicle_id is not None})
    return ledger, await shown_texts(session, own_lines)


def incident_body(ledger: Ledger, incident: IncidentRow, lines: Mapping[int, str]) -> str:
    grouped: dict[str, list[str]] = defaultdict(list)
    told = lines.get(incident.chronicle_id, "") if incident.chronicle_id is not None else ""
    for row in ledger.participants.get(incident.id, []):
        grouped[spoken(row.role)].append(ledger.name_in(row.node_id, told))
    cause = ledger.incidents.get(incident.cause_incident_id) if incident.cause_incident_id is not None else None
    terms = [ledger.term_text(term.op, term.term, term.amount, term.source_node_id, term.source_incident_id) for term in ledger.terms.get(incident.id, [])]
    return body_of(
        [lines.get(incident.chronicle_id, "") if incident.chronicle_id is not None else ""],
        fields(("Named", ledger.name_of(incident))),
        [f"{role[:1].upper()}{role[1:]}: {', '.join(name for name in people if name)}" for role, people in grouped.items()],
        [FACT_SEPARATOR.join(ledger.fact_text(fact) for fact in ledger.facts.get(incident.id, []))],
        fields(
            ("Terms", LIST_SEPARATOR.join(terms)),
            ("Steps", " ".join(ledger.step_text(step, incident) for step in ledger.steps.get(incident.id, []))),
            ("Rumours", LIST_SEPARATOR.join(ledger.rumour_text(rumour) for rumour in ledger.rumours.get(incident.id, []))),
            ("Cause", ledger.line_of(cause) if cause is not None else None),
            ("From", ledger.name(incident.origin_entity_id)),
            ("To", ledger.name(incident.destination_entity_id)),
            ("Note", incident.note),
        ),
    )


async def incident_passages(session: AsyncSession, names: TracedNames, ids: list[int] | None = None) -> list[Passage]:
    ledger, lines = await incident_ledger(session, names, ids)
    chosen = set(ids) if ids is not None else None
    found: list[Passage] = []
    for incident in ledger.incidents.values():
        if chosen is not None and incident.id not in chosen:
            continue
        names.taken()
        place = ledger.name(incident.place_entity_id)
        moment = f"epoch {incident.epoch}" + (f", year {incident.year}" if incident.year is not None else "") + (f", at {place}" if place else "")
        taking = ledger.participants.get(incident.id, [])
        node = incident.place_entity_id or (taking[0].node_id if taking else None) or incident.world_id
        body = incident_body(ledger, incident, lines)
        if incident.chronicle_id is not None:
            names.seen.add(line_ref(incident.chronicle_id))
        found.append(traced(names, ChunkSource.INCIDENT, str(incident.id), heading(words(incident.kind), moment), body, node_id=node))
    return found


async def message_passages(session: AsyncSession, names: TracedNames, ids: list[int] | None = None) -> list[Passage]:
    found: list[Passage] = []
    for message in await scalars_of(session, select(MessageRow).order_by(MessageRow.id), MessageRow.id, ids):
        names.taken()
        sender, recipient = named(names, message.sender_node_id), named(names, message.recipient_node_id)
        title = heading(spoken(message.intent).capitalize(), f"from {sender} to {recipient}, epoch {message.epoch}")
        body = body_of(
            [message.text],
            fields(
                ("Wish", message.wish),
                ("Request", spoken(message.request) if message.request is not None else None),
                ("Tone", spoken(message.tone) if message.tone is not None else None),
                ("Medium", spoken(message.medium) if message.medium is not None else None),
                ("Content", spoken(message.content) if message.content is not None else None),
                ("State", spoken(message.state) if message.state is not None else None),
                ("Envoy", named(names, message.envoy_node_id)),
                ("Intercepted by", named(names, message.intercepted_by_node_id)),
            ),
        )
        found.append(traced(names, ChunkSource.MESSAGE, str(message.id), title, body, node_id=message.sender_node_id))
    return found


async def council_passages(session: AsyncSession, names: TracedNames, ids: list[int] | None = None) -> list[Passage]:
    found: list[Passage] = []
    for council in await scalars_of(session, select(CouncilRow).order_by(CouncilRow.id), CouncilRow.id, ids):
        names.taken()
        body = body_of(fields(("Passed", council.passed)), labelled(council.minutes))
        found.append(traced(names, ChunkSource.COUNCIL, str(council.id), heading(f"Council of epoch {council.epoch}", council.topic), body))
    return found


async def map_note_passages(session: AsyncSession, names: TracedNames, ids: list[int] | None = None) -> list[Passage]:
    found: list[Passage] = []
    for note in await scalars_of(session, select(MapNoteRow).order_by(MapNoteRow.id), MapNoteRow.id, ids):
        names.taken()
        title = heading(named(names, note.world_id) or "Map", "map note")
        found.append(traced(names, ChunkSource.NOTE, f"map{KEY_SEPARATOR}{note.id}", title, note.text, node_id=note.world_id))
    return found


async def note_passages(session: AsyncSession, names: TracedNames, keys: Collection[str] | None = None) -> list[Passage]:
    if keys is None:
        return await map_note_passages(session, names)
    entities = numbers([key.split(KEY_SEPARATOR, 1)[1] for key in keys if key.startswith(f"entity{KEY_SEPARATOR}")])
    maps = numbers([key.split(KEY_SEPARATOR, 1)[1] for key in keys if key.startswith(f"map{KEY_SEPARATOR}")])
    own = [passage for passage in await entity_passages(session, names, entities) if passage.source is ChunkSource.NOTE] if entities else []
    return own + (await map_note_passages(session, names, maps) if maps else [])


def readable_body(body: str, format: ArtifactFormat) -> str:
    return TAGS.sub(" ", body) if format is ArtifactFormat.HTML else body


async def artifact_passages(session: AsyncSession, names: TracedNames, ids: list[int] | None = None) -> list[Passage]:
    subjects: dict[int, int] = {}
    subject = DivineWillArtifactNodeRow
    for part in restricted(select(subject.artifact_id, subject.node_id).order_by(subject.artifact_id, subject.node_id), subject.artifact_id, ids):
        for artifact_id, node_id in await session.execute(part):
            subjects.setdefault(artifact_id, node_id)
    found: list[Passage] = []
    artifact_row, version_row = DivineWillArtifactRow, DivineWillArtifactVersionRow
    current = (version_row.artifact_id == artifact_row.id) & (version_row.version == artifact_row.current_version)
    for part in restricted(select(artifact_row, version_row).join(version_row, current).order_by(artifact_row.id), artifact_row.id, ids):
        for artifact, version in await session.execute(part):
            names.taken()
            body = body_of(
                fields(("Status", spoken(artifact.status)), ("Language", artifact.language), ("Tags", artifact.tags), ("Summary", version.summary)),
                [readable_body(version.body, artifact.format)],
            )
            title = heading(artifact.title, spoken(artifact.kind))
            found.append(traced(names, ChunkSource.ARTIFACT, str(artifact.id), title, body, node_id=subjects.get(artifact.id)))
    return found


def section_body(section: TypedSection) -> str:
    facts = "\n".join(f"{fact.label}: {fact.value}" for fact in section.facts)
    return body_of([facts], section.lines)


def row_key_of(mapper: Mapper[Any], row: Any) -> str:
    return key_text({column.name: jsonable(getattr(row, mapper.get_property_by_column(column).key)) for column in mapper.primary_key})


def typed_id(table: str, key: str) -> str:
    return f"{table}{KEY_SEPARATOR}{key}"


def typed_parts(source_id: str) -> tuple[str, RowKey] | None:
    table, separator, key = source_id.partition(KEY_SEPARATOR)
    if not separator or table not in mappers():
        return None
    try:
        values = json.loads(key)
    except ValueError:
        return None
    return (table, values) if isinstance(values, dict) else None


def key_condition(mapper: Mapper[Any], values: RowKey) -> ColumnElement[bool] | None:
    columns = {column.name: column for column in mapper.primary_key}
    if set(values) != set(columns):
        return None
    return and_(*(columns[name] == value for name, value in values.items()))


async def table_rows(session: AsyncSession, mapper: Mapper[Any], table: str, keys: Sequence[RowKey] | None) -> list[Any]:
    statement = _rows(mapper, table)
    if keys is None:
        return list(await session.scalars(statement))
    conditions = [condition for values in keys if (condition := key_condition(mapper, values)) is not None]
    found: list[Any] = []
    for part in batched(conditions, LOOKUP_BATCH, strict=False):
        found.extend(await session.scalars(statement.where(or_(*part))))
    return found


async def typed_passages(session: AsyncSession, names: TracedNames, wanted: Mapping[str, Sequence[RowKey] | None] | None = None) -> list[Passage]:
    index = TracedTypedIndex(names)
    await index.load_seasons(session)
    found: list[Passage] = []
    tables = indexed_tables() if wanted is None else tuple(sorted(table for table in wanted if table in indexed_set()))
    for table in tables:
        mapper = mappers()[table]
        owner = _owner(mapper)
        columns = [
            column
            for column in mapper.local_table.columns
            if (column.key not in SKIPPED_COLUMNS or (owner is None and column.primary_key)) and column.key != owner
        ]
        if not columns:
            continue
        rows = await table_rows(session, mapper, table, None if wanted is None else wanted[table])
        if not rows:
            continue
        await index.load_referenced(session, [(columns, rows)])
        single = shape_of_table(table) is not None
        title = title_of(table)
        for row in rows:
            names.taken()
            key = typed_id(table, row_key_of(mapper, row))
            node = attribute_of(row, mapper.local_table.columns[owner]) if owner is not None else None
            if isinstance(node, int) and not isinstance(node, bool):
                body = section_body(index.row_section(table, columns, row, single))
                passage_title = heading(named(names, node), title)
            else:
                node = None
                body = FACT_SEPARATOR.join(
                    f"{words(column.key)}: {text}" for column in columns if (text := index.value(column, attribute_of(row, column), row))
                )
                passage_title = heading(RECORDS_HEADING, title)
            if body:
                found.append(traced(names, ChunkSource.TYPED_SECTION, key, passage_title, body, node_id=node))
    return found


def typed_wanted(keys: Collection[str]) -> dict[str, Sequence[RowKey] | None]:
    wanted: dict[str, list[RowKey]] = defaultdict(list)
    for key in sorted(keys):
        parts = typed_parts(key)
        if parts is not None:
            wanted[parts[0]].append(parts[1])
    return dict(wanted)


async def by_numbers(
    render: Callable[[AsyncSession, TracedNames, list[int] | None], Any], session: AsyncSession, names: TracedNames, keys: Collection[str] | None
) -> list[Passage]:
    found: list[Passage] = await render(session, names, None if keys is None else numbers(keys))
    return found


async def by_typed(session: AsyncSession, names: TracedNames, keys: Collection[str] | None) -> list[Passage]:
    return await typed_passages(session, names, None if keys is None else typed_wanted(keys))


async def world_side(session: AsyncSession, names: TracedNames, keys: Collection[str] | None, source: ChunkSource) -> list[Passage]:
    render = {
        ChunkSource.ENTITY: entity_passages,
        ChunkSource.SON: son_passages,
        ChunkSource.FOREIGN_GOD: foreign_god_passages,
        ChunkSource.WORLD: world_body_passages,
        ChunkSource.STAR: star_passages,
        ChunkSource.CREATOR: creator_passages,
        ChunkSource.WORD: word_passages,
        ChunkSource.CHRONICLE: chronicle_passages,
        ChunkSource.INCIDENT: incident_passages,
        ChunkSource.MESSAGE: message_passages,
        ChunkSource.COUNCIL: council_passages,
        ChunkSource.ARTIFACT: artifact_passages,
    }.get(source)
    if render is not None:
        found = await by_numbers(render, session, names, keys)
        return [passage for passage in found if passage.source is source]
    if source is ChunkSource.EPOCH:
        return await epoch_passages(session, names, keys)
    if source is ChunkSource.NOTE:
        return await note_passages(session, names, keys)
    if source is ChunkSource.TYPED_SECTION:
        return await by_typed(session, names, keys)
    return []


WORLD_SOURCES = tuple(source for source in ChunkSource if source is not ChunkSource.ATTACHMENT)


async def keyed_passages(session: AsyncSession, keys: Collection[PassageKey]) -> list[Passage]:
    grouped: dict[ChunkSource, set[str]] = defaultdict(set)
    for source, source_id in keys:
        grouped[source].add(source_id)
    names = await node_names(session)
    found: list[Passage] = []
    for source in WORLD_SOURCES:
        if grouped.get(source):
            found.extend(await world_side(session, names, grouped[source], source))
    wanted = set(keys)
    return [passage for passage in found if (passage.source, passage.source_id) in wanted]


async def unit_passages(session: AsyncSession, units: Sequence[str]) -> list[Passage]:
    names = await node_names(session)
    found: list[Passage] = []
    for unit in units:
        source_value, _, table = unit.partition(KEY_SEPARATOR)
        source = ChunkSource(source_value)
        if source is ChunkSource.TYPED_SECTION:
            found.extend(await typed_passages(session, names, {table: None}))
        else:
            found.extend(await world_side(session, names, None, source))
    return found


def build_units() -> list[str]:
    units = [source.value for source in WORLD_SOURCES if source is not ChunkSource.TYPED_SECTION]
    units.extend(f"{ChunkSource.TYPED_SECTION.value}{KEY_SEPARATOR}{table}" for table in indexed_tables())
    return units
