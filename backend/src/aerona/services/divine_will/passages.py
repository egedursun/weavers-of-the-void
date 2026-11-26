import re
from collections import defaultdict
from collections.abc import Iterable, Mapping
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.grammar import spoken
from aerona.db.base import Base
from aerona.db.repositories.chronicle import shown_lines
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.divine_will import DivineWillArtifactNodeRow, DivineWillArtifactRow, DivineWillArtifactVersionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.epochs import EpochRow, EpochWorldNarrativeRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.job import JobRow
from aerona.db.tables.lore import ChronicleEntityRow, ChronicleRow, CouncilRow, LexemeRow, MessageRow
from aerona.db.tables.meta import MapNoteRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.divine_will import ArtifactFormat, ChunkSource
from aerona.domain.enums.entity import EntityStatus
from aerona.rules.registry import Rules
from aerona.services.books.model import BookBuilder
from aerona.services.books.records import LEDGER_TITLES, Ledger
from aerona.services.books.typed import RecordTable, TypedSection, title_of, words
from aerona.services.divine_will.chunking import PARAGRAPH_BREAK, Passage

IDENTIFIER = re.compile(r"[a-z0-9]+(?:_[a-z0-9]+)+")
TAGS = re.compile(r"<[^>]+>")
FACT_SEPARATOR = " · "
TITLE_SEPARATOR = " — "
LIST_SEPARATOR = "; "
DIVINE_WILL_PREFIX = "divine_will_"
YES = "yes"
NO = "no"
DUPLICATE_MARK = "#"
DIVINE_WILL_TITLES = frozenset(title_of(table.name) for table in Base.metadata.sorted_tables if table.name.startswith(DIVINE_WILL_PREFIX))
UNREAD_TABLES = frozenset({JobRow.__tablename__})
UNREAD_TITLES = DIVINE_WILL_TITLES | LEDGER_TITLES | frozenset(title_of(table) for table in UNREAD_TABLES)
SOURCE_ORDER = {source: position for position, source in enumerate(ChunkSource)}


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


async def node_names(session: AsyncSession) -> dict[int, str]:
    return {node_id: name for node_id, name in await session.execute(select(NodeRow.id, NodeRow.name).order_by(NodeRow.id))}


async def entity_passages(session: AsyncSession, names: Mapping[int, str]) -> list[Passage]:
    found: list[Passage] = []
    rows = await session.scalars(select(EntityRow).where(EntityRow.status != EntityStatus.REJECTED).order_by(EntityRow.id))
    for entity in rows:
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
        found.append(Passage(ChunkSource.ENTITY, str(entity.id), heading(entity.name, kind), body, node_id=entity.id))
        if entity.private_note:
            found.append(Passage(ChunkSource.NOTE, f"entity:{entity.id}", heading(entity.name, "note"), entity.private_note, node_id=entity.id))
    return found


async def son_passages(session: AsyncSession, names: Mapping[int, str]) -> list[Passage]:
    found: list[Passage] = []
    for son in await session.scalars(select(SonRow).order_by(SonRow.id)):
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
        found.append(Passage(ChunkSource.SON, str(son.id), heading(son.name, son.title), body, node_id=son.id))
    return found


async def foreign_god_passages(session: AsyncSession, names: Mapping[int, str]) -> list[Passage]:
    found: list[Passage] = []
    for god in await session.scalars(select(ForeignGodRow).order_by(ForeignGodRow.id)):
        domains = ", ".join(spoken(domain) for domain in (god.domain_primary, god.domain_secondary) if domain is not None)
        body = body_of(
            fields(("Domains", domains), ("Status", spoken(god.status)), ("World", named(names, god.world_id))),
            [god.description or ""],
            fields(("Personality", god.personality), ("Existence", god.existence_profile)),
            labelled(god.depth) if god.depth is not None else [],
        )
        found.append(Passage(ChunkSource.FOREIGN_GOD, str(god.id), heading(god.name, god.title or ""), body, node_id=god.id))
    return found


async def world_body_passages(session: AsyncSession, names: Mapping[int, str]) -> list[Passage]:
    found: list[Passage] = []
    for world in await session.scalars(select(WorldRow).order_by(WorldRow.id)):
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
        found.append(Passage(ChunkSource.WORLD, str(world.id), heading(world.name, spoken(world.world_type)), body, node_id=world.id))
    for star in await session.scalars(select(StarRow).order_by(StarRow.id)):
        body = body_of(
            fields(("Age", spoken(star.age_stage)), ("Galactic zone", spoken(star.galactic_zone))),
            [star.description or ""],
            labelled(star.depth) if star.depth is not None else [],
        )
        found.append(Passage(ChunkSource.STAR, str(star.id), heading(star.name, spoken(star.star_type)), body, node_id=star.id))
    return found


async def creator_passages(session: AsyncSession) -> list[Passage]:
    found: list[Passage] = []
    for creator in await session.scalars(select(CreatorRow).order_by(CreatorRow.id)):
        body = body_of(
            fields(("Appearance", creator.appearance), ("Temperament", creator.temperament), ("Note", creator.note)),
            [f"Passion: {text}" for passion in creator.passions if (text := plain(passion))],
            labelled(creator.depth) if creator.depth is not None else [],
            labelled(creator.epic) if creator.epic is not None else [],
        )
        found.append(Passage(ChunkSource.CREATOR, str(creator.id), heading(creator.name, creator.title or ""), body, node_id=creator.id))
    return found


async def word_passages(session: AsyncSession, names: Mapping[int, str]) -> list[Passage]:
    found: list[Passage] = []
    for word in await session.scalars(select(LexemeRow).order_by(LexemeRow.id)):
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
        found.append(Passage(ChunkSource.WORD, str(word.id), title, body, node_id=word.language_entity_id))
    return found


async def epoch_passages(session: AsyncSession, names: Mapping[int, str]) -> list[Passage]:
    found: list[Passage] = []
    for epoch in await session.scalars(select(EpochRow).order_by(EpochRow.epoch)):
        body = body_of(fields(("Summary", epoch.summary), ("Narrative", epoch.narrative), ("Chronicler", epoch.chronicler_name)))
        found.append(Passage(ChunkSource.EPOCH, str(epoch.epoch), heading(f"Epoch {epoch.epoch}", epoch.name or ""), body))
    narratives = await session.scalars(select(EpochWorldNarrativeRow).order_by(EpochWorldNarrativeRow.epoch, EpochWorldNarrativeRow.world_id))
    for narrative in narratives:
        body = body_of(fields(("Summary", narrative.summary), ("Narrative", narrative.narrative)))
        title = heading(f"Epoch {narrative.epoch}", f"on {named(names, narrative.world_id)}")
        found.append(Passage(ChunkSource.EPOCH, f"{narrative.epoch}:{narrative.world_id}", title, body, node_id=narrative.world_id))
    return found


async def chronicle_passages(session: AsyncSession) -> tuple[list[Passage], dict[int, str]]:
    subjects: dict[int, int] = {}
    link = ChronicleEntityRow
    links = await session.execute(select(link.chronicle_id, link.entity_id).order_by(link.chronicle_id, link.position))
    for chronicle_id, entity_id in links:
        subjects.setdefault(chronicle_id, entity_id)
    found: list[Passage] = []
    lines: dict[int, str] = {}
    rows = await session.scalars(select(ChronicleRow).where(ChronicleRow.kind != ChronicleKind.SYSTEM, shown_lines()).order_by(ChronicleRow.id))
    for line in rows:
        lines[line.id] = line.text
        moment = f"epoch {line.epoch}" + (f", year {line.year}" if line.year is not None else "")
        node = subjects.get(line.id) or line.son_id or line.world_id
        found.append(Passage(ChunkSource.CHRONICLE, str(line.id), heading("Chronicle", moment), line.text, node_id=node))
    return found, lines


def incident_body(ledger: Ledger, incident: IncidentRow, lines: Mapping[int, str]) -> str:
    grouped: dict[str, list[str]] = defaultdict(list)
    for row in ledger.participants.get(incident.id, []):
        grouped[spoken(row.role)].append(ledger.name(row.node_id))
    cause = ledger.incidents.get(incident.cause_incident_id) if incident.cause_incident_id is not None else None
    terms = [ledger.term_text(term.op, term.term, term.amount, term.source_node_id, term.source_incident_id) for term in ledger.terms.get(incident.id, [])]
    return body_of(
        [lines.get(incident.chronicle_id, "") if incident.chronicle_id is not None else ""],
        fields(("Named", ledger.name_of(incident))),
        [f"{role[:1].upper()}{role[1:]}: {', '.join(name for name in people if name)}" for role, people in grouped.items()],
        [FACT_SEPARATOR.join(ledger.fact_text(fact) for fact in ledger.facts.get(incident.id, []))],
        fields(
            ("Terms", LIST_SEPARATOR.join(terms)),
            ("Steps", " ".join(ledger.step_text(step) for step in ledger.steps.get(incident.id, []))),
            ("Rumours", LIST_SEPARATOR.join(ledger.rumour_text(rumour) for rumour in ledger.rumours.get(incident.id, []))),
            ("Cause", ledger.line_of(cause) if cause is not None else None),
            ("From", ledger.name(incident.origin_entity_id)),
            ("To", ledger.name(incident.destination_entity_id)),
            ("Note", incident.note),
        ),
    )


def incident_passages(ledger: Ledger, lines: Mapping[int, str]) -> list[Passage]:
    found: list[Passage] = []
    for incident in ledger.incidents.values():
        place = ledger.name(incident.place_entity_id)
        moment = f"epoch {incident.epoch}" + (f", year {incident.year}" if incident.year is not None else "") + (f", at {place}" if place else "")
        taking = ledger.participants.get(incident.id, [])
        node = incident.place_entity_id or (taking[0].node_id if taking else None) or incident.world_id
        body = incident_body(ledger, incident, lines)
        found.append(Passage(ChunkSource.INCIDENT, str(incident.id), heading(words(incident.kind), moment), body, node_id=node))
    return found


async def message_passages(session: AsyncSession, names: Mapping[int, str]) -> list[Passage]:
    found: list[Passage] = []
    for message in await session.scalars(select(MessageRow).order_by(MessageRow.id)):
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
        found.append(Passage(ChunkSource.MESSAGE, str(message.id), title, body, node_id=message.sender_node_id))
    return found


async def council_passages(session: AsyncSession) -> list[Passage]:
    found: list[Passage] = []
    for council in await session.scalars(select(CouncilRow).order_by(CouncilRow.id)):
        body = body_of(fields(("Passed", council.passed)), labelled(council.minutes))
        found.append(Passage(ChunkSource.COUNCIL, str(council.id), heading(f"Council of epoch {council.epoch}", council.topic), body))
    return found


async def note_passages(session: AsyncSession, names: Mapping[int, str]) -> list[Passage]:
    return [
        Passage(ChunkSource.NOTE, f"map:{note.id}", heading(named(names, note.world_id) or "Map", "map note"), note.text, node_id=note.world_id)
        for note in await session.scalars(select(MapNoteRow).order_by(MapNoteRow.id))
    ]


def readable_body(body: str, format: ArtifactFormat) -> str:
    return TAGS.sub(" ", body) if format is ArtifactFormat.HTML else body


async def artifact_passages(session: AsyncSession) -> list[Passage]:
    subjects: dict[int, int] = {}
    subject = DivineWillArtifactNodeRow
    for artifact_id, node_id in await session.execute(select(subject.artifact_id, subject.node_id).order_by(subject.artifact_id, subject.node_id)):
        subjects.setdefault(artifact_id, node_id)
    found: list[Passage] = []
    artifact_row, version_row = DivineWillArtifactRow, DivineWillArtifactVersionRow
    current = (version_row.artifact_id == artifact_row.id) & (version_row.version == artifact_row.current_version)
    rows = await session.execute(select(artifact_row, version_row).join(version_row, current).order_by(artifact_row.id))
    for artifact, version in rows:
        body = body_of(
            fields(("Status", spoken(artifact.status)), ("Language", artifact.language), ("Tags", artifact.tags), ("Summary", version.summary)),
            [readable_body(version.body, artifact.format)],
        )
        title = heading(artifact.title, spoken(artifact.kind))
        found.append(Passage(ChunkSource.ARTIFACT, str(artifact.id), title, body, node_id=subjects.get(artifact.id)))
    return found


def section_body(section: TypedSection) -> str:
    facts = "\n".join(f"{fact.label}: {fact.value}" for fact in section.facts)
    return body_of([facts], section.lines)


def record_body(table: RecordTable) -> str:
    return body_of(FACT_SEPARATOR.join(f"{header}: {value}" for header, value in zip(table.headers, row, strict=False) if value) for row in table.rows)


def typed_passages(builder: BookBuilder, names: Mapping[int, str]) -> list[Passage]:
    found: list[Passage] = []
    for node_id in sorted(builder.typed.sections):
        seen: dict[str, int] = defaultdict(int)
        for section in builder.typed.of(node_id):
            if section.title in UNREAD_TITLES:
                continue
            seen[section.title] += 1
            mark = f"{DUPLICATE_MARK}{seen[section.title]}" if seen[section.title] > 1 else ""
            title = heading(named(names, node_id) or builder.names.get(node_id, ""), section.title)
            found.append(Passage(ChunkSource.TYPED_SECTION, f"{node_id}:{section.title}{mark}", title, section_body(section), node_id=node_id))
    for table in builder.typed.records:
        if table.title in UNREAD_TITLES:
            continue
        found.append(Passage(ChunkSource.TYPED_SECTION, f"records:{table.title}", heading("Records of the Cosmos", table.title), record_body(table)))
    return found


async def world_passages(session: AsyncSession, rules: Rules) -> list[Passage]:
    names = await node_names(session)
    builder = BookBuilder(session, rules)
    await builder.load_common()
    chronicle, lines = await chronicle_passages(session)
    found = [
        *await entity_passages(session, names),
        *typed_passages(builder, names),
        *chronicle,
        *incident_passages(builder.ledger, lines),
        *await son_passages(session, names),
        *await foreign_god_passages(session, names),
        *await world_body_passages(session, names),
        *await creator_passages(session),
        *await word_passages(session, names),
        *await epoch_passages(session, names),
        *await note_passages(session, names),
        *await message_passages(session, names),
        *await council_passages(session),
        *await artifact_passages(session),
    ]
    return sorted(found, key=lambda passage: (SOURCE_ORDER[passage.source], passage.source_id))
