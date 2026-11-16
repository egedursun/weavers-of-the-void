from dataclasses import dataclass

from sqlalchemy import and_, func, or_, select

from aerona.constants.units import PERCENT
from aerona.core.grammar import an
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.culture import RiteProfileRow
from aerona.db.tables.dominion import GodDesignRow, MagicSiteRow, ThroneRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import CultHoldingRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.place import PlaceProfileRow
from aerona.db.tables.routes import RouteRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held
from aerona.domain.enums.culture import MagicSchool
from aerona.domain.enums.dominion import MagicSiteKind
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType, MortalRole
from aerona.domain.enums.faith import HoldingKind
from aerona.domain.enums.mind import SkillKind
from aerona.engine.context import TickContext
from aerona.engine.cosmos.features import add_stock
from aerona.engine.cosmos.routes import RouteSpec, open_route, reaching
from aerona.engine.cosmos.world_types import hidden_route_method
from aerona.engine.divine.standing import standing_row
from aerona.engine.dominion.book import DominionBook
from aerona.engine.faith.book import patron_node
from aerona.engine.mind.book import skill_level
from aerona.engine.mythic.servitors import turned_back
from aerona.engine.notes import note
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import canon

SITE_KINDS = tuple(MagicSiteKind)
SCHOOLS = tuple(MagicSchool)


SCOUTING = (SkillKind.TRACKING, SkillKind.NAVIGATION, SkillKind.MOUNTAINEERING)


@dataclass
class SiteTally:
    seeded: int = 0
    found: int = 0
    yielded: int = 0
    thrones: int = 0
    passed: int = 0
    essence: int = 0


async def places_of(ctx: TickContext, world_id: int) -> list[EntityRow]:
    return [place for place in await canon(ctx.session, [EntityType.PLACE], world_id=world_id) if not held(place.id)]


async def found_sites_in(ctx: TickContext, atlas: RegionAtlas, region_id: int) -> list[MagicSiteRow]:
    sites = await ctx.session.scalars(select(MagicSiteRow).where(MagicSiteRow.found_epoch.is_not(None)).order_by(MagicSiteRow.id))
    return [site for site in sites if atlas.top_region(site.place_entity_id) == region_id]


async def seed_sites(ctx: TickContext, tally: SiteTally) -> None:
    table = ctx.rules.magic_sites
    worlds = list(await ctx.session.scalars(select(WorldRow).order_by(WorldRow.id)))
    for world in worlds:
        if held(world.id):
            continue
        places = await places_of(ctx, world.id)
        taken = set(await ctx.session.scalars(select(MagicSiteRow.place_entity_id)))
        have = sum(1 for place in places if place.id in taken)
        free = [place for place in places if place.id not in taken]
        rng = ctx.rng(f"magic_sites.{world.id}.{ctx.epoch}")
        others = [other.id for other in worlds if other.id != world.id]
        while have < table.per_world and free:
            place = free.pop(rng.die(len(free)) - 1)
            kind = rng.pick(list(SITE_KINDS))
            target = rng.pick(others) if kind is MagicSiteKind.GATEWAY and others else None
            ctx.session.add(
                MagicSiteRow(place_entity_id=place.id, kind=kind, school=rng.pick(list(SCHOOLS)), strength=table.strength, target_world_id=target, locked=[])
            )
            have += 1
            tally.seeded += 1
    await ctx.session.flush()


async def school_skill(ctx: TickContext, mortal_id: int, school: MagicSchool) -> int:
    rites = select(RiteProfileRow.rite_entity_id).where(RiteProfileRow.school == school)
    found = await ctx.session.scalar(
        select(func.max(SkillRow.level)).where(
            SkillRow.holder_node_id == mortal_id, SkillRow.skill == SkillKind.SPELLCRAFT, SkillRow.subject_node_id.in_(rites)
        )
    )
    return int(found or 0)


async def can_search(ctx: TickContext, mortal: EntityRow) -> bool:
    need = ctx.rules.magic_sites.search_skill
    if await skill_level(ctx.session, mortal.id, SkillKind.SPELLCRAFT) >= need:
        return True
    if mortal.mortal_role is not MortalRole.EXPLORER:
        return False
    return max([await skill_level(ctx.session, mortal.id, skill) for skill in SCOUTING]) >= need


async def search_chance(ctx: TickContext, mortal: EntityRow, site: MagicSiteRow) -> int:
    table = ctx.rules.magic_sites
    if await school_skill(ctx, mortal.id, site.school) >= table.search_skill:
        return table.search_pct
    if mortal.mortal_role is MortalRole.EXPLORER and await can_search(ctx, mortal):
        return table.explorer_search_pct
    return 0


async def searchers(ctx: TickContext, atlas: RegionAtlas, region_id: int | None) -> list[EntityRow]:
    found: list[EntityRow] = []
    for mortal in await canon(ctx.session, [EntityType.MORTAL]):
        if held(mortal.id) or atlas.top_region(mortal.id) != region_id:
            continue
        if await can_search(ctx, mortal):
            found.append(mortal)
    return found


async def community_at(ctx: TickContext, mortal: EntityRow) -> EntityRow | None:
    place = await ctx.session.get(EntityRow, mortal.location_id) if mortal.location_id is not None else None
    return place if place is not None and place.entity_type in COMMUNITY_TYPES else None


async def reveal(ctx: TickContext, site: MagicSiteRow, finder: EntityRow | None, tally: SiteTally) -> None:
    table = ctx.rules.magic_sites
    place = await ctx.session.get(EntityRow, site.place_entity_id)
    site.found_epoch = ctx.epoch
    site.found_by_node_id = finder.id if finder is not None else None
    holder = await community_at(ctx, finder) if finder is not None else None
    if holder is not None and "holder_node_id" not in site.locked:
        site.holder_node_id = holder.id
    profile = await ctx.session.get(PlaceProfileRow, site.place_entity_id)
    if profile is not None and "sacredness" not in profile.locked:
        profile.sacredness = clamp_int(profile.sacredness + table.sacredness, 0, PERCENT)
    cult = await patron_cult(ctx, finder) if finder is not None else None
    if cult is not None and await ctx.session.get(CultHoldingRow, (cult, site.place_entity_id)) is None:
        ctx.session.add(CultHoldingRow(cult_entity_id=cult, holding_entity_id=site.place_entity_id, kind=HoldingKind.HOLY_PLACE, since_epoch=ctx.epoch))
    tally.found += 1
    if site.kind is MagicSiteKind.GATEWAY and site.target_world_id is not None and place is not None and place.world_id is not None:
        await open_gateway(ctx, site, place)
    if place is not None:
        who = finder.name if finder is not None else "the gods"
        await note(
            ctx,
            f"{who} found {an(site.kind.value.replace('_', ' '))} of {site.school.value.replace('_', ' ')} magic at {place.name}.",
            key="dominion.magic_site_found",
            ids=[place.id, *([finder.id] if finder is not None else [])],
        )


async def open_gateway(ctx: TickContext, site: MagicSiteRow, place: EntityRow) -> None:
    first, second = await ctx.session.get(WorldRow, place.world_id), await ctx.session.get(WorldRow, site.target_world_id)
    if first is None or second is None or first.id == second.id or held(first.id, second.id):
        return
    linked = await ctx.session.scalar(
        select(RouteRow.id)
        .where(
            or_(
                and_(RouteRow.world_a_id == first.id, RouteRow.world_b_id == second.id), and_(RouteRow.world_a_id == second.id, RouteRow.world_b_id == first.id)
            )
        )
        .limit(1)
    )
    if linked is not None:
        return
    method = await reaching(ctx.session, first, second, hidden_route_method(first.world_type, second.world_type))
    if method is None:
        return
    await open_route(ctx.session, ctx.rules, ctx.rng(f"gateway.{site.id}"), ctx.epoch, RouteSpec(first.id, second.id, method, known=True))


async def patron_cult(ctx: TickContext, mortal: EntityRow) -> int | None:
    found = await ctx.session.scalar(
        select(EntityRow.id).where(
            EntityRow.id == mortal.affiliated_entity_id, EntityRow.entity_type == EntityType.CULT, EntityRow.status == EntityStatus.CANON
        )
    )
    return int(found) if found is not None else None


async def search_sites(ctx: TickContext, atlas: RegionAtlas, tally: SiteTally) -> None:
    for site in list(await ctx.session.scalars(select(MagicSiteRow).where(MagicSiteRow.found_epoch.is_(None)).order_by(MagicSiteRow.id))):
        if held(site.place_entity_id) or "found_epoch" in site.locked:
            continue
        for mage in await searchers(ctx, atlas, atlas.top_region(site.place_entity_id)):
            if ctx.rng(f"magic_site.search.{site.id}.{mage.id}.{ctx.epoch}").chance(await search_chance(ctx, mage, site)):
                await reveal(ctx, site, mage, tally)
                break
    await ctx.session.flush()


async def yield_sites(ctx: TickContext, tally: SiteTally) -> None:
    table = ctx.rules.magic_sites
    statement = select(MagicSiteRow).where(MagicSiteRow.found_epoch.is_not(None), MagicSiteRow.kind == MagicSiteKind.SOURCE).order_by(MagicSiteRow.id)
    for site in await ctx.session.scalars(statement):
        holder = await ctx.session.get(EntityRow, site.holder_node_id) if site.holder_node_id is not None else None
        if holder is None or holder.status is not EntityStatus.CANON or held(holder.id, site.place_entity_id):
            continue
        amount = round_half_up(site.strength * table.output_pct / PERCENT)
        if amount and holder.entity_type in COMMUNITY_TYPES:
            await add_stock(ctx, holder, CommodityKind.MAGICAL_REAGENTS, amount)
            if "output" not in site.locked:
                site.output = amount
            tally.yielded += amount
    await ctx.session.flush()


async def seed_thrones(ctx: TickContext, tally: SiteTally) -> None:
    table = ctx.rules.thrones
    for world in list(await ctx.session.scalars(select(WorldRow).order_by(WorldRow.id))):
        if held(world.id):
            continue
        taken = set(await ctx.session.scalars(select(ThroneRow.place_entity_id)))
        have = int(sum(1 for throne in await ctx.session.scalars(select(ThroneRow).where(ThroneRow.world_id == world.id))))
        places = [place for place in await places_of(ctx, world.id) if place.id not in taken]
        sacred = {profile.entity_id: profile.sacredness for profile in await ctx.session.scalars(select(PlaceProfileRow))}
        places.sort(key=lambda place: (-sacred.get(place.id, 0), place.id))
        for place in places[: max(0, table.per_world - have)]:
            ctx.session.add(ThroneRow(world_id=world.id, place_entity_id=place.id, power=table.power, locked=[]))
            tally.thrones += 1
    await ctx.session.flush()


async def claimant(ctx: TickContext, atlas: RegionAtlas, book: DominionBook, throne: ThroneRow) -> int | None:
    table = ctx.rules.thrones
    region = atlas.top_region(throne.place_entity_id)
    ruler = book.rulers.get(region) if region is not None else None
    if ruler is not None and ruler.share >= table.dominion_share:
        return ruler.god_node_id
    place = await ctx.session.get(EntityRow, throne.place_entity_id)
    if place is None:
        return None
    for community in await canon(ctx.session, list(COMMUNITY_TYPES), world_id=throne.world_id):
        if community.location_id in {place.id, place.location_id} or community.id == place.location_id:
            patron = await patron_node(ctx.session, community.id)
            if patron is not None:
                return patron
    return None


async def give_essence(ctx: TickContext, god_id: int, amount: int) -> int:
    for kind in (SonRow, ForeignGodRow, CreatorRow):
        god = await ctx.session.get(kind, god_id)
        if god is not None and hasattr(god, "essence"):
            god.essence = god.essence + amount
            return amount
    return 0


async def tend_thrones(ctx: TickContext, tally: SiteTally) -> None:
    table = ctx.rules.thrones
    atlas = await RegionAtlas.load(ctx.session)
    book = await DominionBook.load(ctx.session)
    for throne in list(await ctx.session.scalars(select(ThroneRow).order_by(ThroneRow.id))):
        if held(throne.place_entity_id) or held(throne.world_id):
            continue
        holder = await claimant(ctx, atlas, book, throne)
        if holder is not None and held(holder):
            holder = throne.holder_node_id
        guarded = throne.holder_node_id is not None and holder != throne.holder_node_id
        if guarded and await turned_back(ctx, [throne.place_entity_id], f"throne.guard.{throne.id}.{ctx.epoch}"):
            holder = throne.holder_node_id
        if holder != throne.holder_node_id and "holder_node_id" not in throne.locked:
            throne.holder_node_id, throne.since_epoch = holder, ctx.epoch
            tally.passed += 1
            place = await ctx.session.get(EntityRow, throne.place_entity_id)
            if place is not None:
                name = await god_name(ctx, holder)
                await note(
                    ctx, f"The throne of power at {place.name} passed to {name}.", key="dominion.throne_passed", ids=[place.id, *([holder] if holder else [])]
                )
        if throne.holder_node_id is None:
            continue
        design = await ctx.session.get(GodDesignRow, throne.holder_node_id)
        rank = design.rank if design is not None else 0
        amount = round_half_up(table.essence * throne.power / PERCENT * (PERCENT + rank * table.rank_essence_pct) / PERCENT)
        if amount and not held(throne.holder_node_id):
            tally.essence += await give_essence(ctx, throne.holder_node_id, amount)
        for community in await canon(ctx.session, list(COMMUNITY_TYPES), world_id=throne.world_id):
            if held(community.id, throne.holder_node_id):
                continue
            standing = await standing_row(ctx, community.id, throne.holder_node_id)
            if "awe" not in standing.locked:
                standing.awe = clamp_int(standing.awe + table.standing, 0, PERCENT)
    await ctx.session.flush()


async def god_name(ctx: TickContext, node_id: int | None) -> str:
    for kind in (SonRow, ForeignGodRow, CreatorRow):
        god = await ctx.session.get(kind, node_id) if node_id is not None else None
        if god is not None:
            return str(god.name)
    return "nobody"


async def thrones_held(ctx: TickContext, god_id: int) -> tuple[int, int]:
    table = ctx.rules.thrones
    worlds = 0
    for world in await ctx.session.scalars(select(WorldRow).order_by(WorldRow.id)):
        thrones = list(await ctx.session.scalars(select(ThroneRow).where(ThroneRow.world_id == world.id)))
        if thrones and sum(1 for throne in thrones if throne.holder_node_id == god_id) * PERCENT >= table.ascension_share * len(thrones):
            worlds += 1
    return worlds, table.ascension_worlds
