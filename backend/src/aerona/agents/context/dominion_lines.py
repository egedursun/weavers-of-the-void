from sqlalchemy import select

from aerona.agents.context.scope import Scope
from aerona.catalog.dominion import SCALE_POLES
from aerona.core.grammar import an
from aerona.db.tables.divine import DivineStandingRow
from aerona.db.tables.dominion import DivineCreatureRow, DominionRow, GodDesignRow, GodImageRow, GodScaleRow, MagicSiteRow, RegionDominionRow, ThroneRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.sons import SonRow
from aerona.engine.gods.queries import community_of
from aerona.engine.primitives.distance import RegionAtlas


def spoken(value: str) -> str:
    return value.replace("_", " ")


async def place_name(scope: Scope, entity_id: int | None) -> str:
    place = await scope.session.get(EntityRow, entity_id) if entity_id is not None else None
    return place.name if place is not None else "an unknown place"


async def realm_lines(scope: Scope, son: SonRow) -> list[str]:
    session = scope.session
    shown = scope.rules.context.son_standing_lines
    ruled = list(await session.scalars(select(RegionDominionRow).where(RegionDominionRow.god_node_id == son.id).order_by(RegionDominionRow.share.desc())))
    found = []
    if ruled:
        parts = [f"{await place_name(scope, row.region_entity_id)} ({row.share}% of the dominion there, {row.rivals} rival gods)" for row in ruled[:shown]]
        found.append(f"You rule {len(ruled)} regions: {', '.join(parts)}")
    ruled_ids = {row.region_entity_id for row in ruled}
    claims = await session.scalars(select(DominionRow).where(DominionRow.god_node_id == son.id, DominionRow.strength > 0).order_by(DominionRow.strength.desc()))
    contested = [row for row in claims if row.region_entity_id not in ruled_ids]
    for row in contested[:shown]:
        found.append(f"Your dominion over {await place_name(scope, row.region_entity_id)} stands at {row.strength}, yet another god rules there")
    return found


async def shape_lines(scope: Scope, son: SonRow) -> list[str]:
    session = scope.session
    found = []
    scales = [row for row in await session.scalars(select(GodScaleRow).where(GodScaleRow.god_node_id == son.id).order_by(GodScaleRow.scale)) if row.value]
    if scales:
        parts = [f"{SCALE_POLES[row.scale][0 if row.value > 0 else 1]} {abs(row.value)}" for row in scales]
        found.append(f"Your rule leans the lands toward: {', '.join(parts)}")
    design = await session.get(GodDesignRow, son.id)
    if design is not None:
        found.append(
            f"Your design: dominion strength {design.dominion_strength}, magic aptitude {design.magic_aptitude}, "
            f"manifestation {design.manifestation_strength}, rank {design.rank}; your powers stand at {design.stats_pct}% of their full measure"
        )
    image = await session.get(GodImageRow, son.id)
    if image is not None:
        domain = f", a god of {spoken(image.believed_domain.value)}" if image.believed_domain is not None else ""
        found.append(
            f"Your peoples believe you {image.believed_alignment.value}{domain}, seen as {spoken(image.manifestation.value)}; "
            f"their belief pulls you {image.pull}% an age and you {image.stance.value} it"
        )
    return found


async def holding_lines(scope: Scope, son: SonRow) -> list[str]:
    session = scope.session
    found = []
    for creature in await session.scalars(
        select(DivineCreatureRow).where(DivineCreatureRow.god_node_id == son.id).order_by(DivineCreatureRow.creature_entity_id)
    ):
        deed = f", last it chose to {spoken(creature.last_deed.value)}" if creature.last_deed is not None else ""
        found.append(f"Your creature {await place_name(scope, creature.creature_entity_id)} #{creature.creature_entity_id}: hunger {creature.hunger}{deed}")
    for throne in await session.scalars(select(ThroneRow).where(ThroneRow.holder_node_id == son.id).order_by(ThroneRow.id)):
        found.append(f"You hold the throne of power at {await place_name(scope, throne.place_entity_id)} (power {throne.power})")
    for site in await session.scalars(select(MagicSiteRow).where(MagicSiteRow.holder_node_id == son.id).order_by(MagicSiteRow.id)):
        found.append(f"You hold {an(spoken(site.kind.value))} of {spoken(site.school.value)} at {await place_name(scope, site.place_entity_id)}")
    return found


async def dominion_lines(scope: Scope, son: SonRow) -> list[str]:
    return [*await realm_lines(scope, son), *await shape_lines(scope, son), *await holding_lines(scope, son)]


async def god_called(scope: Scope, node_id: int) -> str:
    god = await scope.session.get(NodeRow, node_id)
    return god.name if god is not None else "a god"


async def ruler_lines(scope: Scope, region_id: int) -> list[str]:
    ruler = await scope.session.get(RegionDominionRow, region_id)
    if ruler is None:
        return []
    name = await god_called(scope, ruler.god_node_id)
    found = [f"{name} holds dominion over your land ({ruler.share}% of all divine hold here)"]
    scales = [
        row
        for row in await scope.session.scalars(select(GodScaleRow).where(GodScaleRow.god_node_id == ruler.god_node_id).order_by(GodScaleRow.scale))
        if row.value
    ]
    if scales:
        found.append(f"under that rule your land leans toward {', '.join(SCALE_POLES[row.scale][0 if row.value > 0 else 1] for row in scales)}")
    return found


async def worship_lines(scope: Scope, me: EntityRow) -> list[str]:
    community = await community_of(scope.session, me)
    if community is None:
        return []
    found = []
    for standing in await scope.session.scalars(
        select(DivineStandingRow).where(DivineStandingRow.community_entity_id == community.id).order_by(DivineStandingRow.god_node_id)
    ):
        if standing.perceived is None:
            continue
        mode = f" and worship it in {standing.mode.value}" if standing.mode is not None else ""
        found.append(f"your people hold {await god_called(scope, standing.god_node_id)} {standing.perceived.value}{mode}")
    return found


async def land_lines(scope: Scope, region_id: int, atlas: RegionAtlas) -> list[str]:
    session = scope.session
    found = []
    for site in await session.scalars(select(MagicSiteRow).where(MagicSiteRow.found_epoch.is_not(None)).order_by(MagicSiteRow.id)):
        if atlas.top_region(site.place_entity_id) == region_id:
            found.append(f"{an('known ' + spoken(site.kind.value))} of {spoken(site.school.value)} lies at {await place_name(scope, site.place_entity_id)}")
    for throne in await session.scalars(select(ThroneRow).order_by(ThroneRow.id)):
        if atlas.top_region(throne.place_entity_id) == region_id:
            holder = await god_called(scope, throne.holder_node_id) if throne.holder_node_id is not None else "no god"
            found.append(f"a throne of power stands at {await place_name(scope, throne.place_entity_id)}, held by {holder}")
    for creature in await session.scalars(select(DivineCreatureRow).order_by(DivineCreatureRow.creature_entity_id)):
        if atlas.top_region(creature.creature_entity_id) == region_id:
            found.append(f"{await place_name(scope, creature.creature_entity_id)}, a creature of {await god_called(scope, creature.god_node_id)}, roams here")
    return found


async def mortal_dominion_lines(scope: Scope, me: EntityRow) -> list[str]:
    atlas = await RegionAtlas.load(scope.session)
    region_id = atlas.top_region(me.id)
    found = await worship_lines(scope, me)
    if region_id is None:
        return found
    return [*await ruler_lines(scope, region_id), *found, *await land_lines(scope, region_id, atlas)]
