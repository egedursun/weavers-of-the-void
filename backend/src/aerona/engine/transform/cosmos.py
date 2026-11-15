from collections import Counter

from sqlalchemy import select

from aerona.catalog.transformations import HUNGER_DOMAINS, POCKET_WORLDS
from aerona.constants.units import PERCENT
from aerona.db.repositories.names import NameRepository
from aerona.db.repositories.worlds import WorldDraft, WorldRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.cosmography import PhenomenonFootprintRow, PhenomenonProfileRow
from aerona.db.tables.divine import OuterBeingProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.cosmography import StarAge
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.world import Discovery, WorldType
from aerona.engine.context import TickContext
from aerona.engine.cosmos.foreign_gods import NewForeignGod, add_foreign_god
from aerona.engine.cosmos.orbits import planet_of
from aerona.engine.cosmos.placement import Cosmography
from aerona.engine.cosmos.routes import connect_world
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.primitives.queries import canon, flags_by_entity
from aerona.engine.transform.anchors import anchored_gods
from aerona.engine.transform.ledger import Ledger
from aerona.engine.transform.moves import bind, end

DEAD_STARS = frozenset({StarAge.DEAD})


async def revering(ctx: TickContext, flag: EntityFlag) -> list[EntityRow]:
    devoted = await flags_by_entity(ctx.session, flag)
    return [community for community in await canon(ctx.session, COMMUNITY_TYPES) if community.id in devoted]


async def world_soul_pressures(ctx: TickContext) -> dict[int, int]:
    table = ctx.rules.transform
    worshippers = Counter(community.world_id for community in await revering(ctx, EntityFlag.WORSHIPS_PLANET))
    found: dict[int, int] = {}
    statement = select(WorldRow).where(WorldRow.world_type == WorldType.LIVING, WorldRow.consciousness_closed.is_(False)).order_by(WorldRow.id)
    for world in await ctx.session.scalars(statement):
        if world.mood < table.world_soul_mood or worshippers[world.id] < table.world_soul_worshippers:
            continue
        if await anchored_gods(ctx, world_id=world.id):
            continue
        found[world.id] = PERCENT
    return found


async def world_soul_check(ctx: TickContext, world_id: int) -> str | None:
    world = await ctx.session.get(WorldRow, world_id)
    if world is None or world.world_type is not WorldType.LIVING:
        return "Only a living world can have a soul that ascends."
    if await anchored_gods(ctx, world_id=world.id):
        return f"{world.name} already has a god whose body it is."
    return None


async def ascend_world(ctx: TickContext, world_id: int, ledger: Ledger) -> int:
    world = await ctx.session.get_one(WorldRow, world_id)
    god = await add_foreign_god(
        ctx.session,
        ctx.rules,
        ctx.rng(f"world_soul.{world.id}"),
        ctx.epoch,
        NewForeignGod(name=f"Soul of {world.name}", world_id=world.id, domains=(Domain.LIFE, None), description=f"The soul of the world {world.name}."),
    )
    ledger.made(god.id)
    god.anchor_world_id = world.id
    for community in await revering(ctx, EntityFlag.WORSHIPS_PLANET):
        if community.world_id == world.id:
            await bind(ctx, ledger, (community.id, god.id, BondKind.WORSHIPS), f"worship of {world.name} given to its soul")
    return god.id


async def star_god_pressures(ctx: TickContext) -> dict[int, int]:
    table = ctx.rules.transform
    cosmography = await Cosmography.load(ctx.session)
    worshippers: Counter[int] = Counter()
    for community in await revering(ctx, EntityFlag.WORSHIPS_STAR):
        star = cosmography.place_world_id(community.world_id).star
        if star is not None:
            worshippers[star.id] += 1
    found: dict[int, int] = {}
    for star_id, count in sorted(worshippers.items()):
        star = cosmography.stars[star_id]
        if count >= table.star_god_worshippers and star.age_stage not in DEAD_STARS and not await anchored_gods(ctx, star_id=star_id):
            found[star_id] = PERCENT
    return found


async def star_god_check(ctx: TickContext, star_id: int) -> str | None:
    star = await ctx.session.get(StarRow, star_id)
    if star is None:
        return "Only a star can be raised to godhood."
    if star.age_stage in DEAD_STARS:
        return f"{star.name} is dead."
    if await anchored_gods(ctx, star_id=star.id):
        return f"{star.name} already has a god."
    return None


async def star_worlds(ctx: TickContext, star_id: int) -> list[WorldRow]:
    cosmography = await Cosmography.load(ctx.session)
    found: list[WorldRow] = []
    for world in sorted(cosmography.worlds.values(), key=lambda row: row.id):
        placed = cosmography.place_world(world).star
        if placed is not None and placed.id == star_id:
            found.append(world)
    return found


async def raise_star(ctx: TickContext, star_id: int, ledger: Ledger) -> int:
    star = await ctx.session.get_one(StarRow, star_id)
    worlds = await star_worlds(ctx, star.id)
    devoted = Counter(community.world_id for community in await revering(ctx, EntityFlag.WORSHIPS_STAR))
    home = max(worlds, key=lambda world: (devoted[world.id], -world.id)) if worlds else None
    if home is None:
        home = await ctx.session.scalar(select(WorldRow).order_by(WorldRow.id).limit(1))
    if home is None:
        return star.id
    god = await add_foreign_god(
        ctx.session,
        ctx.rules,
        ctx.rng(f"star_god.{star.id}"),
        ctx.epoch,
        NewForeignGod(name=f"Spirit of {star.name}", world_id=home.id, domains=(Domain.STAR, None), description=f"The spirit of the star {star.name}."),
    )
    ledger.made(god.id)
    god.anchor_star_id = star.id
    await star_light(ctx, god, ledger)
    return god.id


async def star_light(ctx: TickContext, god: ForeignGodRow, ledger: Ledger | None = None) -> int:
    if god.anchor_star_id is None:
        return 0
    lit = {world.id for world in await star_worlds(ctx, god.anchor_star_id)}
    joined = 0
    for community in await revering(ctx, EntityFlag.WORSHIPS_STAR):
        if community.world_id not in lit or held(community.id, god.id):
            continue
        known = await ctx.session.scalar(
            select(BondRow.id).where(
                BondRow.source_node_id == community.id, BondRow.target_node_id == god.id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE
            )
        )
        if known is not None:
            continue
        await bind(ctx, ledger or Ledger(), (community.id, god.id, BondKind.WORSHIPS), "worship of a star given to its spirit")
        joined += 1
    return joined


async def spread_star_light(ctx: TickContext) -> int:
    joined = 0
    for god in await ctx.session.scalars(select(ForeignGodRow).where(ForeignGodRow.anchor_star_id.is_not(None), ForeignGodRow.death_epoch.is_(None))):
        joined += await star_light(ctx, god)
    return joined


async def outer_cults(ctx: TickContext, being_id: int) -> list[EntityRow]:
    cults = await ctx.session.scalars(
        select(EntityRow)
        .join(BondRow, BondRow.source_node_id == EntityRow.id)
        .where(
            BondRow.target_node_id == being_id,
            BondRow.kind == BondKind.WORSHIPS,
            BondRow.state == BondState.ACTIVE,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.entity_type.in_(COMMUNITY_TYPES),
        )
        .order_by(EntityRow.id)
    )
    return list(dict.fromkeys(cults))


async def entered(ctx: TickContext, being_id: int) -> bool:
    found = await ctx.session.scalar(
        select(BondRow.id).where(
            BondRow.target_node_id == being_id, BondRow.kind == BondKind.DESCENDS_FROM, BondRow.source_node_id.in_(select(ForeignGodRow.id))
        )
    )
    return found is not None


async def outer_entry_pressures(ctx: TickContext) -> dict[int, int]:
    table = ctx.rules.transform
    worlds = {world.id: world for world in await ctx.session.scalars(select(WorldRow))}
    found: dict[int, int] = {}
    for being in await canon(ctx.session, [EntityType.OUTER_BEING]):
        cults = await outer_cults(ctx, being.id)
        if len(cults) < table.outer_entry_cults or await entered(ctx, being.id):
            continue
        leak = max((worlds[cult.world_id].leakage for cult in cults if cult.world_id in worlds), default=0)
        if leak >= table.outer_entry_leak:
            found[being.id] = PERCENT
    return found


async def outer_entry_check(ctx: TickContext, being_id: int) -> str | None:
    being = await ctx.session.get(EntityRow, being_id)
    if being is None or being.entity_type is not EntityType.OUTER_BEING or being.status is not EntityStatus.CANON:
        return "Only a living outer being can enter the cosmos as a god."
    if await entered(ctx, being.id):
        return f"{being.name} has already entered the cosmos."
    return None


async def enter_cosmos(ctx: TickContext, being_id: int, ledger: Ledger) -> int:
    being = await ctx.session.get_one(EntityRow, being_id)
    profile = await ctx.session.get(OuterBeingProfileRow, being.id)
    cults = await outer_cults(ctx, being.id)
    world_id = cults[0].world_id if cults and cults[0].world_id is not None else being.world_id
    if world_id is None:
        world_id = await ctx.session.scalar(select(WorldRow.id).order_by(WorldRow.id).limit(1))
    if world_id is None:
        return being.id
    domain = HUNGER_DOMAINS[profile.hunger] if profile is not None else Domain.MEMORY
    god = await add_foreign_god(
        ctx.session,
        ctx.rules,
        ctx.rng(f"outer_entry.{being.id}"),
        ctx.epoch,
        NewForeignGod(
            name=being.name,
            world_id=world_id,
            domains=(domain, None),
            power=clamp_percent(being.power_level),
            description=f"{being.name}, an outer being worshipped into the cosmos and bound by its law.",
        ),
    )
    ledger.made(god.id)
    await bind(ctx, ledger, (god.id, being.id, BondKind.DESCENDS_FROM), f"the form {being.name} took inside the cosmos")
    for cult in cults:
        await bind(ctx, ledger, (cult.id, god.id, BondKind.WORSHIPS), f"worship of {being.name} inside the cosmos")
    return god.id


async def pocket_pressures(ctx: TickContext) -> dict[int, int]:
    threshold = ctx.rules.phenomena.world_threshold
    statement = select(PhenomenonProfileRow).where(PhenomenonProfileRow.kind.in_(tuple(POCKET_WORLDS)), PhenomenonProfileRow.intensity >= threshold)
    found: dict[int, int] = {}
    for profile in await ctx.session.scalars(statement.order_by(PhenomenonProfileRow.entity_id)):
        phenomenon = await ctx.session.get(EntityRow, profile.entity_id)
        if phenomenon is not None and phenomenon.status is EntityStatus.CANON:
            found[profile.entity_id] = PERCENT
    return found


async def pocket_check(ctx: TickContext, phenomenon_id: int) -> str | None:
    profile = await ctx.session.get(PhenomenonProfileRow, phenomenon_id)
    phenomenon = await ctx.session.get(EntityRow, phenomenon_id)
    if profile is None or phenomenon is None or phenomenon.status is not EntityStatus.CANON:
        return "Only a living phenomenon can grow into a world."
    if profile.kind not in POCKET_WORLDS:
        return "Only a phenomenon of the void, of dream or of time can grow into a world."
    if phenomenon.world_id is None:
        return f"{phenomenon.name} is on no world."
    return None


async def detach(ctx: TickContext, phenomenon_id: int, ledger: Ledger) -> int:
    phenomenon = await ctx.session.get_one(EntityRow, phenomenon_id)
    profile = await ctx.session.get_one(PhenomenonProfileRow, phenomenon_id)
    host = await ctx.session.get_one(WorldRow, phenomenon.world_id)
    planet = await planet_of(ctx.session, host)
    pocket = await WorldRepository(ctx.session).create_world(
        WorldDraft(
            name=await NameRepository(ctx.session).unique_name(phenomenon.name),
            world_type=POCKET_WORLDS[profile.kind],
            orbit=planet.orbit,
            terrain_seed=f"{host.terrain_seed}.{phenomenon.id}",
            terrain_sea=host.terrain_sea,
            terrain_mountains=host.terrain_mountains,
            terrain_humidity=host.terrain_humidity,
            danger=clamp_percent(profile.intensity),
            created_epoch=ctx.epoch,
            star_id=planet.star_id,
            discovery=Discovery.KNOWN,
            description=f"A world grown out of the phenomenon {phenomenon.name} of {host.name}.",
        )
    )
    ledger.made(pocket.id)
    route = await connect_world(ctx, pocket, host.id)
    if route is not None:
        ledger.added(route)
    for footprint in await ctx.session.scalars(select(PhenomenonFootprintRow).where(PhenomenonFootprintRow.phenomenon_entity_id == phenomenon.id)):
        ledger.set(footprint, "intensity", 0)
    end(ctx, ledger, phenomenon, EntityStatus.DESTROYED)
    return pocket.id
