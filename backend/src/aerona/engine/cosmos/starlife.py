from collections import Counter

from sqlalchemy import select

from aerona.catalog.cosmography import STAR_AGE_LABELS
from aerona.catalog.kinds.stars import STAR_AGES
from aerona.constants.units import PERCENT
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.celestial import SkyEventRow, StarRow
from aerona.db.tables.physics import StarPhysicsRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.transform import StarModifierRow
from aerona.db.write_guard import held
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.cosmography import GalaxyAge, StarAge
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityFlag
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.world import SkyEventKind
from aerona.engine.context import TickContext
from aerona.engine.cosmos.catastrophe import scorch_world
from aerona.engine.cosmos.galaxies import active_events, outburst_radiation
from aerona.engine.cosmos.kinds import STRUCTURE_MECHANICS, ZONE_MECHANICS
from aerona.engine.cosmos.placement import Cosmography
from aerona.engine.cosmos.stars import supernova, worlds_of_star
from aerona.engine.cosmos.stellar import (
    drift_brightness,
    drift_metallicity,
    ends_in_supernova,
    engulf_orbit,
    giant_for,
    is_dwarf,
    luminosity_shifts,
    physics_of_stars,
    refresh,
    remnant_for,
    stage_length,
    typical_mass,
)
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_percent, round_half_up
from aerona.engine.primitives.queries import canon, flags_by_entity
from aerona.engine.primitives.stats import shift_bounded
from aerona.rules.registry import Rules

NEXT_STAGE: dict[StarAge, StarAge] = {StarAge.YOUNG: StarAge.MAIN, StarAge.MAIN: StarAge.OLD, StarAge.OLD: StarAge.DYING, StarAge.REBORN: StarAge.MAIN}
BRIGHT_SKY = PERCENT * 4 // 5


def stage_epochs(rules: Rules, star: StarRow, stage: StarAge, physics: StarPhysicsRow | None = None) -> int | None:
    mass = physics.mass if physics is not None else typical_mass(rules, star.star_type)
    return stage_length(rules, mass, stage)


def stage_radiation(rules: Rules, stage: StarAge) -> int:
    rule_name = STAR_AGES[stage].radiation_rule
    return int(getattr(rules.star_life, rule_name)) if rule_name is not None else 0


def stage_stability(rules: Rules, stage: StarAge) -> int:
    return int(getattr(rules.star_life, STAR_AGES[stage].stability_rule))


async def swell(ctx: TickContext, star: StarRow, physics: StarPhysicsRow | None) -> None:
    mass = physics.mass if physics is not None else typical_mass(ctx.rules, star.star_type)
    giant = giant_for(ctx.rules, mass)
    if giant is None or "star_type" in star.locked:
        return
    star.star_type = giant
    reach = engulf_orbit(ctx.rules, mass)
    await note(ctx, f"{star.name} swelled into a giant.", key="star.swelled", kind=ChronicleKind.SKY)
    for world in sorted(await worlds_of_star(ctx.session, star.id), key=lambda row: row.id):
        if world.parent_world_id is None and world.orbit < reach:
            await scorch_world(ctx, world, f"The swelling of {star.name} swallowed")


async def die(ctx: TickContext, star: StarRow, physics: StarPhysicsRow | None) -> None:
    mass = physics.mass if physics is not None else typical_mass(ctx.rules, star.star_type)
    if physics is not None and physics.maker_son_id is not None:
        physics.maker_son_id = None
    if ends_in_supernova(ctx.rules, mass):
        text = await supernova(ctx, star)
        await note(ctx, text, key="sky.supernova", kind=ChronicleKind.SKY)
    if "star_type" not in star.locked:
        star.star_type = remnant_for(ctx.rules, mass)
    star.age_stage = StarAge.DEAD
    star.lifecycle_clock = None
    await note(ctx, f"{star.name} reached the end of its life.", key="star.died", kind=ChronicleKind.SKY)


async def pass_stage(ctx: TickContext, star: StarRow, physics: StarPhysicsRow | None = None) -> None:
    if star.age_stage is StarAge.DYING:
        await die(ctx, star, physics)
        return
    following = NEXT_STAGE.get(star.age_stage)
    if following is None:
        star.lifecycle_clock = None
        return
    star.age_stage = following
    star.lifecycle_clock = stage_epochs(ctx.rules, star, following, physics)
    await note(ctx, f"{star.name} entered its {STAR_AGE_LABELS[following].lower()} age.", key=f"star.stage.{following.value}", kind=ChronicleKind.SKY)
    if following is StarAge.OLD:
        await swell(ctx, star, physics)


async def keep_divine(ctx: TickContext, star: StarRow, physics: StarPhysicsRow | None) -> bool:
    if physics is None or physics.maker_son_id is None:
        return False
    table = ctx.rules.stellar_evolution
    maker = await ctx.session.get(SonRow, physics.maker_son_id)
    upkeep = table.divine_upkeep
    if maker is None or maker.status is SonStatus.DEAD or held(maker.id) or maker.essence < upkeep:
        physics.maker_son_id = None
        physics.upkeep = 0
        await note(ctx, f"{star.name} fell back under the laws of its kind.", key="star.divine_lapsed", kind=ChronicleKind.SKY)
        return False
    maker.essence -= upkeep
    physics.upkeep = upkeep
    if "stability" not in star.locked:
        star.stability = clamp_percent(round_half_up(maker.existence * table.divine_steadiness_pct / PERCENT))
    return True


async def age_star(ctx: TickContext, star: StarRow, pace_pct: int = PERCENT, physics: StarPhysicsRow | None = None) -> None:
    table = ctx.rules.star_life
    if "age_stage" in star.locked or "lifecycle_clock" in star.locked:
        return
    if physics is not None and "age_epochs" not in physics.locked:
        physics.age_epochs += 1
    if await keep_divine(ctx, star, physics):
        return
    for shift in await ctx.session.scalars(select(StarModifierRow).where(StarModifierRow.star_id == star.id, StarModifierRow.aged.is_(False))):
        if star.lifecycle_clock is not None:
            star.lifecycle_clock = max(0, star.lifecycle_clock - shift.age_epochs)
        shift.aged = True
    if star.lifecycle_clock is None:
        star.lifecycle_clock = stage_epochs(ctx.rules, star, star.age_stage, physics)
        return
    hurried = 1 if pace_pct < PERCENT and ctx.rng(f"star_pace.{star.id}").chance(PERCENT - pace_pct) else 0
    star.lifecycle_clock = max(0, star.lifecycle_clock - 1 - hurried)
    if star.lifecycle_clock == 0:
        await pass_stage(ctx, star, physics)
    mass = physics.mass if physics is not None else typical_mass(ctx.rules, star.star_type)
    if "brightness" in star.locked or not is_dwarf(ctx.rules, mass):
        return
    if star.age_stage is StarAge.OLD:
        star.brightness = clamp_percent(star.brightness - table.old_dimming)
    elif star.age_stage is StarAge.DYING:
        star.brightness = clamp_percent(star.brightness - table.dying_dimming)


def radiate(rules: Rules, cosmography: Cosmography, star: StarRow, outburst: int, flaring: bool) -> int:
    zone = ZONE_MECHANICS[star.galactic_zone].radiation(rules) if star.galaxy_id is not None else 0
    structure = cosmography.structures.get(star.structure_id) if star.structure_id is not None else None
    lit = (
        round(STRUCTURE_MECHANICS[structure.kind].radiation(rules) * structure.intensity / PERCENT)
        if structure is not None and structure.ended_epoch is None
        else 0
    )
    flare = rules.star_life.flare_radiation if flaring else 0
    return clamp_percent(stage_radiation(rules, star.age_stage) + zone + lit + outburst + flare)


async def worship(ctx: TickContext, cosmography: Cosmography, dimmed: dict[int, int]) -> Counter[int]:
    table = ctx.rules.star_life
    devoted = await flags_by_entity(ctx.session, EntityFlag.WORSHIPS_STAR)
    worshippers: Counter[int] = Counter()
    for community in await canon(ctx.session, COMMUNITY_TYPES):
        if community.id not in devoted:
            continue
        star = cosmography.place_world_id(community.world_id).star
        if star is None:
            continue
        worshippers[star.id] += 1
        if held(community.id):
            continue
        shift_bounded(ctx.rules, community, "piety", (star.brightness - PERCENT // 2) // 10 * table.worship_piety)
        if dimmed.get(star.id, 0) >= table.dimming_crisis:
            shift_bounded(ctx.rules, community, "piety", -table.crisis_piety)
    for star_id, loss in dimmed.items():
        if loss >= table.dimming_crisis and worshippers[star_id]:
            star = cosmography.stars[star_id]
            await note(
                ctx, f"{star.name} dimmed, and those who worship it fell into a crisis of faith.", key="star.crisis_of_faith", kind=ChronicleKind.WORSHIP
            )
    return worshippers


async def star_cults(ctx: TickContext, cosmography: Cosmography, dimmed: dict[int, int], flaring: set[int | None]) -> int:
    table = ctx.rules.star_life
    devoted = await flags_by_entity(ctx.session, EntityFlag.WORSHIPS_STAR)
    rng = ctx.rng("star_cults")
    risen = 0
    for community in sorted(await canon(ctx.session, COMMUNITY_TYPES), key=lambda row: row.id):
        if community.id in devoted or held(community.id):
            continue
        star = cosmography.place_world_id(community.world_id).star
        if star is None:
            continue
        stirred = star.id in flaring or dimmed.get(star.id, 0) >= table.dimming_crisis or star.brightness >= BRIGHT_SKY
        if not stirred or not rng.chance(table.cult_chance):
            continue
        await EntityRepository(ctx.session).add_flag(community.id, EntityFlag.WORSHIPS_STAR, ctx.epoch)
        await note(ctx, f"{community.name} came to worship {star.name}.", key="star.cult_risen", ids=[community.id], kind=ChronicleKind.WORSHIP)
        risen += 1
    return risen


@reads(
    "table.cosmos",
    "table.dimensional_events",
    "table.dimensions",
    "table.entity_flags",
    "table.galactic_events",
    "table.galactic_structures",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.nodes",
    "table.sky_events",
    "table.star_modifiers",
    "table.star_physics",
    "table.stars",
    "table.worlds",
)
@writes("table.entity_flags", "table.star_physics", "table.stars")
async def star_lives(ctx: TickContext) -> None:
    table = ctx.rules.star_life
    cosmography = await Cosmography.load(ctx.session)
    events = await active_events(ctx)
    flaring = set(
        await ctx.session.scalars(
            select(SkyEventRow.star_id).where(
                SkyEventRow.kind == SkyEventKind.FLARE,
                (SkyEventRow.until_epoch.is_(None)) | (SkyEventRow.until_epoch >= ctx.epoch),
                SkyEventRow.star_id.is_not(None),
            )
        )
    )
    dimmed: dict[int, int] = {}
    physics_rows = await physics_of_stars(ctx.session, ctx.rules, list(cosmography.stars.values()))
    shifts = await luminosity_shifts(ctx.session)
    for star in sorted(cosmography.stars.values(), key=lambda row: row.id):
        if held(star.id):
            continue
        before = star.brightness
        galaxy = cosmography.galaxies.get(star.galaxy_id) if star.galaxy_id is not None else None
        dying = galaxy is not None and galaxy.age_stage in (GalaxyAge.DYING, GalaxyAge.DEAD)
        physics = physics_rows.get(star.id)
        await age_star(ctx, star, table.dying_galaxy_life_pct if dying else PERCENT, physics)
        if physics is not None:
            refresh(ctx.rules, star, physics, shifts.get(star.id, 0))
            drift_brightness(ctx.rules, star, physics)
            drift_metallicity(ctx.rules, star, physics, galaxy)
        dimmed[star.id] = max(0, before - star.brightness)
        if "stability" not in star.locked:
            target = stage_stability(ctx.rules, star.age_stage)
            star.stability = clamp_percent(star.stability + max(-table.stability_drift, min(table.stability_drift, target - star.stability)))
        if "radiation" not in star.locked:
            star.radiation = radiate(
                ctx.rules, cosmography, star, outburst_radiation(events, star.galaxy_id, star.galactic_zone, ctx.epoch), star.id in flaring
            )
    ctx.count("star_cults", await star_cults(ctx, cosmography, dimmed, flaring))
    worshippers = await worship(ctx, cosmography, dimmed)
    for star in cosmography.stars.values():
        if held(star.id):
            continue
        if "sacredness" not in star.locked:
            star.sacredness = clamp_percent(worshippers[star.id] * table.sacredness_per)
        if star.patron_son_id is not None and worshippers[star.id] and not held(star.patron_son_id):
            son = await ctx.session.get(SonRow, star.patron_son_id)
            if son is not None:
                son.essence += worshippers[star.id] * table.patron_essence
    await ctx.session.flush()


def flare_weight_pct(rules: Rules, star: StarRow) -> float:
    return 1 + max(0, rules.star_life.main_stability - star.stability) / PERCENT * rules.star_life.stability_flare_pct / PERCENT
