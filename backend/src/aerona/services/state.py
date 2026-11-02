from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.stats import EXISTENCE_BAND_LABELS, existence_band_effect
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.agency import ActionRecordRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmos import CosmosRow, CreatorRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.epochs import EpochRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.lore import MessageRow, ThreadRow
from aerona.db.tables.meta import ImageRow
from aerona.db.tables.sons import SonPowerRow, SonRelationRow, SonRow
from aerona.domain.enums.agent import MessageIntent
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ThreadStatus
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.son import ExistenceBand, SonStatus
from aerona.domain.models.records import EpochStatsData
from aerona.engine.gods.progress import StarRequirement, power_ceiling, son_max_essence, son_max_hp
from aerona.events.change_feed import ChangeSet, TrackedTable
from aerona.rules.registry import Rules
from aerona.services import sons as son_rules
from aerona.services.images.records import cover_of
from aerona.services.statistics import pulse

LAST_ACTION_PREVIEW = 160


@dataclass(frozen=True)
class SonCard:
    last_action: str | None
    last_action_epoch: int | None
    last_words: str | None
    reputation: str | None
    best_friend: tuple[int, str, int] | None
    worst_rival: tuple[int, str, int] | None


@dataclass(frozen=True)
class SonView:
    son: SonRow
    powers: list[SonPowerRow]
    max_hp: int
    max_essence: int
    action_points: int
    power_cap: int
    band: ExistenceBand
    band_label: str
    band_effect: str
    band_action_loss: int
    unlocked_powers: int
    next_star: StarRequirement | None
    ascension: son_rules.AscensionRequirement | None
    cover: str | None
    card: SonCard


@dataclass(frozen=True)
class WorldBrief:
    id: int
    name: str
    world_type: str
    discovery: str
    leakage: int


@dataclass(frozen=True)
class StateSnapshot:
    cosmos: CosmosRow | None
    creator: CreatorRow | None
    creator_cover: str | None
    world_cover: str | None
    sons: list[SonView] = field(default_factory=list)
    counts: dict[EntityType, int] = field(default_factory=dict)
    prayers_pending: int = 0
    relations: list[SonRelationRow] = field(default_factory=list)
    worlds: list[WorldBrief] = field(default_factory=list)
    foreign_god_count: int = 0
    pending_son_ids: list[int] = field(default_factory=list)
    covenants: list[tuple[int, int, str | None]] = field(default_factory=list)
    open_threads: list[ThreadRow] = field(default_factory=list)
    last_epoch: EpochRow | None = None
    image_count: int = 0
    promptless_count: int = 0
    pulse: EpochStatsData | None = None


async def _card(session: AsyncSession, son: SonRow, relations: list[SonRelationRow], names: dict[int, str]) -> SonCard:
    action = await session.scalar(select(ActionRecordRow).where(ActionRecordRow.actor_node_id == son.id).order_by(ActionRecordRow.id.desc()).limit(1))
    words = await session.scalar(
        select(MessageRow.text).where(MessageRow.sender_node_id == son.id, MessageRow.intent != MessageIntent.PRAYER).order_by(MessageRow.id.desc()).limit(1)
    )
    own = [(row.son_b_id if row.son_a_id == son.id else row.son_a_id, row.value) for row in relations if son.id in (row.son_a_id, row.son_b_id)]
    friends = sorted((item for item in own if item[1] > 0), key=lambda item: -item[1])
    rivals = sorted((item for item in own if item[1] < 0), key=lambda item: item[1])
    return SonCard(
        last_action=(action.summary or "")[:LAST_ACTION_PREVIEW] or None if action is not None else None,
        last_action_epoch=action.epoch if action is not None else None,
        last_words=words,
        reputation=son.reputation_label.value if son.reputation_label is not None else None,
        best_friend=(friends[0][0], names.get(friends[0][0], ""), friends[0][1]) if friends else None,
        worst_rival=(rivals[0][0], names.get(rivals[0][0], ""), rivals[0][1]) if rivals else None,
    )


async def decorate_son(session: AsyncSession, rules: Rules, son: SonRow, relations: list[SonRelationRow], names: dict[int, str]) -> SonView:
    powers = await SonRepository(session).powers(son.id)
    band = son_rules.band(rules, son)
    return SonView(
        son=son,
        powers=powers,
        max_hp=son_max_hp(rules, son),
        max_essence=son_max_essence(rules, son),
        action_points=son_rules.action_points(rules, son, powers),
        power_cap=power_ceiling(rules, son),
        band=band,
        band_label=EXISTENCE_BAND_LABELS[band],
        band_effect=existence_band_effect(rules, band),
        band_action_loss=son_rules.band_action_loss(rules, son, powers),
        unlocked_powers=len(son_rules.unlocked_powers(rules, son, powers)),
        next_star=son_rules.next_star(rules, son),
        ascension=son_rules.ascension(rules, son),
        cover=await cover_of(session, son.id),
        card=await _card(session, son, relations, names),
    )


async def son_views(session: AsyncSession, rules: Rules) -> list[SonView]:
    all_sons = await SonRepository(session).all_sons()
    relations = list(await session.scalars(select(SonRelationRow)))
    names = {son.id: son.name for son in all_sons}
    return [await decorate_son(session, rules, son, relations, names) for son in all_sons]


async def _counts(session: AsyncSession) -> dict[EntityType, int]:
    rows = await session.execute(select(EntityRow.entity_type, func.count()).where(EntityRow.status == EntityStatus.CANON).group_by(EntityRow.entity_type))
    return {entity_type: int(count) for entity_type, count in rows}


async def snapshot(session: AsyncSession, rules: Rules) -> StateSnapshot:
    repository = CosmosRepository(session)
    cosmos = await repository.get()
    if cosmos is None:
        return StateSnapshot(cosmos=None, creator=None, creator_cover=None, world_cover=None)
    creator = await repository.creator()
    worlds = list(await session.scalars(select(WorldRow).order_by(WorldRow.id)))
    living = await son_views(session, rules)
    prayers = await session.scalar(
        select(func.count())
        .select_from(MessageRow)
        .where(
            MessageRow.recipient_node_id == (creator.id if creator else -1),
            MessageRow.intent == MessageIntent.PRAYER,
            MessageRow.answered.is_(False),
        )
    )
    covenant_rows = await session.scalars(
        select(BondRow)
        .join(SonRow, SonRow.id == BondRow.source_node_id)
        .where(BondRow.kind == BondKind.ALLY, BondRow.state == BondState.ACTIVE)
        .order_by(BondRow.id)
    )
    son_ids = {view.son.id for view in living}
    covenants = [(bond.source_node_id, bond.target_node_id, bond.description) for bond in covenant_rows if bond.target_node_id in son_ids]
    last_epoch = await session.scalar(select(EpochRow).where(EpochRow.epoch < cosmos.epoch).order_by(EpochRow.epoch.desc()).limit(1))
    promptless = await session.scalar(
        select(func.count()).select_from(EntityRow).where(EntityRow.status == EntityStatus.CANON, EntityRow.image_prompt.is_(None))
    )
    return StateSnapshot(
        cosmos=cosmos,
        creator=creator,
        creator_cover=await cover_of(session, creator.id) if creator else None,
        world_cover=await cover_of(session, cosmos.primary_world_id) if cosmos.primary_world_id else None,
        sons=living,
        counts=await _counts(session),
        prayers_pending=int(prayers or 0),
        relations=list(await session.scalars(select(SonRelationRow).order_by(SonRelationRow.son_a_id, SonRelationRow.son_b_id))),
        worlds=[WorldBrief(world.id, world.name, world.world_type.value, world.discovery.value, world.leakage) for world in worlds],
        foreign_god_count=int(await session.scalar(select(func.count()).select_from(ForeignGodRow)) or 0),
        pending_son_ids=[
            view.son.id for view in living if view.son.status is SonStatus.ACTIVE and view.son.last_acted_epoch < cosmos.epoch and view.action_points > 0
        ],
        covenants=covenants,
        open_threads=list(await session.scalars(select(ThreadRow).where(ThreadRow.status == ThreadStatus.OPEN).order_by(ThreadRow.id.desc()))),
        last_epoch=last_epoch,
        image_count=int(await session.scalar(select(func.count()).select_from(ImageRow)) or 0),
        promptless_count=int(promptless or 0),
        pulse=await pulse(session),
    )


@dataclass(frozen=True)
class ChangeDigest:
    full: bool
    version: str
    entities: list[EntityRow] = field(default_factory=list)
    removed_entity_ids: list[int] = field(default_factory=list)
    sons: list[SonView] = field(default_factory=list)
    removed_son_ids: list[int] = field(default_factory=list)
    new_chronicle_lines: int = 0
    bonds_changed: bool = False
    cosmos_changed: bool = False
    worlds_changed: bool = False
    relations_changed: bool = False
    foreign_god_ids: list[int] = field(default_factory=list)


def _ids(values: tuple[str, ...]) -> list[int]:
    return [int(value) for value in values if value.isdigit()]


async def change_digest(session: AsyncSession, rules: Rules, changes: ChangeSet) -> ChangeDigest:
    if changes.full:
        return ChangeDigest(full=True, version=changes.version)
    changed_entities = _ids(changes.changed(TrackedTable.ENTITIES))
    entities = list(await session.scalars(select(EntityRow).where(EntityRow.id.in_(changed_entities)).order_by(EntityRow.id)))
    rejected = [entity.id for entity in entities if entity.status is EntityStatus.REJECTED]
    changed_sons = _ids(changes.changed(TrackedTable.SONS))
    relations = list(await session.scalars(select(SonRelationRow)))
    names = {son_id: name for son_id, name in await session.execute(select(SonRow.id, SonRow.name))}
    sons = [await decorate_son(session, rules, son, relations, names) for son in await session.scalars(select(SonRow).where(SonRow.id.in_(changed_sons)))]
    cosmic_tables = (TrackedTable.WORLDS, TrackedTable.STARS, TrackedTable.FOREIGN_GODS, TrackedTable.ROUTES, TrackedTable.JOURNEYS)
    return ChangeDigest(
        full=False,
        version=changes.version,
        entities=[entity for entity in entities if entity.status is not EntityStatus.REJECTED],
        removed_entity_ids=_ids(changes.deleted(TrackedTable.ENTITIES)) + rejected,
        sons=sons,
        removed_son_ids=_ids(changes.deleted(TrackedTable.SONS)),
        new_chronicle_lines=len(changes.changed(TrackedTable.CHRONICLE)),
        bonds_changed=changes.touched(TrackedTable.BONDS),
        cosmos_changed=changes.touched(TrackedTable.COSMOS) or changes.touched(TrackedTable.CREATOR),
        worlds_changed=any(changes.touched(table) for table in cosmic_tables),
        relations_changed=changes.touched(TrackedTable.SON_RELATIONS),
        foreign_god_ids=_ids(changes.changed(TrackedTable.FOREIGN_GODS)) + _ids(changes.deleted(TrackedTable.FOREIGN_GODS)),
    )
