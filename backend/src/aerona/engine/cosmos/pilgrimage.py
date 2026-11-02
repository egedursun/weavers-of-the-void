import re

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.engine.context import TickContext
from aerona.engine.notes import note
from aerona.engine.primitives.faith import living_patron
from aerona.engine.primitives.queries import add_flag, canon, connect, flags_by_entity, living_entity
from aerona.engine.primitives.stats import shift_stat
from aerona.rules.registry import Rules

SITE_TYPES = frozenset({EntityType.PLACE, EntityType.STRUCTURE, EntityType.REGION})
TEMPLE_WORDS = re.compile(r"temple|shrine|altar|sanctuary", re.IGNORECASE)


async def holy_sites(session: AsyncSession, world_id: int, son_id: int | None) -> list[EntityRow]:
    marked = await flags_by_entity(session, EntityFlag.PILGRIMAGE_SITE)
    found: list[EntityRow] = []
    for entity in await canon(session, SITE_TYPES, world_id):
        if entity.id in marked:
            found.append(entity)
            continue
        if son_id is None or entity.entity_type is not EntityType.STRUCTURE or not TEMPLE_WORDS.search(entity.subtype or ""):
            continue
        home = await living_entity(session, entity.location_id)
        patron = await living_patron(session, home) if home is not None else None
        if patron is not None and patron.id == son_id:
            found.append(entity)
    return sorted(found, key=lambda site: (site.id not in marked, site.id))


async def has_holy_site(session: AsyncSession, community: EntityRow, world_id: int) -> bool:
    patron = await living_patron(session, community)
    if patron is None:
        return bool(await holy_sites(session, world_id, None))
    world = await session.get(WorldRow, world_id)
    return (world is not None and world.patron_son_id == patron.id) or bool(await holy_sites(session, world_id, patron.id))


async def reach_holy_site(ctx: TickContext, rules: Rules, pilgrims: EntityRow, world_id: int, landing: EntityRow) -> tuple[EntityRow, str]:
    patron = await living_patron(ctx.session, pilgrims)
    sites = await holy_sites(ctx.session, world_id, patron.id if patron is not None else None)
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
