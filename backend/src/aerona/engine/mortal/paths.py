from sqlalchemy import select

from aerona.catalog.careers import CAREERS, CareerSpec
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import HouseProfileRow
from aerona.domain.enums.body import DamageType, HarmCause
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.environment import CoastKind
from aerona.domain.enums.mind import NeedKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mortal import CareerPath
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.mind.book import needs_of, write_needs
from aerona.engine.mind.skills import practise_any
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.queries import active_bonds, connect, flags_by_entity
from aerona.engine.recording.record import record


async def by_the_sea(ctx: TickContext, town_id: int | None) -> bool:
    region = (await RegionAtlas.load(ctx.session)).top_region(town_id) if town_id is not None else None
    ground = await ctx.session.get(RegionEnvironmentRow, region) if region is not None else None
    return ground is not None and ground.coast_kind is not CoastKind.NONE


async def house_seated(ctx: TickContext, town_id: int | None) -> HouseProfileRow | None:
    if town_id is None:
        return None
    for house in await ctx.session.scalars(select(HouseProfileRow).where(HouseProfileRow.extinct_epoch.is_(None)).order_by(HouseProfileRow.house_entity_id)):
        if town_id in (house.seats or []):
            return house
    return None


async def frontiers(ctx: TickContext, world_id: int | None, home: int | None) -> list[EntityRow]:
    marked = set(await flags_by_entity(ctx.session, EntityFlag.COLONY)) | set(await flags_by_entity(ctx.session, EntityFlag.PIONEER))
    found = await ctx.session.scalars(
        select(EntityRow)
        .where(
            EntityRow.id.in_(sorted(marked)),
            EntityRow.entity_type == EntityType.SETTLEMENT,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.world_id == world_id,
        )
        .order_by(EntityRow.id)
    )
    return [town for town in found if town.id != home]


async def path_open(ctx: TickContext, mortal: EntityRow, spec: CareerSpec) -> bool:
    if spec.crews:
        return await by_the_sea(ctx, mortal.location_id)
    if spec.household:
        return await house_seated(ctx, mortal.location_id) is not None
    if spec.frontier:
        return bool(await frontiers(ctx, mortal.world_id, mortal.location_id))
    return spec.opening


async def go_to_sea(ctx: TickContext, mortal: EntityRow) -> bool:
    if not ctx.rng(f"path.sea.{mortal.id}.{ctx.epoch}").chance(ctx.rules.careers.sea_loss_pct):
        return False
    harm = Harm(PERCENT, HarmCause.ACCIDENT, "lost at sea", damage_type=DamageType.ASPHYXIA)
    await apply_hits(ctx, mortal, harm, lethal=True)
    await record(ctx, "career.lost_at_sea", roles={IncidentRole.SUBJECT: mortal.id})
    return True


async def enter_service(ctx: TickContext, mortal: EntityRow) -> bool:
    house = await house_seated(ctx, mortal.location_id)
    if house is None or await active_bonds(ctx.session, [BondKind.MEMBER_OF], sources=[mortal.id], targets=[house.house_entity_id]):
        return False
    await connect(ctx.session, mortal.id, house.house_entity_id, BondKind.MEMBER_OF, ctx.epoch, description="in service")
    await record(ctx, "career.entered_service", roles={IncidentRole.SUBJECT: mortal.id, IncidentRole.TARGET: house.house_entity_id})
    return True


async def make_art(ctx: TickContext, mortal: EntityRow) -> bool:
    needs = dict(await needs_of(ctx.session, mortal.id))
    needs[NeedKind.CREATING] = PERCENT
    await write_needs(ctx.session, mortal.id, needs)
    return True


async def settle_frontier(ctx: TickContext, mortal: EntityRow) -> bool:
    places = await frontiers(ctx, mortal.world_id, mortal.location_id)
    rng = ctx.rng(f"path.settle.{mortal.id}.{ctx.epoch}")
    if not places or not rng.chance(ctx.rules.careers.settle_found_pct):
        return False
    home = mortal.location_id
    frontier = rng.pick(places)
    mortal.location_id = frontier.id
    await connect(ctx.session, mortal.id, frontier.id, BondKind.MIGRATED_TO, ctx.epoch, description="settled a frontier")
    await record(ctx, "career.settled_frontier", roles={IncidentRole.SUBJECT: mortal.id, IncidentRole.ORIGIN: home, IncidentRole.DESTINATION: frontier.id})
    return True


async def walk_path(ctx: TickContext, mortal: EntityRow, profile: MortalProfileRow) -> str | None:
    if profile.career is None:
        return None
    spec = CAREERS[profile.career]
    if spec.skills:
        await practise_any(ctx.session, ctx.rules, mortal.id, spec.skills, ctx.rules.careers.service_skill_xp, epoch=ctx.epoch)
    acted = False
    if spec.crews:
        acted = await go_to_sea(ctx, mortal)
    elif spec.household:
        acted = await enter_service(ctx, mortal)
    elif spec.venues:
        acted = await make_art(ctx, mortal)
    elif spec.frontier:
        acted = await settle_frontier(ctx, mortal)
    return profile.career.value if acted else None


def path_weight(ctx: TickContext, path: CareerPath) -> float:
    return CAREERS[path].weight(ctx.rules) / (PERCENT // 2)
