from aerona.constants.units import PERCENT
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.society import SocialClass
from aerona.engine.context import TickContext
from aerona.engine.demography.cohorts import cohorts_of
from aerona.engine.demography.control import move_cohort
from aerona.engine.primitives.numbers import round_half_up
from aerona.rules.registry import Rules


def lean(rules: Rules, culture: PeopleCultureRow | None) -> float:
    if culture is None:
        return 0.0
    return (culture.urbanisation - rules.customs.urban_pivot) / PERCENT


def scaled(rules: Rules, culture: PeopleCultureRow | None, pct: int) -> float:
    return max(0.0, 1 + lean(rules, culture) * pct / PERCENT)


def founding_factor(rules: Rules, culture: PeopleCultureRow | None) -> float:
    return scaled(rules, culture, rules.customs.urban_found_pct)


def town_pull_factor(rules: Rules, culture: PeopleCultureRow | None) -> float:
    return scaled(rules, culture, rules.customs.urban_town_pull_pct)


def growth_factor(rules: Rules, culture: PeopleCultureRow | None) -> float:
    return scaled(rules, culture, rules.customs.urban_growth_pct)


def class_shift(rules: Rules, culture: PeopleCultureRow | None, farmers: int, artisans: int) -> int:
    drift = lean(rules, culture)
    if drift > 0:
        return round_half_up(farmers * drift * rules.customs.urban_class_pct / PERCENT)
    if drift < 0:
        return -round_half_up(artisans * -drift * rules.customs.rural_class_pct / PERCENT)
    return 0


async def urban_drift(ctx: TickContext, community: EntityRow, culture: PeopleCultureRow | None) -> int:
    if held(community.id):
        return 0
    rows = await cohorts_of(ctx.session, community.id)
    farmers = sum(row.count for key, row in rows.items() if key[2] is SocialClass.FARMER)
    artisans = sum(row.count for key, row in rows.items() if key[2] is SocialClass.ARTISAN)
    shift = class_shift(ctx.rules, culture, farmers, artisans)
    if shift > 0:
        merchants = shift // 3
        moved = await move_cohort(ctx, community.id, count=shift - merchants, source=SocialClass.FARMER, target=SocialClass.ARTISAN, band=None, condition=None)
        if merchants:
            moved += await move_cohort(ctx, community.id, count=merchants, source=SocialClass.FARMER, target=SocialClass.MERCHANT, band=None, condition=None)
        return moved
    if shift < 0:
        return -await move_cohort(ctx, community.id, count=-shift, source=SocialClass.ARTISAN, target=SocialClass.FARMER, band=None, condition=None)
    return 0
