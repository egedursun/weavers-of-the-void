from collections.abc import Sequence
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.death_causes import DEATH_CAUSES
from aerona.catalog.kinds.defined.son import SON_DEATH_CAUSE
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.chronicle import ChronicleRepository
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.ecology import BeastProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.tongues import DivineTongueRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.foreign_god import ForeignGodStatus
from aerona.domain.enums.mortal import DeathCause
from aerona.domain.enums.node import NodeKind
from aerona.domain.enums.presence import SpeakerGroup
from aerona.domain.enums.son import SonDeathCause, SonStatus
from aerona.engine.minds.profiles import MINDED_TYPES
from aerona.rules.registry import Rules

Voiced = SonRow | ForeignGodRow | EntityRow

ENTITY_GROUPS: dict[EntityType, SpeakerGroup] = {
    EntityType.MORTAL: SpeakerGroup.MORTALS,
    EntityType.SPIRIT: SpeakerGroup.SPIRITS,
    EntityType.COSMIC_BEING: SpeakerGroup.BEINGS,
    EntityType.OUTER_BEING: SpeakerGroup.BEINGS,
    EntityType.BEAST: SpeakerGroup.BEASTS,
}
GROUP_ORDER = {group: index for index, group in enumerate(SpeakerGroup)}
UNHEARD_STATUSES = frozenset({EntityStatus.REJECTED})
ENDED_STATUSES = frozenset({EntityStatus.DEAD, EntityStatus.DESTROYED})
ENDING_LINES = 40
NOT_A_SPEAKER = "{name} has no mind of its own to summon."
NO_SUCH_NODE = "No such being."


@dataclass(frozen=True)
class Speaker:
    node: Voiced
    group: SpeakerGroup
    dead: bool

    @property
    def node_id(self) -> int:
        return self.node.id

    @property
    def name(self) -> str:
        return self.node.name

    @property
    def kind(self) -> NodeKind:
        return self.node.kind

    @property
    def entity_type(self) -> EntityType | None:
        return self.node.entity_type if isinstance(self.node, EntityRow) else None

    @property
    def epithet(self) -> str:
        if isinstance(self.node, EntityRow):
            return self.node.subtype or ""
        return self.node.title or ""


@dataclass(frozen=True)
class SpeakerLine:
    node_id: int
    name: str
    kind: NodeKind
    entity_type: EntityType | None
    group: SpeakerGroup
    dead: bool


@dataclass(frozen=True)
class Death:
    epoch: int | None
    son_cause: SonDeathCause | None = None
    mortal_cause: DeathCause | None = None
    line: str = ""

    @property
    def how(self) -> str:
        if self.son_cause is not None:
            return SON_DEATH_CAUSE[self.son_cause].label.lower()
        if self.mortal_cause is not None:
            return DEATH_CAUSES[self.mortal_cause].label.lower()
        return ""


@dataclass(frozen=True)
class SpeakerCard:
    speaker: Speaker
    place_name: str = ""
    world_name: str = ""
    patron_name: str = ""
    faith: int | None = None
    languages: list[str] = field(default_factory=list)
    death: Death | None = None


def creature_mind(entity: EntityRow, profile: BeastProfileRow | None) -> int:
    if profile is not None:
        return profile.intelligence
    return int(getattr(entity.stats, "intelligence", 0) or 0)


def entity_dead(entity: EntityRow) -> bool:
    return entity.status in ENDED_STATUSES


async def speaker_of(session: AsyncSession, rules: Rules, node: NodeRow | None) -> Speaker | None:
    if isinstance(node, SonRow):
        return Speaker(node, SpeakerGroup.SONS, node.status is SonStatus.DEAD)
    if isinstance(node, ForeignGodRow):
        return Speaker(node, SpeakerGroup.FOREIGN_GODS, node.status is ForeignGodStatus.DEAD)
    if not isinstance(node, EntityRow) or node.entity_type not in MINDED_TYPES or node.status in UNHEARD_STATUSES:
        return None
    group = ENTITY_GROUPS.get(node.entity_type)
    if group is None:
        return None
    if group is SpeakerGroup.BEASTS and creature_mind(node, await session.get(BeastProfileRow, node.id)) < rules.mortal_agents.creature_min_intelligence:
        return None
    return Speaker(node, group, entity_dead(node))


async def heard_speaker(session: AsyncSession, rules: Rules, node_id: int) -> Speaker | None:
    node = await session.get(NodeRow, node_id)
    if node is None:
        raise NotFoundError(NO_SUCH_NODE)
    return await speaker_of(session, rules, node)


async def require_speaker(session: AsyncSession, rules: Rules, node_id: int) -> Speaker:
    node = await session.get(NodeRow, node_id)
    if node is None:
        raise NotFoundError(NO_SUCH_NODE)
    found = await speaker_of(session, rules, node)
    if found is None:
        raise ValidationFailedError(NOT_A_SPEAKER.format(name=node.name))
    return found


def name_filter(query: str) -> str:
    return f"%{query.strip()}%"


async def god_lines(session: AsyncSession, query: str) -> list[SpeakerLine]:
    found: list[SpeakerLine] = []
    sons = select(SonRow.id, SonRow.name, SonRow.status).order_by(SonRow.id)
    gods = select(ForeignGodRow.id, ForeignGodRow.name, ForeignGodRow.status).order_by(ForeignGodRow.id)
    if query.strip():
        sons = sons.where(SonRow.name.ilike(name_filter(query)))
        gods = gods.where(ForeignGodRow.name.ilike(name_filter(query)))
    for node_id, name, son_status in await session.execute(sons):
        found.append(SpeakerLine(node_id, name, NodeKind.SON, None, SpeakerGroup.SONS, son_status is SonStatus.DEAD))
    for node_id, name, god_status in await session.execute(gods):
        found.append(SpeakerLine(node_id, name, NodeKind.FOREIGN_GOD, None, SpeakerGroup.FOREIGN_GODS, god_status is ForeignGodStatus.DEAD))
    return found


async def entity_lines(session: AsyncSession, rules: Rules, query: str, types: Sequence[EntityType]) -> list[SpeakerLine]:
    statement = (
        select(EntityRow.id, EntityRow.name, EntityRow.entity_type, EntityRow.status)
        .where(EntityRow.entity_type.in_(types), EntityRow.status.not_in(UNHEARD_STATUSES))
        .order_by(EntityRow.id)
    )
    if query.strip():
        statement = statement.where(EntityRow.name.ilike(name_filter(query)))
    rows = list(await session.execute(statement))
    beasts = [node_id for node_id, _, entity_type, _ in rows if ENTITY_GROUPS.get(entity_type) is SpeakerGroup.BEASTS]
    minded = await minded_beasts(session, rules, beasts)
    found: list[SpeakerLine] = []
    for node_id, name, entity_type, status in rows:
        group = ENTITY_GROUPS.get(entity_type)
        if group is None or (group is SpeakerGroup.BEASTS and node_id not in minded):
            continue
        found.append(SpeakerLine(node_id, name, NodeKind.ENTITY, entity_type, group, status in ENDED_STATUSES))
    return found


async def minded_beasts(session: AsyncSession, rules: Rules, beast_ids: Sequence[int]) -> set[int]:
    if not beast_ids:
        return set()
    profiles = {row.beast_entity_id: row for row in await session.scalars(select(BeastProfileRow).where(BeastProfileRow.beast_entity_id.in_(beast_ids)))}
    entities = await session.scalars(select(EntityRow).where(EntityRow.id.in_(beast_ids)).order_by(EntityRow.id))
    floor = rules.mortal_agents.creature_min_intelligence
    return {entity.id for entity in entities if creature_mind(entity, profiles.get(entity.id)) >= floor}


async def speaker_lines(session: AsyncSession, rules: Rules, *, query: str = "", group: SpeakerGroup | None = None, dead: bool = False) -> list[SpeakerLine]:
    gods = [] if group not in (None, SpeakerGroup.SONS, SpeakerGroup.FOREIGN_GODS) else await god_lines(session, query)
    types = sorted(entity_type for entity_type, found in ENTITY_GROUPS.items() if group is None or found is group)
    entities = await entity_lines(session, rules, query, types) if types else []
    lines = [line for line in [*gods, *entities] if (group is None or line.group is group) and (dead or not line.dead)]
    return sorted(lines, key=lambda line: (GROUP_ORDER[line.group], line.name.casefold(), line.node_id))


async def world_name(session: AsyncSession, world_id: int | None) -> str:
    world = await session.get(WorldRow, world_id) if world_id is not None else None
    return world.name if world is not None else ""


async def tongues_of(session: AsyncSession, speaker: Speaker) -> list[str]:
    if isinstance(speaker.node, EntityRow):
        targets = [bond.target_node_id for bond in await BondRepository(session).outgoing(speaker.node_id, BondKind.SPEAKS)]
    else:
        targets = list(
            await session.scalars(
                select(DivineTongueRow.language_entity_id).where(DivineTongueRow.god_node_id == speaker.node_id).order_by(DivineTongueRow.language_entity_id)
            )
        )
    if not targets:
        return []
    return list(await session.scalars(select(EntityRow.name).where(EntityRow.id.in_(targets)).order_by(EntityRow.id)))


async def ending_line(session: AsyncSession, entity_id: int, epoch: int | None) -> str:
    if epoch is None:
        return ""
    lines = await ChronicleRepository(session).mentioning(entity_id, ENDING_LINES)
    return next((line.text for line in lines if line.epoch == epoch), "")


async def death_of(session: AsyncSession, speaker: Speaker) -> Death | None:
    if not speaker.dead:
        return None
    node = speaker.node
    if isinstance(node, SonRow):
        return Death(node.death_epoch, son_cause=node.death_cause)
    if isinstance(node, ForeignGodRow):
        return Death(node.death_epoch)
    profile = await session.get(MortalProfileRow, node.id)
    cause = profile.cause_of_death if profile is not None else None
    return Death(node.end_epoch, mortal_cause=cause, line=await ending_line(session, node.id, node.end_epoch))


async def speaker_card(session: AsyncSession, speaker: Speaker) -> SpeakerCard:
    node = speaker.node
    death = await death_of(session, speaker)
    languages = await tongues_of(session, speaker)
    if isinstance(node, EntityRow):
        place = await session.get(EntityRow, node.location_id) if node.location_id is not None else None
        patron_id = await BondRepository(session).patron(node.id)
        patron = await session.get(NodeRow, patron_id) if patron_id is not None else None
        return SpeakerCard(
            speaker,
            place_name=place.name if place is not None else "",
            world_name=await world_name(session, node.world_id),
            patron_name=patron.name if patron is not None else "",
            languages=languages,
            death=death,
        )
    world_id = node.current_world_id if isinstance(node, SonRow) else node.world_id
    return SpeakerCard(speaker, world_name=await world_name(session, world_id), faith=node.faith, languages=languages, death=death)
