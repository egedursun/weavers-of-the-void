from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.structures import HOLY_HOUSES
from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.engine.context import TickContext
from aerona.engine.environment.places import holy_place_ids
from aerona.engine.notes import note
from aerona.engine.primitives.faith import living_patron
from aerona.engine.primitives.queries import add_flag, canon, connect, flags_by_entity, living_entity
from aerona.engine.primitives.stats import shift_stat
from aerona.rules.registry import Rules

SITE_TYPES = frozenset({EntityType.PLACE, EntityType.STRUCTURE, EntityType.REGION})


async def holy_sites(session: AsyncSession, world_id: int, son_id: int | None, rules: Rules) -> list[EntityRow]:
    marked = await flags_by_entity(session, EntityFlag.PILGRIMAGE_SITE)
    sacred = await holy_place_ids(session, rules, world_id)
    rank = {place_id: index for index, place_id in enumerate(sacred)}
    found: list[EntityRow] = []
    for entity in await canon(session, SITE_TYPES, world_id):
        if entity.id in marked or entity.id in rank:
            found.append(entity)
            continue
        profile = await session.get(StructureProfileRow, entity.id) if entity.entity_type is EntityType.STRUCTURE else None
        if son_id is None or profile is None or profile.kind not in HOLY_HOUSES:
            continue
        if profile.dedicated_son_id == son_id:
            found.append(entity)
            continue
        home = await living_entity(session, entity.location_id)
        patron = await living_patron(session, home) if home is not None else None
        if patron is not None and patron.id == son_id:
            found.append(entity)
    return sorted(found, key=lambda site: (site.id not in marked and site.id not in rank, rank.get(site.id, len(rank)), site.id))


async def has_holy_site(session: AsyncSession, community: EntityRow, world_id: int, rules: Rules) -> bool:
    patron = await living_patron(session, community)
    if patron is None:
        return bool(await holy_sites(session, world_id, None, rules))
    world = await session.get(WorldRow, world_id)
    return (world is not None and world.patron_son_id == patron.id) or bool(await holy_sites(session, world_id, patron.id, rules))


async def reach_holy_site(ctx: TickContext, rules: Rules, pilgrims: EntityRow, world_id: int, landing: EntityRow) -> tuple[EntityRow, str]:
    patron = await living_patron(ctx.session, pilgrims)
    sites = await holy_sites(ctx.session, world_id, patron.id if patron is not None else None, rules)
    site = sites[0] if sites else landing
    await add_flag(ctx.session, site.id, EntityFlag.PILGRIMAGE_SITE, ctx.epoch)
    if not await BondRepository(ctx.session).exists_between(pilgrims.id, site.id, BondKind.CELEBRATES):
        await connect(ctx.session, pilgrims.id, site.id, BondKind.CELEBRATES, ctx.epoch, description="pilgrimage")
    shift_stat(pilgrims, "piety", rules.travel.pilgrimage_piety)
    if patron is not None:
        patron.fame += rules.travel.pilgrimage_renown
    in_name = f" in the name of {patron.name}" if patron is not None else ""
    return site, f"the pilgrims made offerings at {site.name}{in_name}"


async def declare_pilgrimage_site(ctx: TickContext, entity_id: int, by: str) -> EntityRow:
    site = await living_entity(ctx.session, entity_id)
    if site is None or site.entity_type not in SITE_TYPES:
        raise ValidationFailedError("Only a place, structure or region can become a pilgrimage site.")
    if not await add_flag(ctx.session, site.id, EntityFlag.PILGRIMAGE_SITE, ctx.epoch):
        raise ValidationFailedError(f"{site.name} is already a pilgrimage site.")
    await note(
        ctx, f"{by} declared {site.name} a pilgrimage site; believers will travel to it from distant worlds.", key="travel.pilgrimage_site", ids=[site.id]
    )
    return site
