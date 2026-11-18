from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy import ColumnElement, Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.schemas.cards import (
    CardOrder,
    CardQuery,
    CharacterCard,
    CharacterCardAbility,
    CharacterCardNote,
    CharacterCardPage,
    CharacterCardStat,
    CharacterDeckCount,
    CharacterRarityCount,
)
from aerona.catalog.entity_types import ENTITY_TYPES
from aerona.catalog.rarities import entity_power_band, entity_rarity
from aerona.catalog.stats import STATS, max_essence, max_hp
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodPowerRow, ForeignGodRow
from aerona.db.tables.sons import SonPowerRow, SonRow
from aerona.db.tables.stat_columns import StatColumns
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.foreign_god import ForeignGodStatus
from aerona.domain.enums.limits import PERCENT_MAX
from aerona.domain.enums.node import NodeKind
from aerona.domain.enums.rarity import RARITY_ORDER, Rarity
from aerona.domain.enums.son import SonStatus
from aerona.domain.models.profiles import ExistenceProfile, Personality
from aerona.domain.models.stats import STAT_CEILING
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules
from aerona.services.images.records import covers_of

CHARACTER_TYPES: tuple[EntityType, ...] = (
    EntityType.MORTAL,
    EntityType.BEAST,
    EntityType.SPIRIT,
    EntityType.OUTER_BEING,
    EntityType.COSMIC_BEING,
)
ENDED_ENTITY = frozenset({EntityStatus.DEAD, EntityStatus.DESTROYED})
HEADLINE_SIZE = 2


@dataclass(frozen=True)
class GodCard:
    card: CharacterCard
    rank: tuple[int, int, int]
    haystack: str


def _stat_line(key: str, label: str, value: int | None, maximum: int | None) -> CharacterCardStat | None:
    if value is None:
        return None
    return CharacterCardStat(key=key, label=label, value=value, maximum=maximum)


def _present(lines: Iterable[CharacterCardStat | None]) -> list[CharacterCardStat]:
    return [line for line in lines if line is not None]


def _god_stats(row: StatColumns) -> list[CharacterCardStat]:
    return _present(_stat_line(spec.stat.value, spec.label, getattr(row, spec.stat.value), STAT_CEILING) for spec in STATS.values())


def _persona_notes(personality: Personality | None, existence: ExistenceProfile | None) -> list[CharacterCardNote]:
    pairs: list[tuple[str, str]] = []
    if personality is not None:
        pairs += [
            ("Appearance", personality.appearance),
            ("Temperament", personality.temperament),
            ("Obsession", personality.obsession),
            ("Fear", personality.fear),
            ("Manner of speech", personality.speech_style),
            ("Secret", personality.secret),
        ]
    if existence is not None:
        pairs += [("Nature", existence.nature), ("Manifestation", existence.manifestation), ("True name", existence.true_name)]
    return [CharacterCardNote(label=label, text=text.strip()) for label, text in pairs if text.strip()]


def _flavor(*texts: str | None) -> str:
    return next((text.strip() for text in texts if text and text.strip()), "")


def _abilities(powers: Iterable[tuple[str, str]]) -> list[CharacterCardAbility]:
    return [CharacterCardAbility(name=name, text=text) for name, text in powers]


def _creator_card(creator: CreatorRow) -> CharacterCard:
    moods = _present(
        (
            _stat_line("mood_contentment", "Contentment", creator.mood_contentment, PERCENT_MAX),
            _stat_line("mood_anger", "Anger", creator.mood_anger, PERCENT_MAX),
            _stat_line("mood_interest", "Interest", creator.mood_interest, PERCENT_MAX),
            _stat_line("mood_loneliness", "Loneliness", creator.mood_loneliness, PERCENT_MAX),
            _stat_line("mood_temperament", "Temperament", creator.mood_temperament, PERCENT_MAX),
        )
    )
    sides = (("Appearance", creator.appearance), ("Temperament", creator.temperament))
    notes = [CharacterCardNote(label=label, text=text.strip()) for label, text in sides if text and text.strip()]
    return CharacterCard(
        node_id=creator.id,
        node_kind=NodeKind.CREATOR,
        entity_type=None,
        name=creator.name,
        title=creator.title,
        subtype=None,
        rarity=None,
        stars=None,
        power_level=None,
        level=None,
        xp=None,
        domains=[],
        world_id=None,
        cover=None,
        flavor=_flavor(creator.temperament, creator.appearance),
        headline=_present((_stat_line("essence", "Essence", creator.essence, None),)),
        stats=moods,
        abilities=[],
        notes=notes,
        fallen=False,
        born_epoch=None,
        ended_epoch=None,
    )


def _son_card(son: SonRow, rules: Rules, powers: list[tuple[str, str]]) -> CharacterCard:
    life_cap = max_hp(rules, son.endurance)
    essence_cap = max_essence(rules, son.might)
    vitals = _present(
        (
            _stat_line("hp", "Life", son.hp, life_cap),
            _stat_line("essence", "Essence", son.essence, essence_cap),
            _stat_line("existence", "Existence", son.existence, PERCENT_MAX),
            _stat_line("faith", "Faith", son.faith, None),
            _stat_line("fame", "Fame", son.fame, None),
        )
    )
    return CharacterCard(
        node_id=son.id,
        node_kind=NodeKind.SON,
        entity_type=None,
        name=son.name,
        title=son.title,
        subtype=None,
        rarity=son.rarity,
        stars=son.stars,
        power_level=None,
        level=son.level,
        xp=son.xp,
        domains=[son.domain_primary, son.domain_secondary],
        world_id=son.current_world_id,
        cover=None,
        flavor=_flavor(son.personality.temperament, son.personality.appearance),
        headline=_present((_stat_line("might", "Might", son.might, STAT_CEILING), _stat_line("hp", "Life", son.hp, life_cap))),
        stats=_god_stats(son) + vitals,
        abilities=_abilities(powers),
        notes=_persona_notes(son.personality, son.existence_profile),
        fallen=son.status is SonStatus.DEAD,
        born_epoch=son.birth_epoch,
        ended_epoch=son.death_epoch,
    )


def _foreign_god_card(god: ForeignGodRow, powers: list[tuple[str, str]]) -> CharacterCard:
    domains: list[Domain] = [god.domain_primary] + ([god.domain_secondary] if god.domain_secondary is not None else [])
    standing = _present((_stat_line("power", "Power", god.power, PERCENT_MAX), _stat_line("faith", "Faith", god.faith, None)))
    return CharacterCard(
        node_id=god.id,
        node_kind=NodeKind.FOREIGN_GOD,
        entity_type=None,
        name=god.name,
        title=god.title,
        subtype=None,
        rarity=None,
        stars=None,
        power_level=None,
        level=None,
        xp=None,
        domains=domains,
        world_id=god.world_id,
        cover=None,
        flavor=_flavor(god.description, god.personality.temperament if god.personality else None),
        headline=_present((_stat_line("might", "Might", god.might, STAT_CEILING), _stat_line("power", "Power", god.power, PERCENT_MAX))),
        stats=_god_stats(god) + standing,
        abilities=_abilities(powers),
        notes=_persona_notes(god.personality, god.existence_profile),
        fallen=god.status is ForeignGodStatus.DEAD,
        born_epoch=god.created_epoch,
        ended_epoch=god.death_epoch,
    )


def _entity_card(entity: EntityRow, rules: Rules) -> CharacterCard:
    spec = ENTITY_TYPES[entity.entity_type]
    stat_lines = _present(_stat_line(field.key, field.label, stat(entity, field.key), field.bounds(rules)[1]) for field in spec.stats)
    return CharacterCard(
        node_id=entity.id,
        node_kind=NodeKind.ENTITY,
        entity_type=entity.entity_type,
        name=entity.name,
        title=entity.title,
        subtype=entity.subtype,
        rarity=entity_rarity(rules, entity.power_level),
        stars=None,
        power_level=entity.power_level,
        level=None,
        xp=None,
        domains=[entity.domain] if entity.domain is not None else [],
        world_id=entity.world_id,
        cover=None,
        flavor=_flavor(entity.description),
        headline=stat_lines[:HEADLINE_SIZE],
        stats=stat_lines,
        abilities=[],
        notes=[],
        fallen=entity.status in ENDED_ENTITY,
        born_epoch=entity.birth_epoch,
        ended_epoch=entity.end_epoch,
    )


def _haystack(*parts: str | None) -> str:
    return " ".join(part for part in parts if part).casefold()


async def _god_cards(session: AsyncSession, rules: Rules) -> list[GodCard]:
    cards: list[GodCard] = []
    creator = await CosmosRepository(session).creator()
    if creator is not None:
        card = _creator_card(creator)
        cards.append(GodCard(card, (0, 0, 0), _haystack(card.name, card.title, card.flavor)))
    sons = list(await session.scalars(select(SonRow)))
    son_powers: dict[int, list[tuple[str, str]]] = {}
    for row in await session.scalars(select(SonPowerRow).order_by(SonPowerRow.son_id, SonPowerRow.slot)):
        son_powers.setdefault(row.son_id, []).append((row.name, row.description))
    for son in sons:
        card = _son_card(son, rules, son_powers.get(son.id, []))
        cards.append(GodCard(card, (1, -son.rarity.rank, -son.level), _haystack(card.name, card.title, card.flavor)))
    god_powers: dict[int, list[tuple[str, str]]] = {}
    for power in await session.scalars(select(ForeignGodPowerRow).order_by(ForeignGodPowerRow.god_id, ForeignGodPowerRow.slot)):
        god_powers.setdefault(power.god_id, []).append((power.name, power.description))
    for god in await session.scalars(select(ForeignGodRow)):
        card = _foreign_god_card(god, god_powers.get(god.id, []))
        cards.append(GodCard(card, (2, -god.power, 0), _haystack(card.name, card.title, card.flavor)))
    return cards


def _god_matches(god: GodCard, query: CardQuery, *, deck: bool, rarity: bool = True) -> bool:
    card = god.card
    if deck and query.entity_type is not None:
        return False
    if deck and query.node_kind is not None and card.node_kind is not query.node_kind:
        return False
    if rarity and query.rarity is not None and card.rarity is not query.rarity:
        return False
    if query.world_id is not None and card.world_id != query.world_id:
        return False
    if query.fallen is not None and card.fallen is not query.fallen:
        return False
    needle = (query.q or "").strip().casefold()
    return not needle or needle in god.haystack


def _god_order(cards: list[GodCard], order: CardOrder) -> list[GodCard]:
    if order is CardOrder.NAME:
        return sorted(cards, key=lambda god: (god.card.name.casefold(), god.card.node_id))
    if order is CardOrder.NEWEST:
        return sorted(cards, key=lambda god: (-(god.card.born_epoch if god.card.born_epoch is not None else -1), god.card.node_id))
    return sorted(cards, key=lambda god: (god.rank, god.card.name.casefold(), god.card.node_id))


def _entity_filters(query: CardQuery, rules: Rules, *, deck: bool, rarity: bool = True) -> list[ColumnElement[bool]] | None:
    if deck and query.node_kind is not None and query.node_kind is not NodeKind.ENTITY:
        return None
    if deck and query.entity_type is not None and query.entity_type not in CHARACTER_TYPES:
        return None
    types = [query.entity_type] if deck and query.entity_type is not None else list(CHARACTER_TYPES)
    conditions: list[ColumnElement[bool]] = [EntityRow.entity_type.in_(types), EntityRow.status != EntityStatus.REJECTED]
    if rarity and query.rarity is not None:
        low, high = entity_power_band(rules, query.rarity)
        conditions.append(EntityRow.power_level >= low)
        if high is not None:
            conditions.append(EntityRow.power_level <= high)
    if query.world_id is not None:
        conditions.append(EntityRow.world_id == query.world_id)
    if query.fallen is not None:
        ended = EntityRow.status.in_(list(ENDED_ENTITY))
        conditions.append(ended if query.fallen else ~ended)
    needle = (query.q or "").strip()
    if needle:
        pattern = f"%{needle}%"
        columns = (EntityRow.name, EntityRow.title, EntityRow.subtype, EntityRow.description)
        conditions.append(or_(*(column.ilike(pattern) for column in columns)))
    return conditions


def _entity_order(statement: Select[EntityRow], order: CardOrder) -> Select[EntityRow]:
    if order is CardOrder.NAME:
        return statement.order_by(EntityRow.name, EntityRow.id)
    if order is CardOrder.NEWEST:
        return statement.order_by(EntityRow.birth_epoch.desc(), EntityRow.id.desc())
    return statement.order_by(EntityRow.power_level.desc(), EntityRow.importance.desc().nulls_last(), EntityRow.id)


async def _deck_counts(session: AsyncSession, gods: list[GodCard], query: CardQuery, rules: Rules) -> list[CharacterDeckCount]:
    tally: dict[NodeKind, int] = {}
    for god in gods:
        if _god_matches(god, query, deck=False):
            tally[god.card.node_kind] = tally.get(god.card.node_kind, 0) + 1
    decks = [CharacterDeckCount(node_kind=kind, entity_type=None, total=total) for kind, total in tally.items()]
    conditions = _entity_filters(query, rules, deck=False)
    if conditions is not None:
        rows = await session.execute(select(EntityRow.entity_type, func.count()).where(*conditions).group_by(EntityRow.entity_type))
        found = {entity_type: int(total) for entity_type, total in rows}
        present = [entity_type for entity_type in CHARACTER_TYPES if found.get(entity_type)]
        decks += [CharacterDeckCount(node_kind=NodeKind.ENTITY, entity_type=entity_type, total=found[entity_type]) for entity_type in present]
    return decks


async def _rarity_counts(session: AsyncSession, gods: list[GodCard], query: CardQuery, rules: Rules) -> list[CharacterRarityCount]:
    tally: dict[Rarity, int] = {}
    for god in gods:
        if god.card.rarity is not None and _god_matches(god, query, deck=True, rarity=False):
            tally[god.card.rarity] = tally.get(god.card.rarity, 0) + 1
    conditions = _entity_filters(query, rules, deck=True, rarity=False)
    if conditions is not None:
        rows = await session.execute(select(EntityRow.power_level, func.count()).where(*conditions).group_by(EntityRow.power_level))
        for power_level, total in rows:
            tier = entity_rarity(rules, power_level)
            tally[tier] = tally.get(tier, 0) + int(total)
    return [CharacterRarityCount(rarity=rarity, total=tally.get(rarity, 0)) for rarity in RARITY_ORDER]


async def _attach_covers(session: AsyncSession, cards: list[CharacterCard]) -> list[CharacterCard]:
    covers = await covers_of(session, (card.node_id for card in cards))
    return [card.model_copy(update={"cover": covers.get(card.node_id)}) for card in cards]


async def _latest_node_id(session: AsyncSession, gods: list[GodCard]) -> int | None:
    newest_entity = await session.scalar(select(func.max(EntityRow.id)).where(EntityRow.entity_type.in_(CHARACTER_TYPES)))
    found = [god.card.node_id for god in gods] + ([int(newest_entity)] if newest_entity is not None else [])
    return max(found, default=None)


async def character_cards(session: AsyncSession, rules: Rules, query: CardQuery) -> CharacterCardPage:
    gods = await _god_cards(session, rules)
    chosen = _god_order([god for god in gods if _god_matches(god, query, deck=True)], query.order)
    conditions = _entity_filters(query, rules, deck=True)
    entity_total = 0
    if conditions is not None:
        entity_total = int(await session.scalar(select(func.count()).select_from(EntityRow).where(*conditions)) or 0)
    taken = [god.card for god in chosen[query.offset : query.offset + query.limit]]
    room = query.limit - len(taken)
    if conditions is not None and room > 0:
        skip = max(0, query.offset - len(chosen))
        statement = _entity_order(select(EntityRow).where(*conditions), query.order).offset(skip).limit(room)
        taken += [_entity_card(entity, rules) for entity in await session.scalars(statement)]
    return CharacterCardPage(
        items=await _attach_covers(session, taken),
        total=len(chosen) + entity_total,
        offset=query.offset,
        limit=query.limit,
        decks=await _deck_counts(session, gods, query, rules),
        rarities=await _rarity_counts(session, gods, query, rules),
        latest_node_id=await _latest_node_id(session, gods),
    )
