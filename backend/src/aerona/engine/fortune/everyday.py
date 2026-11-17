from collections.abc import Mapping
from dataclasses import dataclass

from aerona.constants.units import PERCENT
from aerona.core.grammar import an, spoken
from aerona.core.random import SeededRandom
from aerona.core.total import total
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import DamageType, HarmCause
from aerona.domain.enums.entity import EntityStatus, EntityType, MortalRole
from aerona.domain.enums.folkways import MishapKind
from aerona.domain.enums.mortal import LifeStage
from aerona.engine.body.customs import people_id_of
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import points_of, shift_points
from aerona.engine.fortune.profiles import draw_shift, fortune_of
from aerona.engine.kinds.crafts_life import Exposure, exposure_of
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.mortal.standing import add_stress
from aerona.engine.primitives.naming import seed_of

PER_MIL = 1000
FRAIL = frozenset({LifeStage.INFANT, LifeStage.CHILD, LifeStage.ELDER, LifeStage.ANCIENT})
DANGEROUS = frozenset(
    {MortalRole.WARRIOR, MortalRole.SWORN_WARRIOR, MortalRole.HUNTER, MortalRole.EXPLORER, MortalRole.CAPTAIN, MortalRole.PILOT, MortalRole.ENGINEER}
)
HARMED: Mapping[MishapKind, DamageType | None] = total(
    MishapKind,
    {
        MishapKind.ILLNESS: None,
        MishapKind.CROP_FAILURE: None,
        MishapKind.CHILD_DEATH: None,
        MishapKind.LIVESTOCK_DEATH: None,
        MishapKind.ACCIDENT: DamageType.BLUNT,
        MishapKind.BAD_LUCK: None,
        MishapKind.FALL: DamageType.BLUNT,
        MishapKind.CRUSH: DamageType.BLUNT,
        MishapKind.CUT: DamageType.CUT,
        MishapKind.BURN: DamageType.FIRE,
        MishapKind.SCALD: DamageType.FIRE,
        MishapKind.DROWNING: DamageType.COLD,
        MishapKind.BEAST: DamageType.PIERCE,
        MishapKind.TOOL: DamageType.CUT,
        MishapKind.MACHINE: DamageType.CUT,
        MishapKind.VEHICLE: DamageType.BLUNT,
        MishapKind.COLLAPSE: DamageType.BLUNT,
        MishapKind.HOUSE_FIRE: DamageType.FIRE,
        MishapKind.POISONING: DamageType.CHEMICAL,
        MishapKind.CHOKING: DamageType.BLUNT,
        MishapKind.EXPOSURE: DamageType.COLD,
        MishapKind.LIGHTNING: DamageType.ELECTRIC,
        MishapKind.SPORT: DamageType.BLUNT,
        MishapKind.BRAWL: DamageType.BLUNT,
        MishapKind.LOST_WAY: None,
        MishapKind.STORES_SPOILED: None,
        MishapKind.GOODS_LOST: None,
        MishapKind.PURSE_LOST: None,
        MishapKind.THEFT_SUFFERED: None,
        MishapKind.TOOL_BROKEN: None,
        MishapKind.NEAR_MISS: None,
    },
)
LOSSES = frozenset({MishapKind.STORES_SPOILED, MishapKind.GOODS_LOST, MishapKind.PURSE_LOST, MishapKind.THEFT_SUFFERED, MishapKind.TOOL_BROKEN})
FRIGHTS = frozenset({MishapKind.NEAR_MISS, MishapKind.LOST_WAY})
EVERYDAY = (
    MishapKind.FALL,
    MishapKind.CUT,
    MishapKind.BURN,
    MishapKind.SCALD,
    MishapKind.CRUSH,
    MishapKind.BEAST,
    MishapKind.TOOL,
    MishapKind.VEHICLE,
    MishapKind.COLLAPSE,
    MishapKind.HOUSE_FIRE,
    MishapKind.POISONING,
    MishapKind.CHOKING,
    MishapKind.DROWNING,
    MishapKind.SPORT,
    MishapKind.BRAWL,
    MishapKind.LOST_WAY,
    MishapKind.STORES_SPOILED,
    MishapKind.GOODS_LOST,
    MishapKind.PURSE_LOST,
    MishapKind.THEFT_SUFFERED,
    MishapKind.TOOL_BROKEN,
    MishapKind.NEAR_MISS,
)
WORKING = (MishapKind.TOOL, MishapKind.MACHINE, MishapKind.CRUSH, MishapKind.COLLAPSE, MishapKind.BEAST)
CHILDHOOD = (MishapKind.FALL, MishapKind.DROWNING, MishapKind.BURN, MishapKind.SCALD, MishapKind.CHOKING, MishapKind.POISONING)
WEATHER = (MishapKind.EXPOSURE, MishapKind.LIGHTNING)
SPORTING = (MishapKind.SPORT, MishapKind.BRAWL)
UNEXPOSED = Exposure()


@dataclass(frozen=True)
class Mishap:
    kind: MishapKind
    victim: int
    severity: int
    died: bool
    cause: str


def rate_of(ctx: TickContext, stage: LifeStage | None, role: MortalRole | None, fortune: int, exposure: Exposure = UNEXPOSED) -> float:
    table = ctx.rules.everyday_mishaps
    rate = PERCENT / PERCENT
    if stage in FRAIL:
        rate *= table.young_old_pct / PERCENT
    if role in DANGEROUS:
        rate *= table.dangerous_work_pct / PERCENT
    if ctx.epoch % 4 == 3:
        rate *= table.winter_pct / PERCENT
        shortfall = max(0, ctx.rules.dress.cold_warmth - exposure.warmth) if exposure.dressed else 0
        rate *= 1 + shortfall * ctx.rules.dress.exposure_pct / PERCENT / PERCENT
    rate *= 1 + exposure.wear * ctx.rules.household_goods.wear_pct / PERCENT / PERCENT
    rate *= 1 + exposure.violence * ctx.rules.games.violence_pct / PERCENT / PERCENT
    return rate * (2 - draw_shift(ctx, fortune))


def kinds_for(stage: LifeStage | None, role: MortalRole | None, cold: bool, exposure: Exposure = UNEXPOSED) -> tuple[MishapKind, ...]:
    pool = list(EVERYDAY)
    if stage in FRAIL:
        pool += CHILDHOOD
    if role in DANGEROUS or exposure.wear > 0:
        pool += WORKING
    if cold:
        pool += WEATHER
    if exposure.violence > 0:
        pool += SPORTING
    return tuple(pool)


def grade(ctx: TickContext, rng: SeededRandom, rate: float) -> tuple[int, int] | None:
    table = ctx.rules.everyday_mishaps
    roll = rng.random() * PER_MIL
    if roll < table.deadly_per_mil * rate:
        return 3, table.deadly_damage
    if roll < (table.deadly_per_mil + table.grave_per_mil) * rate:
        return 2, table.grave_damage
    if roll < (table.deadly_per_mil + table.grave_per_mil) * rate + table.small_per_epoch * PER_MIL // PERCENT * rate:
        return 1, table.small_damage
    return None


async def exposure_for(ctx: TickContext, mortal: EntityRow, known: dict[int, Exposure]) -> Exposure:
    people = await people_id_of(ctx.session, mortal)
    if people is None:
        return UNEXPOSED
    if people not in known:
        known[people] = await exposure_of(ctx, people)
    return known[people]


async def befall(ctx: TickContext, mortal: EntityRow, exposure: Exposure = UNEXPOSED) -> Mishap | None:
    profile = await ctx.session.get(MortalProfileRow, mortal.id)
    stage = profile.life_stage if profile is not None else None
    fortune = await fortune_of(ctx, mortal.id)
    rng = ctx.rng(seed_of("everyday", mortal.id, ctx.epoch))
    graded = grade(ctx, rng, rate_of(ctx, stage, mortal.mortal_role, fortune, exposure))
    if graded is None:
        return None
    level, damage = graded
    kind = rng.pick(list(kinds_for(stage, mortal.mortal_role, ctx.epoch % 4 == 3, exposure)))
    table = ctx.rules.everyday_mishaps
    died = False
    if kind in LOSSES:
        if await points_of(ctx.session, mortal) > 0:
            await shift_points(ctx.session, mortal, -table.loss_wealth * level)
    elif kind in FRIGHTS or HARMED[kind] is None:
        await add_stress(ctx.session, mortal.id, table.small_stress * level, ctx.epoch)
    else:
        words = kind.value.replace("_", " ")
        wounded = await apply_hits(ctx, mortal, Harm(float(damage), HarmCause.ACCIDENT, an(words), damage_type=HARMED[kind]))
        died = mortal.status is not EntityStatus.CANON
        level = max(level, max((row.severity for row in wounded.injuries), default=0) // 2)
    return Mishap(kind, mortal.id, level, died, f"{spoken(kind)} in daily life")


async def everyday(ctx: TickContext, folk: list[int]) -> list[Mishap]:
    found: list[Mishap] = []
    known: dict[int, Exposure] = {}
    for mortal_id in folk:
        mortal = await ctx.session.get(EntityRow, mortal_id)
        if mortal is None or mortal.entity_type is not EntityType.MORTAL or mortal.status is not EntityStatus.CANON or held(mortal.id):
            continue
        happened = await befall(ctx, mortal, await exposure_for(ctx, mortal, known))
        if happened is not None:
            found.append(happened)
    return found


async def trigger(ctx: TickContext, victim: EntityRow, kind: MishapKind, level: int) -> Mishap:
    table = ctx.rules.everyday_mishaps
    damage = (table.small_damage, table.grave_damage, table.deadly_damage)[max(1, min(3, level)) - 1]
    died = False
    severity = level
    if kind in LOSSES:
        if await points_of(ctx.session, victim) > 0:
            await shift_points(ctx.session, victim, -table.loss_wealth * level)
    elif kind in FRIGHTS or HARMED[kind] is None:
        await add_stress(ctx.session, victim.id, table.small_stress * level, ctx.epoch)
    else:
        wounded = await apply_hits(ctx, victim, Harm(float(damage), HarmCause.ACCIDENT, an(kind.value.replace("_", " ")), damage_type=HARMED[kind]))
        died = victim.status is not EntityStatus.CANON
        severity = max(level, max((row.severity for row in wounded.injuries), default=0) // 2)
    return Mishap(kind, victim.id, severity, died, "brought about by a god's hand")
