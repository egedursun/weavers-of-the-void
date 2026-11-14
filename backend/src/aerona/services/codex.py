from dataclasses import dataclass, field

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.climate import CLIMATES
from aerona.catalog.knowledge import RESOURCE_MECHANICS
from aerona.catalog.stars import STAR_TYPE_LABELS
from aerona.catalog.travel import TRAVEL_METHODS
from aerona.catalog.worlds import ATMOSPHERE_LABELS, DISCOVERY_LABELS, GRAVITY_LABELS, WORLD_TYPES
from aerona.core.errors import NotFoundError
from aerona.core.grammar import several
from aerona.db.repositories.chronicle import shown_lines
from aerona.db.repositories.nodes import NodeRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.db.tables.epochs import EpochRow, EpochWorldNarrativeRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.routes import RouteRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityFlag, EntityStatus, EntityType
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules

DESCRIPTION_PREVIEW = 160
HEADLINES_PER_WORLD = 4
HEADLINE_LENGTH = 140
MEGAFAUNA = "megafauna"
OUTER_BEING = "Outer Being"
LEAK = "Leak"
TIMES = "\u00d7"
SEPARATOR = " \u00b7 "
HEADLINE_KINDS = frozenset(
    {
        ChronicleKind.WAR,
        ChronicleKind.FATE,
        ChronicleKind.WORLD,
        ChronicleKind.WORLD_BIRTH,
        ChronicleKind.DEATH,
        ChronicleKind.REBELLION,
        ChronicleKind.APOCALYPSE,
        ChronicleKind.HORROR,
        ChronicleKind.CIVILIZATION,
        ChronicleKind.EXPEDITION,
        ChronicleKind.ASCENSION,
        ChronicleKind.LEGENDARY_QUEST,
        ChronicleKind.SKY,
        ChronicleKind.FOREIGN_GOD,
        ChronicleKind.COSMIC,
    }
)


@dataclass(frozen=True)
class Danger:
    id: int | None
    name: str
    reason: str


@dataclass(frozen=True)
class PeopleLine:
    id: int
    name: str
    entity_type: EntityType
    population: int
    language: str | None
    god: str | None


@dataclass(frozen=True)
class ResourceLine:
    id: int
    name: str
    description: str
    mechanics: str | None
    original: bool


@dataclass(frozen=True)
class RouteLine:
    id: int
    target: str
    method: str
    duration: int
    danger: int
    active: bool
    known: bool


@dataclass(frozen=True)
class GodLine:
    id: int
    name: str
    title: str | None
    status: str
    attitude: int


@dataclass(frozen=True)
class TravellerGuide:
    world: WorldRow
    type_label: str
    star: str | None
    star_type: str | None
    parent: str | None
    atmosphere: str
    gravity: str
    discovery: str
    climate: str | None
    climate_epochs_left: int | None
    dangers: list[Danger] = field(default_factory=list)
    peoples: list[PeopleLine] = field(default_factory=list)
    resources: list[ResourceLine] = field(default_factory=list)
    routes: list[RouteLine] = field(default_factory=list)
    foreign_gods: list[GodLine] = field(default_factory=list)
    sky: list[EntityRow] = field(default_factory=list)


@dataclass(frozen=True)
class WorldChronicle:
    world_id: int
    name: str
    event_count: int
    headlines: list[str]
    summary: str | None
    narrative: str | None


@dataclass(frozen=True)
class CosmicEpoch:
    epoch: int
    name: str | None
    summary: str | None
    worlds: list[WorldChronicle]


async def _canon(session: AsyncSession, world_id: int, types: list[EntityType]) -> list[EntityRow]:
    statement = select(EntityRow).where(EntityRow.world_id == world_id, EntityRow.status == EntityStatus.CANON, EntityRow.entity_type.in_(types))
    return list(await session.scalars(statement.order_by(EntityRow.id)))


async def _first_target_name(session: AsyncSession, source_id: int, kind: BondKind) -> str | None:
    statement = select(BondRow.target_node_id).where(BondRow.source_node_id == source_id, BondRow.kind == kind, BondRow.state == BondState.ACTIVE)
    target = await session.scalar(statement.order_by(BondRow.id).limit(1))
    return await NodeRepository(session).name_of(target) if target is not None else None


async def _dangers(session: AsyncSession, rules: Rules, world: WorldRow, complete: bool) -> list[Danger]:
    guide = rules.guide
    shown = None if complete else guide.danger_list
    places = [
        entity for entity in await _canon(session, world.id, [EntityType.REGION, EntityType.PLACE]) if (stat(entity, "danger") or 0) >= guide.dangerous_place
    ]
    places.sort(key=lambda entity: -(stat(entity, "danger") or 0))
    dangers = [Danger(entity.id, entity.name, f"danger {stat(entity, 'danger')}") for entity in places[:shown]]
    species = [entity for entity in await _canon(session, world.id, [EntityType.SPECIES]) if (stat(entity, "danger") or 0) >= guide.dangerous_species]
    species.sort(key=lambda entity: -(stat(entity, "danger") or 0))
    megafauna = set(await session.scalars(select(EntityFlagRow.entity_id).where(EntityFlagRow.flag == EntityFlag.MEGAFAUNA)))
    for entity in species[:shown]:
        suffix = f", {MEGAFAUNA}" if entity.id in megafauna else ""
        dangers.append(Danger(entity.id, entity.name, f"predator (danger {stat(entity, 'danger')}){suffix}"))
    dangers += [Danger(entity.id, entity.name, OUTER_BEING) for entity in await _canon(session, world.id, [EntityType.OUTER_BEING])]
    if world.leakage >= guide.leak_threshold:
        dangers.append(Danger(None, LEAK, f"cosmic leak {world.leakage}/100: minds cloud, species warp"))
    return dangers


async def _peoples(session: AsyncSession, rules: Rules, world_id: int, complete: bool) -> list[PeopleLine]:
    communities = await _canon(session, world_id, list(COMMUNITY_TYPES))
    communities.sort(key=lambda entity: -((stat(entity, "population") or 0) + (stat(entity, "followers") or 0)))
    return [
        PeopleLine(
            entity.id,
            entity.name,
            entity.entity_type,
            (stat(entity, "population") or 0) + (stat(entity, "followers") or 0),
            await _first_target_name(session, entity.id, BondKind.SPEAKS),
            await _first_target_name(session, entity.id, BondKind.WORSHIPS),
        )
        for entity in communities[: None if complete else rules.guide.people_list]
    ]


async def _resources(session: AsyncSession, world_id: int, complete: bool) -> list[ResourceLine]:
    original = set(await session.scalars(select(EntityFlagRow.entity_id).where(EntityFlagRow.flag == EntityFlag.ORIGINAL_RESOURCE)))
    return [
        ResourceLine(
            entity.id,
            entity.name,
            entity.description if complete else entity.description[:DESCRIPTION_PREVIEW],
            RESOURCE_MECHANICS[entity.resource_mechanic].label if entity.resource_mechanic is not None else None,
            entity.id in original,
        )
        for entity in await _canon(session, world_id, [EntityType.RESOURCE])
    ]


async def _routes(session: AsyncSession, world_id: int, complete: bool) -> list[RouteLine]:
    routes = await session.scalars(select(RouteRow).where(or_(RouteRow.world_a_id == world_id, RouteRow.world_b_id == world_id)).order_by(RouteRow.id))
    lines: list[RouteLine] = []
    for route in routes:
        if not route.known and not complete:
            continue
        other = route.world_b_id if route.world_a_id == world_id else route.world_a_id
        name = await NodeRepository(session).name_of(other) or ""
        lines.append(RouteLine(route.id, name, TRAVEL_METHODS[route.method].label, route.duration_epochs, route.danger, route.active, route.known))
    return lines


async def traveller_guide(session: AsyncSession, rules: Rules, world_id: int, *, complete: bool = False) -> TravellerGuide:
    world = await session.get(WorldRow, world_id)
    if world is None:
        raise NotFoundError("No such world.")
    star = await session.get(StarRow, world.star_id) if world.star_id is not None else None
    parent = await NodeRepository(session).name_of(world.parent_world_id) if world.parent_world_id is not None else None
    gods = await session.scalars(select(ForeignGodRow).where(ForeignGodRow.world_id == world_id).order_by(ForeignGodRow.id))
    return TravellerGuide(
        world=world,
        type_label=WORLD_TYPES[world.world_type].label,
        star=star.name if star is not None else None,
        star_type=STAR_TYPE_LABELS[star.star_type] if star is not None else None,
        parent=parent,
        atmosphere=ATMOSPHERE_LABELS[world.atmosphere],
        gravity=GRAVITY_LABELS[world.gravity],
        discovery=DISCOVERY_LABELS[world.discovery],
        climate=CLIMATES[world.climate_era].label if world.climate_era is not None else None,
        climate_epochs_left=world.climate_epochs_left,
        dangers=await _dangers(session, rules, world, complete),
        peoples=await _peoples(session, rules, world_id, complete),
        resources=await _resources(session, world_id, complete),
        routes=await _routes(session, world_id, complete),
        foreign_gods=[GodLine(god.id, god.name, god.title, god.status.value, god.stance) for god in gods],
        sky=await _canon(session, world_id, [EntityType.CELESTIAL]),
    )


def guide_markdown(guide: TravellerGuide) -> str:
    world = guide.world
    head = [f"**{guide.type_label}**"]
    if guide.star:
        head.append(f"around {guide.star} ({guide.star_type})")
    if guide.parent:
        head.append(f"moon of {guide.parent}")
    head += [f"time {TIMES}{world.time_factor:g}", f"atmosphere {guide.atmosphere.lower()}", f"gravity {guide.gravity.lower()}"]
    lines = [SEPARATOR.join(head)]
    if guide.climate:
        lines.append(f"**Climate:** {guide.climate}" + (f" ({guide.climate_epochs_left} more epochs)" if guide.climate_epochs_left else ""))
    if guide.dangers:
        lines.append("**Dangers:** " + "; ".join(f"{danger.name} ({danger.reason})" for danger in guide.dangers))
    if guide.peoples:
        lines.append(
            "**Peoples:** " + "; ".join(f"{people.name} ({people.population})" + (f", worships {people.god}" if people.god else "") for people in guide.peoples)
        )
    if guide.resources:
        lines.append("**Resources:** " + "; ".join(resource.name + (f" [{resource.mechanics}]" if resource.mechanics else "") for resource in guide.resources))
    if guide.routes:
        lines.append(
            "**Roads:** "
            + "; ".join(
                f"{route.target} ({route.method}, {several(route.duration, 'epoch', 'epochs')}"
                + ("" if route.active else ", closed")
                + ("" if route.known else ", unknown")
                + ")"
                for route in guide.routes
            )
        )
    if guide.foreign_gods:
        lines.append("**Gods of this world:** " + "; ".join(god.name + (f" ({god.title})" if god.title else "") for god in guide.foreign_gods))
    if guide.sky:
        lines.append("**In the sky:** " + "; ".join(body.name for body in guide.sky))
    return "\n\n".join(lines)


async def _world_of_line(session: AsyncSession, line: ChronicleRow) -> int | None:
    if line.world_id is not None:
        return line.world_id
    if line.son_id is not None:
        world: int | None = await session.scalar(select(SonRow.current_world_id).where(SonRow.id == line.son_id))
        return world
    return None


async def cosmic_chronicle(session: AsyncSession, rules: Rules, last: int | None = None, *, complete: bool = False) -> list[CosmicEpoch]:
    count = max(1, min(last or rules.server.cosmic_chronicle_default, rules.server.cosmic_chronicle_max))
    epochs = sorted(set(await session.scalars(select(ChronicleRow.epoch).distinct())))
    if not complete:
        epochs = epochs[-count:]
    names = {world.id: world.name for world in await session.scalars(select(WorldRow))}
    result: list[CosmicEpoch] = []
    for epoch in epochs:
        grouped: dict[int, list[ChronicleRow]] = {}
        for line in await session.scalars(select(ChronicleRow).where(ChronicleRow.epoch == epoch, shown_lines()).order_by(ChronicleRow.id)):
            world_id = await _world_of_line(session, line)
            if world_id is not None and world_id in names:
                grouped.setdefault(world_id, []).append(line)
        narratives = {row.world_id: row for row in await session.scalars(select(EpochWorldNarrativeRow).where(EpochWorldNarrativeRow.epoch == epoch))}
        worlds = []
        for world_id, lines in sorted(grouped.items()):
            headlines = [" ".join(line.text.split()) for line in lines if line.kind in HEADLINE_KINDS]
            if not complete:
                headlines = [headline[:HEADLINE_LENGTH] for headline in headlines[:HEADLINES_PER_WORLD]]
            narrative = narratives.get(world_id)
            worlds.append(
                WorldChronicle(
                    world_id, names[world_id], len(lines), headlines, narrative.summary if narrative else None, narrative.narrative if narrative else None
                )
            )
        row = await session.get(EpochRow, epoch)
        result.append(CosmicEpoch(epoch, row.name if row else None, row.summary if row else None, worlds))
    return result
