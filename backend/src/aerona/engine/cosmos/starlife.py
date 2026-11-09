from collections import Counter

from sqlalchemy import select

from aerona.catalog.cosmography import STAR_AGE_LABELS
from aerona.constants.units import PERCENT
from aerona.db.tables.celestial import SkyEventRow, StarRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.cosmography import StarAge
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityFlag
from aerona.domain.enums.world import SkyEventKind, StarType
from aerona.engine.context import TickContext
from aerona.engine.cosmos.galaxies import active_events, outburst_radiation
from aerona.engine.cosmos.kinds import STRUCTURE_MECHANICS, ZONE_MECHANICS
from aerona.engine.cosmos.placement import Cosmography
from aerona.engine.cosmos.star_types import star_mechanics
from aerona.engine.cosmos.stars import supernova
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_percent, round_half_up
from aerona.engine.primitives.queries import canon, flags_by_entity
from aerona.engine.primitives.stats import shift_bounded
from aerona.rules.registry import Rules

NEXT_STAGE: dict[StarAge, StarAge] = {StarAge.YOUNG: StarAge.MAIN, StarAge.MAIN: StarAge.OLD, StarAge.OLD: StarAge.DYING, StarAge.REBORN: StarAge.MAIN}
SPENT_REMNANT = StarType.WHITE_DWARF


def heavy(rules: Rules, star: StarRow) -> bool:
    return star_mechanics(star.star_type).collapse_weight(rules) > 0


def stage_epochs(rules: Rules, star: StarRow, stage: StarAge) -> int | None:
    table = rules.star_life
    base = {
        StarAge.YOUNG: table.young_epochs,
        StarAge.MAIN: table.main_epochs,
        StarAge.OLD: table.old_epochs,
        StarAge.DYING: table.dying_epochs,
        StarAge.REBORN: table.young_epochs,
    }.get(stage)
    if base is None:
        return None
    return max(1, round_half_up(base * table.heavy_life_pct / PERCENT) if heavy(rules, star) else base)


def stage_radiation(rules: Rules, stage: StarAge) -> int:
    table = rules.star_life
    return {
        StarAge.YOUNG: table.young_radiation,
        StarAge.MAIN: table.main_radiation,
        StarAge.OLD: table.main_radiation,
        StarAge.DYING: table.dying_radiation,
        StarAge.DEAD: 0,
        StarAge.REBORN: table.young_radiation,
    }[stage]


def stage_stability(rules: Rules, stage: StarAge) -> int:
    table = rules.star_life
    return {
        StarAge.YOUNG: table.young_stability,
        StarAge.MAIN: table.main_stability,
        StarAge.OLD: table.old_stability,
        StarAge.DYING: table.dying_stability,
        StarAge.DEAD: table.main_stability,
        StarAge.REBORN: table.young_stability,
    }[stage]


async def pass_stage(ctx: TickContext, star: StarRow) -> None:
    if star.age_stage is StarAge.DYING:
        if heavy(ctx.rules, star) and ctx.rng(f"star_death.{star.id}").chance(ctx.rules.star_life.supernova_chance):
            text = await supernova(ctx, star)
            await note(ctx, text, key="sky.supernova", kind=ChronicleKind.SKY)
        elif "star_type" not in star.locked:
            star.star_type = SPENT_REMNANT
        star.age_stage = StarAge.DEAD
        star.lifecycle_clock = None
        await note(ctx, f"{star.name} reached the end of its life.", key="star.died", kind=ChronicleKind.SKY)
        return
    following = NEXT_STAGE.get(star.age_stage)
    if following is None:
        star.lifecycle_clock = None
        return
    star.age_stage = following
    star.lifecycle_clock = stage_epochs(ctx.rules, star, following)
    await note(ctx, f"{star.name} entered its {STAR_AGE_LABELS[following].lower()} age.", key=f"star.stage.{following.value}", kind=ChronicleKind.SKY)


async def age_star(ctx: TickContext, star: StarRow) -> None:
    table = ctx.rules.star_life
    if "age_stage" in star.locked or "lifecycle_clock" in star.locked:
        return
    if star.lifecycle_clock is None:
        star.lifecycle_clock = stage_epochs(ctx.rules, star, star.age_stage)
        return
    star.lifecycle_clock = max(0, star.lifecycle_clock - 1)
    if star.lifecycle_clock == 0:
        await pass_stage(ctx, star)
    if "brightness" in star.locked:
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


@reads("table.cosmos", "table.dimensional_events", "table.entity_flags", "table.galactic_events", "table.galactic_structures", "table.sky_events")
@writes("table.stars")
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
    for star in sorted(cosmography.stars.values(), key=lambda row: row.id):
        if held(star.id):
            continue
        before = star.brightness
        await age_star(ctx, star)
        dimmed[star.id] = max(0, before - star.brightness)
        if "stability" not in star.locked:
            target = stage_stability(ctx.rules, star.age_stage)
            star.stability = clamp_percent(star.stability + max(-table.stability_drift, min(table.stability_drift, target - star.stability)))
        if "radiation" not in star.locked:
            star.radiation = radiate(
                ctx.rules, cosmography, star, outburst_radiation(events, star.galaxy_id, star.galactic_zone, ctx.epoch), star.id in flaring
            )
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
