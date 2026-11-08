from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import ThreadLinkRow, ThreadRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ThreadStatus
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.war import HeroQuestKind
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.queries import BondIndex
from aerona.engine.primitives.stats import stat_or
from aerona.engine.services.sides import SideIndex
from aerona.rules.registry import Rules

THREAD_EXCLUDED_TYPES = frozenset({EntityType.LANGUAGE, EntityType.LAW})


@dataclass(frozen=True)
class QuestOption:
    kind: HeroQuestKind
    target_id: int
    weight: float
    description: str
    thread_id: int | None = None


@dataclass(frozen=True)
class QuestWorld:
    entities: Mapping[int, EntityRow]
    bonds: BondIndex
    atlas: RegionAtlas
    sides: SideIndex
    lost: set[int]
    feuds: set[tuple[int, int]]
    threads: Sequence[tuple[ThreadRow, Sequence[int]]]


async def open_threads(session: AsyncSession) -> list[tuple[ThreadRow, list[int]]]:
    threads = list(await session.scalars(select(ThreadRow).where(ThreadRow.status == ThreadStatus.OPEN).order_by(ThreadRow.id)))
    links: dict[int, list[int]] = {thread.id: [] for thread in threads}
    statement = select(ThreadLinkRow.thread_id, ThreadLinkRow.entity_id).where(ThreadLinkRow.thread_id.in_(list(links))).order_by(ThreadLinkRow.entity_id)
    for thread_id, entity_id in await session.execute(statement):
        if entity_id not in links[thread_id]:
            links[thread_id].append(entity_id)
    return [(thread, links[thread.id]) for thread in threads]


def within_reach(rules: Rules, world: QuestWorld, hero: EntityRow, target: EntityRow) -> bool:
    hops = world.atlas.hops(hero.id, target.id)
    return hops is not None and hops <= rules.heroes.quest_max_distance


def hunt_options(rules: Rules, world: QuestWorld, hero: EntityRow) -> list[QuestOption]:
    killed = {bond.target_node_id for bond in world.bonds.outgoing(hero.id, BondKind.KILLED)}
    return [
        QuestOption(HeroQuestKind.HUNT, species.id, rules.heroes.quest_weight_hunt, f"to hunt {species.name}")
        for species in world.entities.values()
        if species.entity_type is EntityType.SPECIES
        and stat_or(species, "danger", 0) >= rules.heroes.hunt_quest_min_danger
        and species.id not in killed
        and within_reach(rules, world, hero, species)
    ]


def thread_options(rules: Rules, world: QuestWorld, hero: EntityRow, side: int | None) -> list[QuestOption]:
    if side is None:
        return []
    home = world.atlas.top_region(hero.id)
    options: list[QuestOption] = []
    for thread, linked in world.threads:
        target = next(
            (
                world.entities[item]
                for item in linked
                if item in world.entities
                and item != hero.id
                and world.entities[item].entity_type not in THREAD_EXCLUDED_TYPES
                and world.entities[item].world_id == hero.world_id
            ),
            None,
        )
        if target is None:
            continue
        nearby = home is not None and any(world.atlas.top_region(item) == home for item in linked)
        if side in linked or nearby:
            description = f"to pursue the secret of the open story around {target.name}"
            options.append(QuestOption(HeroQuestKind.THREAD, target.id, rules.heroes.quest_weight_thread, description, thread.id))
    return options


def relic_options(rules: Rules, world: QuestWorld, hero: EntityRow) -> list[QuestOption]:
    settings = rules.heroes
    options: list[QuestOption] = []
    for item in world.entities.values():
        if item.entity_type is not EntityType.ITEM or world.bonds.incoming(item.id, BondKind.OWNS) or not within_reach(rules, world, hero, item):
            continue
        weight = settings.quest_weight_lost_item + (settings.quest_weight_strong_item_bonus if item.power_level >= settings.quest_strong_item_power else 0)
        options.append(QuestOption(HeroQuestKind.RELIC, item.id, weight, f"to find the lost {item.name}"))
    return options


def knowledge_options(rules: Rules, world: QuestWorld, hero: EntityRow) -> list[QuestOption]:
    return [
        QuestOption(HeroQuestKind.KNOWLEDGE, item.id, rules.heroes.quest_weight_lost_knowledge, f"to search the ruins for the lost {item.name} knowledge")
        for item in world.entities.values()
        if item.entity_type is EntityType.KNOWLEDGE and item.id in world.lost and item.world_id == hero.world_id
    ]


def vengeance_options(rules: Rules, world: QuestWorld, side: int | None) -> list[QuestOption]:
    if side is None:
        return []
    options: list[QuestOption] = []
    for first, second in sorted(world.feuds):
        if side not in (first, second):
            continue
        enemy = world.entities.get(second if first == side else first)
        if enemy is None or enemy.status is not EntityStatus.CANON:
            continue
        victims = world.sides.heroes_of(enemy.id)
        if victims:
            target = victims[0]
            description = f"to avenge the blood feud on {enemy.name} ({target.name})"
            options.append(QuestOption(HeroQuestKind.VENGEANCE, target.id, rules.heroes.quest_weight_vengeance, description))
    return options


def quest_options(rules: Rules, world: QuestWorld, hero: EntityRow) -> list[QuestOption]:
    side = world.sides.side_of(hero)
    return [
        *hunt_options(rules, world, hero),
        *thread_options(rules, world, hero, side),
        *relic_options(rules, world, hero),
        *knowledge_options(rules, world, hero),
        *vengeance_options(rules, world, side),
    ]
