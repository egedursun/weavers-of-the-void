from collections.abc import Mapping
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified, instance_state

from aerona.catalog.commodities import COMMODITIES, FOOD_KINDS
from aerona.catalog.life.demography import APPLY_SHORTFALLS_SHORTFALL_EFFECTS
from aerona.catalog.needs import SERVE_ORDER, SHORTFALL_EFFECTS, basket_weight
from aerona.constants.units import PERCENT
from aerona.db.tables.demography import PeopleBiologyRow, PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.society_depth import ClassStandingRow, CommunityNeedRow
from aerona.domain.enums.demography import AgeBand, CohortCondition
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import TemperatureBand
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.society import Commodity, SocialClass
from aerona.domain.enums.society_depth import ShortfallEffect
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.demography.biology import edible
from aerona.engine.demography.cohorts import cohorts_of, row_for
from aerona.engine.economy.household import Meal, Wear
from aerona.engine.economy.stocks import goods_of, holding
from aerona.engine.industry.cold import frostbite
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.primitives.kept import kept_rows
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.prosperity import add_prosperity
from aerona.engine.primitives.stats import set_stats, shift_stat, stat
from aerona.engine.primitives.transfers import move_amount
from aerona.engine.recording.record import record
from aerona.rules.registry import Rules

E = ShortfallEffect
COLD_BANDS = frozenset({TemperatureBand.FROZEN, TemperatureBand.COLD})
WARM_BANDS = frozenset({TemperatureBand.WARM, TemperatureBand.HOT})
PLENTY_CLASSES = (SocialClass.NOBLE, SocialClass.MERCHANT)
LUXURY_CAP = PERCENT * 10
NeedKey = tuple[SocialClass, CommodityKind]


NEED_COLUMNS = ("wanted", "got", "epoch")


@dataclass(frozen=True)
class ClassNeed:
    fed_pct: int = PERCENT
    needs_met_pct: int = PERCENT
    luxury_pct: int = PERCENT
    staple_short_pct: int = 0
    effects: dict[ShortfallEffect, int] = field(default_factory=dict)


@dataclass(frozen=True)
class Basket:
    rows: dict[NeedKey, tuple[int, int]] = field(default_factory=dict)
    classes: dict[SocialClass, ClassNeed] = field(default_factory=dict)
    effects: dict[ShortfallEffect, int] = field(default_factory=dict)


def short_pct(wanted: int, got: int) -> int:
    return clamp_int(round_half_up((wanted - min(wanted, got)) * PERCENT / wanted), 0, PERCENT) if wanted > 0 else 0


async def staples_of(session: AsyncSession, community: EntityRow) -> tuple[CommodityKind, ...]:
    people = await people_of(session, community)
    if people is None:
        return ()
    culture = await session.get(PeopleCultureRow, people.id)
    biology = await session.get(PeopleBiologyRow, people.id)
    kinds: list[CommodityKind] = []
    for value in [*(culture.staples if culture is not None else []), *([biology.staple.value] if biology is not None else [])]:
        try:
            kind = CommodityKind(value)
        except ValueError:
            continue
        if kind in FOOD_KINDS and kind not in kinds and (biology is None or kind in edible(biology.diet)):
            kinds.append(kind)
    return tuple(kinds)


def class_weights(shares: Mapping[SocialClass, float], kind: CommodityKind) -> dict[SocialClass, float]:
    effect = SHORTFALL_EFFECTS[kind]
    return {social_class: max(0.0, shares.get(social_class, 0.0)) * basket_weight(effect, social_class) for social_class in SocialClass}


def split(total: int, weights: Mapping[SocialClass, float]) -> dict[SocialClass, int]:
    whole = sum(weights.values())
    if total <= 0 or whole <= 0:
        return dict.fromkeys(SocialClass, 0)
    parts = {social_class: int(total * weight / whole) for social_class, weight in weights.items()}
    rest = total - sum(parts.values())
    for social_class in sorted(weights, key=lambda item: (-(total * weights[item] / whole - parts[item]), SERVE_ORDER.index(item))):
        if rest <= 0:
            break
        if weights[social_class] > 0:
            parts[social_class] += 1
            rest -= 1
    return parts


def serve(total: int, wanted: Mapping[SocialClass, int], order: tuple[SocialClass, ...]) -> dict[SocialClass, int]:
    left = max(0, total)
    served: dict[SocialClass, int] = {}
    for social_class in order:
        taken = min(left, wanted.get(social_class, 0))
        served[social_class] = taken
        left -= taken
    return served


def serve_order(standing: Mapping[SocialClass, ClassStandingRow], shares: Mapping[SocialClass, float]) -> tuple[SocialClass, ...]:
    def per_head(social_class: SocialClass) -> float:
        row = standing.get(social_class)
        share = shares.get(social_class, 0.0)
        return row.wealth / share if row is not None and share > 0 else 0.0

    if not standing or not any(row.wealth > 0 for row in standing.values()):
        return SERVE_ORDER
    return tuple(sorted(SERVE_ORDER, key=lambda item: (-per_head(item), SERVE_ORDER.index(item))))


def held_got(wanted: int, got: int, held_pct: int | None) -> int:
    return round_half_up(wanted * held_pct / PERCENT) if held_pct is not None else got


def fed_by_class(
    rows: Mapping[NeedKey, tuple[int, int]], meal: Meal, order: tuple[SocialClass, ...], shares: Mapping[SocialClass, float]
) -> dict[SocialClass, int]:
    wanted: dict[SocialClass, int] = dict.fromkeys(SocialClass, 0)
    got: dict[SocialClass, int] = dict.fromkeys(SocialClass, 0)
    for (social_class, kind), (want, have) in rows.items():
        if kind not in FOOD_KINDS:
            continue
        value = COMMODITIES[kind].nourishment
        wanted[social_class] += want * value
        got[social_class] += min(want, have) * value
    extra = sum(max(0, meal.eaten.get(kind, 0) - meal.wanted.get(kind, 0)) * COMMODITIES[kind].nourishment for kind in meal.wanted)
    for social_class in order:
        gap = max(0, wanted[social_class] - got[social_class])
        filled = min(gap, extra)
        got[social_class] += filled
        extra -= filled
    fallback = meal.fed_pct if meal.wanted else PERCENT
    return {
        social_class: (clamp_int(round_half_up(got[social_class] * PERCENT / wanted[social_class]), 0, PERCENT) if wanted[social_class] > 0 else fallback)
        for social_class in SocialClass
        if shares.get(social_class, 0.0) > 0 or wanted[social_class] > 0
    }


def build_basket(
    shares: Mapping[SocialClass, float],
    meal: Meal,
    worn: Wear,
    *,
    staples: tuple[CommodityKind, ...],
    order: tuple[SocialClass, ...],
    held: Mapping[NeedKey, int],
    luxuries_left: int,
) -> Basket:
    rows: dict[NeedKey, tuple[int, int]] = {}
    for kind, wanted in [*meal.wanted.items(), *worn.wanted.items()]:
        got = min(wanted, meal.eaten.get(kind, 0)) if kind in FOOD_KINDS else worn.got.get(kind, 0)
        wanted_by = split(wanted, class_weights(shares, kind))
        served = serve(got, wanted_by, order)
        for social_class in SocialClass:
            want = wanted_by.get(social_class, 0)
            key = (social_class, kind)
            if want > 0 or key in held:
                rows[key] = (want, held_got(want, served.get(social_class, 0), held.get(key)))
    fed = fed_by_class(rows, meal, order, shares)
    luxury_wanted = {social_class: rows.get((social_class, CommodityKind.LUXURIES), (0, 0)) for social_class in SocialClass}
    spare = split(luxuries_left, class_weights(shares, CommodityKind.LUXURIES))
    classes: dict[SocialClass, ClassNeed] = {}
    for social_class in SocialClass:
        if shares.get(social_class, 0.0) <= 0:
            continue
        effects: dict[ShortfallEffect, int] = {}
        wanted_by_effect: dict[ShortfallEffect, int] = {}
        got_by_effect: dict[ShortfallEffect, int] = {}
        for (holder, kind), (want, have) in rows.items():
            if holder is not social_class or kind in FOOD_KINDS:
                continue
            effect = SHORTFALL_EFFECTS[kind]
            wanted_by_effect[effect] = wanted_by_effect.get(effect, 0) + want
            got_by_effect[effect] = got_by_effect.get(effect, 0) + min(want, have)
        for effect, want in wanted_by_effect.items():
            effects[effect] = short_pct(want, got_by_effect.get(effect, 0))
        effects[E.HUNGER] = PERCENT - fed.get(social_class, PERCENT)
        weights = {effect: basket_weight(effect, social_class) for effect in effects if effect is not E.HUNGER}
        whole = sum(weights.values())
        met = PERCENT - round_half_up(sum(effects[effect] * weight for effect, weight in weights.items()) / whole) if whole > 0 else PERCENT
        staple_want = sum(rows.get((social_class, kind), (0, 0))[0] for kind in staples)
        staple_got = sum(min(*rows.get((social_class, kind), (0, 0))) for kind in staples)
        want, have = luxury_wanted[social_class]
        luxury = clamp_int(round_half_up((have + spare.get(social_class, 0)) * PERCENT / want), 0, LUXURY_CAP) if want > 0 else PERCENT
        classes[social_class] = ClassNeed(
            fed_pct=fed.get(social_class, PERCENT),
            needs_met_pct=clamp_int(met, 0, PERCENT),
            luxury_pct=luxury,
            staple_short_pct=short_pct(staple_want, staple_got),
            effects=effects,
        )
    community: dict[ShortfallEffect, int] = {E.HUNGER: PERCENT - meal.fed_pct if meal.wanted else 0}
    totals: dict[ShortfallEffect, tuple[int, int]] = {}
    for (_, kind), (want, have) in rows.items():
        if kind in FOOD_KINDS:
            continue
        effect = SHORTFALL_EFFECTS[kind]
        before = totals.get(effect, (0, 0))
        totals[effect] = (before[0] + want, before[1] + min(want, have))
    for effect, (want, have) in totals.items():
        community[effect] = short_pct(want, have)
    return Basket(rows, classes, community)


async def standing_of(session: AsyncSession, community_id: int) -> dict[SocialClass, ClassStandingRow]:
    return {row.social_class: row for row in await kept_rows(session, ClassStandingRow, ClassStandingRow.community_entity_id, community_id)}


async def needs_of(session: AsyncSession, community_id: int) -> dict[NeedKey, CommunityNeedRow]:
    rows = await kept_rows(session, CommunityNeedRow, CommunityNeedRow.community_entity_id, community_id)
    return {(row.social_class, row.commodity): row for row in rows}


async def save_basket(ctx: TickContext, community: EntityRow, basket: Basket, found: dict[NeedKey, CommunityNeedRow]) -> None:
    for key, (wanted, got) in basket.rows.items():
        row = found.get(key)
        if row is None:
            row = CommunityNeedRow(community_entity_id=community.id, social_class=key[0], commodity=key[1], wanted=0, got=0, held_pct=None, epoch=ctx.epoch)
            ctx.session.add(row)
            found[key] = row
        row.wanted, row.got, row.epoch = max(0, wanted), max(0, got), ctx.epoch
    for key, row in found.items():
        if key not in basket.rows and row.held_pct is None:
            row.wanted, row.got, row.epoch = 0, 0, ctx.epoch
    for row in found.values():
        if instance_state(row).modified:
            for name in NEED_COLUMNS:
                flag_modified(row, name)
    standing = await standing_of(ctx.session, community.id)
    for social_class, need in basket.classes.items():
        kept = standing.get(social_class)
        if kept is None:
            kept = ClassStandingRow(community_entity_id=community.id, social_class=social_class, wealth=0, income=0, locked=[], epoch=ctx.epoch)
            ctx.session.add(kept)
        for name in ("fed_pct", "needs_met_pct", "luxury_pct"):
            if name not in kept.locked:
                setattr(kept, name, getattr(need, name))
        kept.epoch = ctx.epoch
    await ctx.session.flush()


def held_needs(standing: Mapping[SocialClass, ClassStandingRow], basket: Basket) -> Basket:
    classes = dict(basket.classes)
    for social_class, row in standing.items():
        need = classes.get(social_class)
        if need is None or not row.locked:
            continue
        classes[social_class] = ClassNeed(
            fed_pct=row.fed_pct if "fed_pct" in row.locked else need.fed_pct,
            needs_met_pct=row.needs_met_pct if "needs_met_pct" in row.locked else need.needs_met_pct,
            luxury_pct=row.luxury_pct if "luxury_pct" in row.locked else need.luxury_pct,
            staple_short_pct=need.staple_short_pct,
            effects=need.effects,
        )
    return Basket(basket.rows, classes, basket.effects)


def class_need_penalty(rules: Rules, social_class: SocialClass, need: ClassNeed) -> float:
    table = rules.consumption
    penalty = table.need_satisfaction * (PERCENT - need.needs_met_pct) / PERCENT
    penalty += table.hunger_satisfaction * (PERCENT - need.fed_pct) / PERCENT
    penalty += table.staple_satisfaction * need.staple_short_pct / PERCENT
    if social_class in PLENTY_CLASSES and need.luxury_pct >= table.luxury_plenty_pct:
        penalty -= table.luxury_plenty_satisfaction
    return penalty


def land_factor(rules: Rules, band: TemperatureBand | None) -> float:
    table = rules.consumption
    if band in COLD_BANDS:
        return table.cold_land_pct / PERCENT
    if band in WARM_BANDS:
        return table.warm_land_pct / PERCENT
    return 1.0


async def freeze(ctx: TickContext, community: EntityRow, short: int, band: TemperatureBand | None) -> int:
    population = stat(community, "population") or 0
    if band in COLD_BANDS and short >= ctx.rules.energy.shortfall_note_pct:
        await frostbite(ctx, community)
    dead = round_half_up(population * ctx.rules.consumption.cold_death_pct / PERCENT * short / PERCENT * land_factor(ctx.rules, band))
    dead = min(dead, max(0, population - 1))
    if dead <= 0:
        return 0
    with flowing(FlowCategory.DEATH):
        set_stats(community, population=population - dead)
    if dead > 0:
        await record(
            ctx,
            "consumption.cold_deaths",
            roles={IncidentRole.VICTIM: community.id},
            facts={"dead": dead, "short": short, "band": band},
            place=community.id,
        )
    return dead


async def sicken(ctx: TickContext, community: EntityRow, short: int) -> int:
    rows = await cohorts_of(ctx.session, community.id)
    moved = 0
    for key in sorted(rows, key=lambda item: tuple(part.value for part in item)):
        band, sex, social_class, condition = key
        if band is not AgeBand.ADULT or condition is not CohortCondition.NONE or rows[key].count <= 0:
            continue
        count = round_half_up(rows[key].count * ctx.rules.consumption.sickness_pct / PERCENT * short / PERCENT)
        if count <= 0:
            continue
        if move_amount(rows[key], row_for(ctx.session, rows, community.id, (band, sex, social_class, CohortCondition.SICK), ctx.epoch), "count", count):
            moved += count
    if moved > 0:
        await record(ctx, "consumption.sickness", roles={IncidentRole.VICTIM: community.id}, facts={"sick": moved, "short": short}, place=community.id)
    return moved


async def starve_herds(ctx: TickContext, community: EntityRow, short: int) -> int:
    herd = await holding(ctx.session, community.id, CommodityKind.LIVESTOCK)
    lost = round_half_up(herd * ctx.rules.consumption.herd_loss_pct / PERCENT * short / PERCENT)
    if lost <= 0:
        return 0
    taken = await goods_of(ctx.session, ctx.epoch).take_units(community.id, CommodityKind.LIVESTOCK, lost, GoodsFlow.CONSUMPTION)
    if taken > 0:
        await record(ctx, "consumption.herd_loss", roles={IncidentRole.VICTIM: community.id}, facts={"lost": taken, "short": short}, place=community.id)
    return taken


async def apply_shortfalls(ctx: TickContext, community: EntityRow, basket: Basket, band: TemperatureBand | None) -> dict[ShortfallEffect, int]:
    table = ctx.rules.consumption
    done: dict[ShortfallEffect, int] = {}
    for effect, short in sorted(basket.effects.items(), key=lambda item: item[0].value):
        if short <= 0:
            continue
        if effect is E.COLD:
            done[effect] = await freeze(ctx, community, short, band)
        elif effect is E.SICKNESS:
            done[effect] = await sicken(ctx, community, short)
        elif effect is E.HERDS:
            done[effect] = await starve_herds(ctx, community, short)
        elif effect is E.IMPIETY:
            loss = round_half_up(table.impiety_piety * short / PERCENT)
            shift_stat(community, "piety", -loss)
            done[effect] = loss
        elif effect is E.TOIL:
            loss = round_half_up(table.toil_prosperity * short / PERCENT)
            add_prosperity(ctx.rules, community, -loss)
            done[effect] = loss
        elif effect is E.INSECURITY:
            loss = round_half_up(table.insecurity_defense * short / PERCENT)
            shift_stat(community, "defense" if community.entity_type is EntityType.SETTLEMENT else "martiality", -loss)
            done[effect] = loss
        elif effect in APPLY_SHORTFALLS_SHORTFALL_EFFECTS:
            done[effect] = short
    return done


async def effect_shortfalls(session: AsyncSession, community_id: int) -> dict[ShortfallEffect, int]:
    totals: dict[ShortfallEffect, tuple[int, int]] = {}
    for row in (await needs_of(session, community_id)).values():
        effect = SHORTFALL_EFFECTS[row.commodity]
        got = held_got(row.wanted, row.got, row.held_pct)
        before = totals.get(effect, (0, 0))
        totals[effect] = (before[0] + row.wanted, before[1] + min(row.wanted, got))
    standing = await standing_of(session, community_id)
    found: dict[ShortfallEffect, int] = {effect: short_pct(want, have) for effect, (want, have) in totals.items() if effect is not E.HUNGER}
    society = await session.get(CommunitySocietyRow, community_id)
    weights = {social_class: society.share(social_class) if society is not None else 1.0 for social_class in standing}
    whole = sum(weights.values())
    fed = sum(row.fed_pct * weights[social_class] for social_class, row in standing.items())
    found[E.HUNGER] = clamp_int(PERCENT - round_half_up(fed / whole), 0, PERCENT) if whole > 0 else 0
    return found


async def fed_index(session: AsyncSession, community_id: int) -> int | None:
    society = await session.get(CommunitySocietyRow, community_id)
    stocked = society.stock(Commodity.FOOD) if society is not None else None
    if not await standing_of(session, community_id):
        return stocked
    eaten = PERCENT - (await effect_shortfalls(session, community_id)).get(E.HUNGER, 0)
    return max(stocked or 0, eaten)


async def poverty_of(session: AsyncSession, community_id: int, shares: Mapping[SocialClass, float]) -> int:
    standing = await standing_of(session, community_id)
    poor = [social_class for social_class in SERVE_ORDER[len(SERVE_ORDER) // 2 :] if social_class in standing and shares.get(social_class, 0.0) > 0]
    whole = sum(shares.get(social_class, 0.0) for social_class in poor)
    if whole <= 0:
        return 0
    return clamp_int(round_half_up(sum((PERCENT - standing[item].needs_met_pct) * shares[item] for item in poor) / whole), 0, PERCENT)
