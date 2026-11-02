from collections.abc import Mapping, Sequence

from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.war import WarCause
from aerona.engine.context import TickContext
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.faith import FaithIndex
from aerona.engine.primitives.prosperity import add_prosperity
from aerona.engine.primitives.queries import BondIndex, canon, flags_by_entity
from aerona.engine.primitives.stats import shift_stat, stat_or
from aerona.engine.services.community_relations import change_relation, relation
from aerona.engine.services.war import declare_war
from aerona.rules.registry import Rules

OWNER_BOND_KINDS = (BondKind.BUILT, BondKind.RULES, BondKind.OWNS)


def deserves_wonder(rules: Rules, work: EntityRow) -> bool:
    settings = rules.wonders
    return stat_or(work, "splendor", 0) >= settings.min_splendor or work.power_level >= settings.min_power


def wonder_owner(work: EntityRow, entities: Mapping[int, EntityRow], bonds: BondIndex) -> EntityRow | None:
    location = entities.get(work.location_id) if work.location_id is not None else None
    if location is not None and location.entity_type in COMMUNITY_TYPES:
        return location
    for kind in OWNER_BOND_KINDS:
        for bond in bonds.incoming(work.id, kind):
            owner = entities.get(bond.source_node_id)
            if owner is not None:
                return owner
    return None


async def promote_wonders(ctx: TickContext, works: Sequence[EntityRow], wonders: set[int]) -> int:
    repository = EntityRepository(ctx.session)
    promoted = 0
    for work in works:
        if work.id in wonders or not deserves_wonder(ctx.rules, work):
            continue
        await repository.add_flag(work.id, EntityFlag.WONDER, ctx.epoch)
        wonders.add(work.id)
        promoted += 1
        await note(
            ctx,
            f"{work.name} joined the wonders of the world; pilgrims and envious eyes from distant lands turn to it.",
            key="wonders.promoted",
            ids=[work.id],
            kind=ChronicleKind.CONSTRUCTION,
        )
    return promoted


async def envy(ctx: TickContext, work: EntityRow, owner: EntityRow, neighbours: Sequence[EntityRow]) -> int:
    settings = ctx.rules.wonders
    rng = ctx.rng(f"envy.{work.id}")
    wars = 0
    for neighbour in neighbours:
        current = await relation(ctx.session, ctx.rules, neighbour.id, owner.id)
        if current >= settings.envy_threshold:
            continue
        current = await change_relation(ctx, neighbour.id, owner.id, -settings.envy_relation_loss)
        if current > -settings.war_relation or not rng.chance(settings.envy_war_chance):
            continue
        if await declare_war(ctx, neighbour.id, owner.id, f"for {work.name}", cause=WarCause.ENVY):
            wars += 1
            await note(
                ctx,
                f"{neighbour.name} coveted the {work.name} wonder and declared {owner.name} its enemy.",
                key="wonders.envy_war",
                ids=[neighbour.id, owner.id, work.id],
                feed=FeedCategory.WAR,
                kind=ChronicleKind.WORLD,
            )
    return wars


async def wonders(ctx: TickContext) -> None:
    session = ctx.session
    settings = ctx.rules.wonders
    entities = {entity.id: entity for entity in await canon(session)}
    works = [entity for entity in entities.values() if entity.entity_type is EntityType.STRUCTURE]
    flagged = await flags_by_entity(session, EntityFlag.WONDER)
    ctx.count("promoted", await promote_wonders(ctx, works, flagged))
    bonds = await BondIndex.load(session, OWNER_BOND_KINDS)
    atlas = await RegionAtlas.load(session)
    faith = await FaithIndex.load(session)
    communities = [entity for entity in entities.values() if entity.entity_type in COMMUNITY_TYPES]
    wars = 0
    for work in works:
        owner = wonder_owner(work, entities, bonds) if work.id in flagged else None
        if owner is None or owner.status is not EntityStatus.CANON:
            continue
        add_prosperity(ctx.rules, owner, settings.prosperity)
        shift_stat(owner, "piety", settings.faith)
        patron = faith.living_patron_son(owner.id)
        if patron is not None:
            patron.fame += settings.renown
        neighbours = [other for other in communities if other.id != owner.id and atlas.adjacent(other.id, owner.id)]
        wars += await envy(ctx, work, owner, neighbours)
    ctx.count("envy_wars", wars)


PHASES = (Phase("wonders", wonders),)
