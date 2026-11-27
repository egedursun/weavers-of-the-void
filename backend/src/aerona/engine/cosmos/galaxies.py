import math
from collections import Counter

from sqlalchemy import select

from aerona.catalog.cosmography import BARRED_GALAXIES, GALACTIC_EVENT_LABELS, GALAXY_AGE_ORDER, SPIRAL_GALAXIES
from aerona.catalog.travel import travel_method_profile
from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.names import NameRepository
from aerona.db.tables.celestial import StarRow
from aerona.db.tables.cosmography import GalacticEventRow, GalacticStructureRow, GalaxyRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.physics import StarSystemRow
from aerona.db.tables.routes import RouteRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held
from aerona.domain.enums.cosmography import GalacticEventKind, GalacticNucleus, GalacticStructureKind, GalacticZone, GalaxyAge, GalaxyType, RouteScope
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityFlag, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import StepAction, StepOutcome
from aerona.domain.enums.world import Discovery, StarType
from aerona.engine.context import TickContext
from aerona.engine.cosmos.kinds import CLUSTER_KIND_MECHANICS, GALAXY_TYPE_MECHANICS, STRUCTURE_MECHANICS
from aerona.engine.cosmos.ladder import GalaxyDraft, birth_position, create_galaxy, settle_star
from aerona.engine.cosmos.placement import Cosmography
from aerona.engine.cosmos.stars import StarSpec, create_star
from aerona.engine.cosmos.stellar import physics_of_stars
from aerona.engine.cosmos.systems import join_system
from aerona.engine.gods.essence import endow
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.primitives.queries import canon, flags_by_entity
from aerona.engine.primitives.stats import scale_stat, shift_bounded
from aerona.engine.recording.record import StepDraft, record

BRIGHT_DOMAINS = frozenset({Domain.STAR, Domain.SUN, Domain.LIGHT, Domain.SKY})
DARK_DOMAINS = frozenset({Domain.DEATH, Domain.ASH, Domain.SHADOW})
BIRTH_TYPES: dict[GalaxyAge, tuple[tuple[StarType, int], ...]] = {
    GalaxyAge.FORMING: ((StarType.PROTOSTAR, 4), (StarType.BLUE_STAR, 2), (StarType.BLUE_WHITE_STAR, 2), (StarType.RED_DWARF, 2)),
    GalaxyAge.YOUNG: ((StarType.PROTOSTAR, 2), (StarType.BLUE_WHITE_STAR, 2), (StarType.WHITE_STAR, 2), (StarType.YELLOW_DWARF, 2), (StarType.RED_DWARF, 3)),
    GalaxyAge.MATURE: ((StarType.YELLOW_DWARF, 3), (StarType.ORANGE_DWARF, 3), (StarType.RED_DWARF, 4), (StarType.WHITE_STAR, 1), (StarType.BLUE_STAR, 1)),
    GalaxyAge.OLD: ((StarType.RED_DWARF, 5), (StarType.ORANGE_DWARF, 2), (StarType.YELLOW_DWARF, 1)),
    GalaxyAge.DYING: ((StarType.RED_DWARF, 5), (StarType.BROWN_DWARF, 2)),
    GalaxyAge.DEAD: ((StarType.BROWN_DWARF, 1),),
}
SPLIT_TYPES = (GalaxyType.IRREGULAR, GalaxyType.DWARF_IRREGULAR)
DISRUPTED_STRUCTURES = frozenset({GalacticStructureKind.SPIRAL_ARM, GalacticStructureKind.BAR})


def unlocked(row: GalaxyRow | StarRow | GalacticStructureRow, field: str) -> bool:
    return field not in row.locked


def active(event: GalacticEventRow, epoch: int) -> bool:
    return event.until_epoch is None or event.until_epoch >= epoch


async def open_event(
    ctx: TickContext,
    galaxy: GalaxyRow,
    kind: GalacticEventKind,
    intensity: int,
    *,
    other: GalaxyRow | None = None,
    star: StarRow | None = None,
    structure: GalacticStructureRow | None = None,
) -> GalacticEventRow:
    label = GALACTIC_EVENT_LABELS[kind]
    text = f"{label.label} in {galaxy.name}: {label.description}"
    row = GalacticEventRow(
        kind=kind,
        galaxy_id=galaxy.id,
        other_galaxy_id=other.id if other is not None else None,
        structure_id=structure.id if structure is not None else None,
        star_id=star.id if star is not None else None,
        epoch=ctx.epoch,
        until_epoch=ctx.epoch + ctx.rules.galaxies.event_epochs - 1,
        intensity=clamp_percent(intensity),
        text=text,
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await record(
        ctx,
        f"galaxy.{kind.value}",
        roles={
            IncidentRole.SUBJECT: galaxy.id,
            IncidentRole.CO_ACTOR: other.id if other is not None else None,
            IncidentRole.ACTOR: star.id if star is not None else None,
        },
        facts={
            "event": kind,
            "intensity": row.intensity,
            "structure": structure.name if structure is not None else None,
            "epochs": ctx.rules.galaxies.event_epochs,
        },
        steps=(StepDraft(StepAction.BEGIN, target=galaxy.id), StepDraft(StepAction.END, target=galaxy.id)),
    )
    ctx.count(f"galactic_{kind.value}")
    return row


def formation_target(ctx: TickContext, galaxy: GalaxyRow, patron: SonRow | None, merging: bool) -> int:
    table = ctx.rules.galaxies
    target = GALAXY_TYPE_MECHANICS[galaxy.galaxy_type].formation(ctx.rules)
    target -= GALAXY_AGE_ORDER.index(galaxy.age_stage) * table.age_formation_loss // 2
    if patron is not None:
        domains = {patron.domain_primary, patron.domain_secondary}
        if domains & BRIGHT_DOMAINS:
            target += table.patron_formation
        if domains & DARK_DOMAINS:
            target -= table.patron_formation
    if merging:
        target += table.merger_burst
    return clamp_percent(target)


async def drift_formation(ctx: TickContext, cosmography: Cosmography, galaxy: GalaxyRow) -> None:
    if not unlocked(galaxy, "star_formation"):
        return
    patron = await ctx.session.get(SonRow, galaxy.patron_son_id) if galaxy.patron_son_id is not None else None
    merging = galaxy.merging_with_galaxy_id is not None or any(other.merging_with_galaxy_id == galaxy.id for other in cosmography.galaxies.values())
    target = formation_target(ctx, galaxy, patron, merging)
    step = ctx.rules.galaxies.formation_drift
    value = galaxy.star_formation + max(-step, min(step, target - galaxy.star_formation))
    cluster = cosmography.clusters.get(galaxy.cluster_id) if galaxy.cluster_id is not None else None
    if cluster is not None:
        value -= cluster.medium_heat // 10 * ctx.rules.clusters.medium_strip
    galaxy.star_formation = clamp_percent(value)


async def age_galaxy(ctx: TickContext, galaxy: GalaxyRow) -> None:
    if not unlocked(galaxy, "age_stage") or galaxy.age_stage is GalaxyAge.DEAD:
        return
    if not ctx.rng(f"galaxy_age.{galaxy.id}").chance(ctx.rules.galaxies.age_chance):
        return
    before = galaxy.age_stage
    galaxy.age_stage = GALAXY_AGE_ORDER[GALAXY_AGE_ORDER.index(before) + 1]
    await record(
        ctx,
        "galaxy.aged",
        roles={IncidentRole.SUBJECT: galaxy.id},
        facts={"age": galaxy.age_stage, "chance": ctx.rules.galaxies.age_chance},
        steps=(StepDraft(StepAction.AGE, target=galaxy.id, instrument_key=before.value, record_table=GalaxyRow.__tablename__, record_key=str(galaxy.id)),),
    )


async def bear_stars(ctx: TickContext, cosmography: Cosmography, galaxy: GalaxyRow) -> int:
    table = ctx.rules.galaxies
    rng = ctx.rng(f"galaxy_birth.{galaxy.id}")
    born = 0
    nurseries = sorted(
        (
            row
            for row in cosmography.structures.values()
            if row.galaxy_id == galaxy.id and row.ended_epoch is None and STRUCTURE_MECHANICS[row.kind].birth(ctx.rules) > 0
        ),
        key=lambda row: row.id,
    )
    for structure in rng.shuffled(nurseries):
        if born >= table.birth_cap:
            break
        chance = STRUCTURE_MECHANICS[structure.kind].birth(ctx.rules) * structure.intensity / PERCENT * galaxy.star_formation / PERCENT
        if not rng.chance(chance):
            continue
        kinds = BIRTH_TYPES[galaxy.age_stage]
        star_type = rng.weighted([kind for kind, _ in kinds], [weight for _, weight in kinds])
        count = len(cosmography.stars_in_galaxy(galaxy.id)) + born + 1
        name = await NameRepository(ctx.session).unique_name(f"{galaxy.name} {count}")
        star = await create_star(
            ctx.session,
            ctx.rules,
            rng,
            ctx.epoch,
            StarSpec(name, star_type, 0, table.birth_brightness_die, None, galaxy.id, birth_position(rng, structure)),
        )
        cosmography.stars[star.id] = star
        born += 1
        await pair_newborn(ctx, cosmography, star, structure, rng)
        await record(
            ctx,
            "galaxy.star_born",
            roles={IncidentRole.SUBJECT: galaxy.id, IncidentRole.PRODUCT: star.id},
            facts={"structure": structure.name, "star_type": star_type, "chance": chance * PERCENT},
            steps=(StepDraft(StepAction.APPEAR, target=star.id, outcome=StepOutcome.SUCCESS),),
        )
    return born


async def pair_newborn(ctx: TickContext, cosmography: Cosmography, star: StarRow, structure: GalacticStructureRow, rng: SeededRandom) -> bool:
    table = ctx.rules.stellar_evolution
    siblings = sorted((row for row in cosmography.stars.values() if row.structure_id == structure.id and row.id != star.id), key=lambda row: row.id)
    if not siblings or not rng.chance(table.binary_chance):
        return False
    primary = (await physics_of_stars(ctx.session, ctx.rules, [siblings[0]]))[siblings[0].id]
    if primary.system_id is None:
        return False
    await join_system(ctx.session, ctx.rules, star, primary.system_id)
    system = await ctx.session.get(StarSystemRow, primary.system_id)
    if system is not None and "separation" not in system.locked:
        system.separation = table.binary_separation_tenths / 10
    await record(
        ctx,
        "star.binary_born",
        roles={IncidentRole.SUBJECT: siblings[0].id, IncidentRole.PRODUCT: star.id},
        facts={"separation": system.separation if system is not None else table.binary_separation_tenths / 10},
    )
    return True


async def nucleus_outburst(ctx: TickContext, galaxy: GalaxyRow) -> None:
    table = ctx.rules.galaxies
    chance = {GalacticNucleus.ACTIVE: table.outburst_chance_active, GalacticNucleus.QUASAR: table.outburst_chance_quasar}.get(galaxy.nucleus, 0)
    if chance and ctx.rng(f"galaxy_outburst.{galaxy.id}").chance(chance):
        await open_event(ctx, galaxy, GalacticEventKind.CORE_OUTBURST, table.outburst_radiation)


async def gamma_burst(ctx: TickContext, cosmography: Cosmography, galaxy: GalaxyRow) -> None:
    table = ctx.rules.galaxies
    rng = ctx.rng(f"galaxy_gamma.{galaxy.id}")
    if not rng.chance(table.gamma_chance):
        return
    stars = [star for star in cosmography.stars_in_galaxy(galaxy.id) if not held(star.id)]
    if not stars:
        return
    source = rng.pick(sorted(stars, key=lambda star: star.id))
    await open_event(ctx, galaxy, GalacticEventKind.GAMMA_RAY_BURST, PERCENT, star=source)
    struck = [star for star in stars if math.hypot(star.x - source.x, star.y - source.y) <= table.gamma_reach]
    for star in struck:
        for world in cosmography.worlds.values():
            if held(world.id) or cosmography.place_world(world).star is not star:
                continue
            if "biosphere_health" not in world.locked:
                world.biosphere_health = clamp_percent(world.biosphere_health - table.gamma_biosphere_loss)
            for ground in await ctx.session.scalars(select(RegionEnvironmentRow).where(RegionEnvironmentRow.world_id == world.id)):
                if not held(ground.entity_id) and "soil_fertility" not in ground.locked:
                    ground.soil_fertility = clamp_percent(ground.soil_fertility - table.gamma_fertility_loss)
            for species in await canon(ctx.session, [EntityType.SPECIES], world.id):
                if not held(species.id):
                    scale_stat(ctx.rules, species, "abundance", (PERCENT - table.gamma_cull_pct) / PERCENT)


async def chance_events(ctx: TickContext, cosmography: Cosmography, galaxy: GalaxyRow) -> None:
    table = ctx.rules.galaxies
    rng = ctx.rng(f"galaxy_events.{galaxy.id}")
    stars = sorted((star for star in cosmography.stars_in_galaxy(galaxy.id) if not held(star.id)), key=lambda star: star.id)
    if rng.chance(table.starburst_chance) and unlocked(galaxy, "star_formation"):
        galaxy.star_formation = clamp_percent(galaxy.star_formation + table.starburst_formation)
        await open_event(ctx, galaxy, GalacticEventKind.STARBURST, table.starburst_formation)
    if rng.chance(table.collapse_chance):
        await collapse_cloud(ctx, cosmography, galaxy, rng)
    if stars:
        await star_events(ctx, cosmography, galaxy, stars, rng)
    if galaxy.galaxy_type is GalaxyType.VEILED and rng.chance(table.shrouding_chance) and unlocked(galaxy, "discovery"):
        galaxy.discovery = Discovery.LEGEND
        await open_event(ctx, galaxy, GalacticEventKind.SHROUDING, PERCENT)
    if galaxy.galaxy_type is GalaxyType.SHATTERED and len(stars) > 1 and rng.chance(table.severing_chance):
        await sever(ctx, cosmography, galaxy, stars)


async def collapse_cloud(ctx: TickContext, cosmography: Cosmography, galaxy: GalaxyRow, rng: SeededRandom) -> None:
    table = ctx.rules.galaxies
    x, y = birth_position(rng, GalacticStructureRow(x=0.0, y=0.0, radius=galaxy.radius))
    nursery = GalacticStructureRow(
        galaxy_id=galaxy.id,
        kind=GalacticStructureKind.STELLAR_NURSERY,
        name=await nursery_name(ctx, galaxy),
        x=x,
        y=y,
        radius=galaxy.radius * table.core_reach_pct / PERCENT,
        intensity=table.layout_intensity,
        created_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(nursery)
    await ctx.session.flush()
    cosmography.structures[nursery.id] = nursery
    await open_event(ctx, galaxy, GalacticEventKind.NEBULA_COLLAPSE, nursery.intensity, structure=nursery)


async def star_events(ctx: TickContext, cosmography: Cosmography, galaxy: GalaxyRow, stars: list[StarRow], rng: SeededRandom) -> None:
    table = ctx.rules.galaxies
    if rng.chance(table.strip_chance):
        stream = GalacticStructureRow(
            galaxy_id=galaxy.id,
            kind=GalacticStructureKind.STELLAR_STREAM,
            name=f"Stream of {galaxy.name} {ctx.epoch}",
            x=galaxy.radius * table.halo_reach_pct / PERCENT / 2,
            y=0.0,
            radius=galaxy.radius * table.bulge_reach_pct / PERCENT,
            intensity=table.layout_intensity,
            created_epoch=ctx.epoch,
            locked=[],
        )
        ctx.session.add(stream)
        await ctx.session.flush()
        cosmography.structures[stream.id] = stream
        torn = rng.pick(stars)
        if unlocked(torn, "structure_id"):
            torn.structure_id = stream.id
        await open_event(ctx, galaxy, GalacticEventKind.TIDAL_STRIPPING, table.layout_intensity, star=torn, structure=stream)
    if rng.chance(table.hypervelocity_chance):
        flung = rng.pick(stars)
        if unlocked(flung, "galaxy_id"):
            flung.galaxy_id = None
            settle_star(ctx.rules, cosmography, flung)
            await open_event(ctx, galaxy, GalacticEventKind.HYPERVELOCITY_STAR, PERCENT, star=flung)
    if rng.chance(table.dimming_chance):
        for star in stars:
            if unlocked(star, "brightness"):
                star.brightness = clamp_percent(star.brightness - table.dimming_loss)
        await open_event(ctx, galaxy, GalacticEventKind.GALACTIC_DIMMING, table.dimming_loss)
    if galaxy.galaxy_type is GalaxyType.LIVING and rng.chance(table.awakening_chance):
        for star in stars:
            if unlocked(star, "brightness"):
                star.brightness = clamp_percent(star.brightness + table.awakening_brightness)
        await open_event(ctx, galaxy, GalacticEventKind.AWAKENING, table.awakening_brightness)


async def nursery_name(ctx: TickContext, galaxy: GalaxyRow) -> str:
    count = int(
        await ctx.session.scalar(
            select(GalacticStructureRow.id).where(GalacticStructureRow.galaxy_id == galaxy.id).order_by(GalacticStructureRow.id.desc()).limit(1)
        )
        or 0
    )
    return f"Nursery {count + 1} of {galaxy.name}"


async def sever(ctx: TickContext, cosmography: Cosmography, galaxy: GalaxyRow, stars: list[StarRow]) -> None:
    rng = ctx.rng(f"galaxy_sever.{galaxy.id}")
    shard = await create_galaxy(
        ctx.session,
        ctx.rules,
        GalaxyDraft(
            f"{galaxy.name} Shard",
            rng.pick(SPLIT_TYPES),
            ctx.epoch,
            cluster_id=galaxy.cluster_id,
            dimension_id=galaxy.dimension_id if galaxy.cluster_id is None else None,
            x=galaxy.x + galaxy.radius * 2,
            y=galaxy.y,
            radius=galaxy.radius / 2,
        ),
    )
    cosmography.galaxies[shard.id] = shard
    for star in stars[len(stars) // 2 :]:
        if unlocked(star, "galaxy_id"):
            star.galaxy_id = shard.id
            settle_star(ctx.rules, cosmography, star)
    await open_event(ctx, galaxy, GalacticEventKind.SEVERING, PERCENT, other=shard)


async def break_arms(ctx: TickContext, cosmography: Cosmography, galaxy: GalaxyRow, host: GalaxyRow) -> int:
    rng = ctx.rng(f"merger_arms.{galaxy.id}")
    broken = 0
    for structure in sorted(cosmography.structures.values(), key=lambda row: row.id):
        if structure.galaxy_id not in (galaxy.id, host.id) or structure.ended_epoch is not None or structure.kind not in DISRUPTED_STRUCTURES:
            continue
        if "ended_epoch" in structure.locked or not rng.chance(ctx.rules.galaxies.merger_arm_break):
            continue
        structure.ended_epoch = ctx.epoch
        for star in cosmography.stars.values():
            if star.structure_id == structure.id and unlocked(star, "structure_id") and not held(star.id):
                star.structure_id = None
        broken += 1
        await record(
            ctx,
            "galaxy.arm_broken",
            roles={IncidentRole.SUBJECT: galaxy.id, IncidentRole.DESTINATION: host.id},
            facts={"structure": structure.name, "chance": ctx.rules.galaxies.merger_arm_break},
            steps=(StepDraft(StepAction.COLLIDE, actor=galaxy.id, target=host.id, outcome=StepOutcome.BROKEN),),
        )
    return broken


async def advance_mergers(ctx: TickContext, cosmography: Cosmography, galaxies: list[GalaxyRow]) -> None:
    for galaxy in galaxies:
        if galaxy.merging_with_galaxy_id is None or held(galaxy.id) or galaxy.merge_progress >= PERCENT:
            continue
        host = cosmography.galaxies.get(galaxy.merging_with_galaxy_id)
        if host is None or held(host.id):
            continue
        ctx.count("arms_broken", await break_arms(ctx, cosmography, galaxy, host))
        if unlocked(galaxy, "merge_progress"):
            galaxy.merge_progress = clamp_percent(galaxy.merge_progress + ctx.rules.galaxies.merger_step)
        if galaxy.merge_progress >= PERCENT:
            await absorb(ctx, cosmography, galaxy, host)


def may_merge(ctx: TickContext, cosmography: Cosmography, first: GalaxyRow, second: GalaxyRow) -> bool:
    table = ctx.rules.galaxies
    if first.cluster_id is None or first.cluster_id != second.cluster_id or held(first.id, second.id):
        return False
    if first.merging_with_galaxy_id is not None or second.merging_with_galaxy_id is not None or PERCENT in (first.merge_progress, second.merge_progress):
        return False
    reach = (first.radius + second.radius) * table.merger_reach_pct / PERCENT
    distance = math.hypot(first.x - second.x, first.y - second.y)
    if distance > reach:
        return False
    cluster = cosmography.clusters[first.cluster_id]
    chance = table.merger_chance * CLUSTER_KIND_MECHANICS[cluster.cluster_kind].merger(ctx.rules) / PERCENT
    chance *= 2 * (1 - distance / reach) if reach > 0 else 1
    central = cosmography.central_galaxy(cluster.id)
    if central is not None and central.id in (first.id, second.id):
        chance *= ctx.rules.clusters.central_pull_pct / PERCENT
    return ctx.rng(f"galaxy_merge.{first.id}.{second.id}").chance(min(PERCENT, chance))


async def mergers(ctx: TickContext, cosmography: Cosmography) -> int:
    begun = 0
    galaxies = sorted(cosmography.galaxies.values(), key=lambda row: row.id)
    await advance_mergers(ctx, cosmography, galaxies)
    for index, first in enumerate(galaxies):
        for second in galaxies[index + 1 :]:
            if not may_merge(ctx, cosmography, first, second):
                continue
            small, large = sorted((first, second), key=lambda row: (len(cosmography.stars_in_galaxy(row.id)), row.radius, -row.id))
            if not unlocked(small, "merging_with_galaxy_id"):
                continue
            small.merging_with_galaxy_id = large.id
            small.merge_progress = 0
            await shorten_routes(ctx, cosmography, small, large)
            await open_event(ctx, large, GalacticEventKind.MERGER_BEGUN, ctx.rules.galaxies.merger_burst, other=small)
            begun += 1
    return begun


async def shorten_routes(ctx: TickContext, cosmography: Cosmography, first: GalaxyRow, second: GalaxyRow) -> None:
    ids = {world.id for world in cosmography.worlds_in_galaxy(first.id)}
    others = {world.id for world in cosmography.worlds_in_galaxy(second.id)}
    for route in await ctx.session.scalars(select(RouteRow).order_by(RouteRow.id)):
        if "duration_epochs" in route.locked:
            continue
        if (route.world_a_id in ids and route.world_b_id in others) or (route.world_b_id in ids and route.world_a_id in others):
            route.duration_epochs = max(1, route.duration_epochs - ctx.rules.galaxies.merger_route_cut)


def reshape(ctx: TickContext, cosmography: Cosmography, galaxy: GalaxyRow) -> None:
    kind = GALAXY_TYPE_MECHANICS[galaxy.galaxy_type]
    if unlocked(galaxy, "arm_count"):
        galaxy.arm_count = max(kind.arms_min(ctx.rules), min(kind.arms_max(ctx.rules), galaxy.arm_count))
    spiral = galaxy.galaxy_type in SPIRAL_GALAXIES and galaxy.arm_count > 0
    barred = galaxy.galaxy_type in BARRED_GALAXIES
    for structure in cosmography.structures.values():
        if structure.galaxy_id != galaxy.id or structure.ended_epoch is not None or "ended_epoch" in structure.locked:
            continue
        if (structure.kind is GalacticStructureKind.SPIRAL_ARM and not spiral) or (structure.kind is GalacticStructureKind.BAR and not barred):
            structure.ended_epoch = ctx.epoch
            for star in cosmography.stars.values():
                if star.structure_id == structure.id and unlocked(star, "structure_id") and not held(star.id):
                    star.structure_id = None


async def absorb(ctx: TickContext, cosmography: Cosmography, small: GalaxyRow, large: GalaxyRow) -> None:
    rng = ctx.rng(f"galaxy_absorb.{small.id}")
    disc = GalacticStructureRow(x=0.0, y=0.0, radius=large.radius)
    for star in cosmography.stars_in_galaxy(small.id):
        if held(star.id) or not unlocked(star, "galaxy_id"):
            continue
        star.galaxy_id = large.id
        star.x, star.y = birth_position(rng, disc)
        settle_star(ctx.rules, cosmography, star)
    for structure in list(cosmography.structures.values()):
        if structure.galaxy_id == small.id and structure.ended_epoch is None:
            structure.galaxy_id = large.id
            structure.x, structure.y = birth_position(rng, disc)
    if unlocked(large, "galaxy_type"):
        large.galaxy_type = GalaxyType.ELLIPTICAL if large.galaxy_type is GalaxyType.PECULIAR else GalaxyType.PECULIAR
        reshape(ctx, cosmography, large)
    if unlocked(small, "age_stage"):
        small.age_stage = GalaxyAge.DEAD
    if unlocked(small, "star_formation"):
        small.star_formation = 0
    await open_event(ctx, large, GalacticEventKind.MERGER_COMPLETED, PERCENT, other=small)


async def patrons(ctx: TickContext, cosmography: Cosmography) -> int:
    paid = 0
    for galaxy in cosmography.galaxies.values():
        if galaxy.patron_son_id is None or held(galaxy.id, galaxy.patron_son_id):
            continue
        son = await ctx.session.get(SonRow, galaxy.patron_son_id)
        if son is None:
            continue
        worlds = sum(1 for world in cosmography.worlds_in_galaxy(galaxy.id) if world.patron_son_id == son.id)
        gain = worlds * ctx.rules.galaxies.patron_essence
        if gain:
            paid += endow(ctx.rules, son, gain)
    return paid


async def galaxy_worship(ctx: TickContext, cosmography: Cosmography) -> int:
    devoted = await flags_by_entity(ctx.session, EntityFlag.WORSHIPS_GALAXY)
    lifted = 0
    for community in await canon(ctx.session, COMMUNITY_TYPES):
        if community.id not in devoted or held(community.id):
            continue
        galaxy = cosmography.place_world_id(community.world_id).galaxy
        if galaxy is not None and galaxy.star_formation >= PERCENT // 2:
            shift_bounded(ctx.rules, community, "piety", ctx.rules.galaxies.worship_piety)
            lifted += 1
    return lifted


async def galaxy_cults(ctx: TickContext, cosmography: Cosmography) -> int:
    stirred = set(await ctx.session.scalars(select(GalacticEventRow.galaxy_id).where(GalacticEventRow.epoch == ctx.epoch)))
    if not stirred:
        return 0
    devoted = await flags_by_entity(ctx.session, EntityFlag.WORSHIPS_GALAXY)
    rng = ctx.rng("galaxy_cults")
    risen = 0
    for community in sorted(await canon(ctx.session, COMMUNITY_TYPES), key=lambda row: row.id):
        if community.id in devoted or held(community.id):
            continue
        galaxy = cosmography.place_world_id(community.world_id).galaxy
        if galaxy is None or galaxy.id not in stirred or not rng.chance(ctx.rules.galaxies.cult_chance):
            continue
        await EntityRepository(ctx.session).add_flag(community.id, EntityFlag.WORSHIPS_GALAXY, ctx.epoch)
        await record(
            ctx,
            "galaxy.cult_risen",
            roles={IncidentRole.ACTOR: community.id, IncidentRole.SUBJECT: galaxy.id},
            facts={"chance": ctx.rules.galaxies.cult_chance},
        )
        risen += 1
    return risen


async def cluster_drift(ctx: TickContext, cosmography: Cosmography) -> int:
    stretched = 0
    cap = ctx.rules.clusters.expansion_cap
    for route in await ctx.session.scalars(select(RouteRow).where(RouteRow.active.is_(True)).order_by(RouteRow.id)):
        if "duration_epochs" in route.locked or held(route.world_a_id, route.world_b_id):
            continue
        if cosmography.scope_by_id(route.world_a_id, route.world_b_id) is not RouteScope.INTERCLUSTER:
            continue
        first = cosmography.place_world_id(route.world_a_id).top_cluster
        second = cosmography.place_world_id(route.world_b_id).top_cluster
        expansion = max(first.expansion if first is not None else 0, second.expansion if second is not None else 0)
        if not expansion or route.duration_epochs >= travel_method_profile(ctx.rules, route.method).duration_epochs + cap:
            continue
        if ctx.rng(f"cluster_drift.{route.id}").chance(expansion):
            route.duration_epochs += 1
            stretched += 1
    return stretched


async def cluster_worship(ctx: TickContext, cosmography: Cosmography, grown: set[int]) -> int:
    devoted = await flags_by_entity(ctx.session, EntityFlag.WORSHIPS_GALAXY)
    counts: Counter[int] = Counter()
    for galaxy_id in sorted(grown):
        home = cosmography.galaxies[galaxy_id].cluster_id
        if home is not None:
            counts[home] += 1
    lifted = 0
    for community in await canon(ctx.session, COMMUNITY_TYPES):
        if community.id not in devoted or held(community.id):
            continue
        cluster = cosmography.place_world_id(community.world_id).cluster
        if cluster is not None and counts[cluster.id]:
            shift_bounded(ctx.rules, community, "piety", ctx.rules.clusters.worship_piety * counts[cluster.id])
            lifted += 1
    return lifted


@reads(
    "table.cosmos",
    "table.creator",
    "table.dimensional_events",
    "table.dimensions",
    "table.entities",
    "table.entity_flags",
    "table.foreign_gods",
    "table.galactic_events",
    "table.galactic_structures",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.name_registry",
    "table.node_births",
    "table.nodes",
    "table.routes",
    "table.sons",
    "table.stars",
    "table.worlds",
)
@writes(
    "table.chronicle",
    "table.entity_flags",
    "table.galactic_events",
    "table.galactic_structures",
    "table.galaxies",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
    "table.name_registry",
    "table.node_births",
    "table.stars",
)
async def galaxy_cycles(ctx: TickContext) -> None:
    cosmography = await Cosmography.load(ctx.session)
    grown: set[int] = set()
    for galaxy in sorted(cosmography.galaxies.values(), key=lambda row: row.id):
        if held(galaxy.id) or galaxy.merge_progress >= PERCENT:
            continue
        before = galaxy.star_formation
        await drift_formation(ctx, cosmography, galaxy)
        if galaxy.star_formation > before:
            grown.add(galaxy.id)
        await age_galaxy(ctx, galaxy)
        ctx.count("stars_born", await bear_stars(ctx, cosmography, galaxy))
        await nucleus_outburst(ctx, galaxy)
        await gamma_burst(ctx, cosmography, galaxy)
        await chance_events(ctx, cosmography, galaxy)
    ctx.count("mergers_begun", await mergers(ctx, cosmography))
    ctx.count("patron_essence", await patrons(ctx, cosmography))
    ctx.count("galaxy_cults", await galaxy_cults(ctx, cosmography))
    ctx.count("galaxy_worship", await galaxy_worship(ctx, cosmography))
    ctx.count("cluster_worship", await cluster_worship(ctx, cosmography, grown))
    ctx.count("routes_stretched", await cluster_drift(ctx, cosmography))
    await ctx.session.flush()


def outburst_radiation(events: list[GalacticEventRow], galaxy_id: int | None, zone: GalacticZone, epoch: int) -> int:
    if galaxy_id is None or zone not in (GalacticZone.CORE, GalacticZone.BULGE):
        return 0
    return max(
        (event.intensity for event in events if event.galaxy_id == galaxy_id and event.kind is GalacticEventKind.CORE_OUTBURST and active(event, epoch)),
        default=0,
    )


async def active_events(ctx: TickContext) -> list[GalacticEventRow]:
    statement = (
        select(GalacticEventRow).where((GalacticEventRow.until_epoch.is_(None)) | (GalacticEventRow.until_epoch >= ctx.epoch)).order_by(GalacticEventRow.id)
    )
    return list(await ctx.session.scalars(statement))
