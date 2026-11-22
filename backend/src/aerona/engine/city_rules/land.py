from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.city_rules import LandUseRuleRow, MunicipalServiceRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.settlement import DistrictRow, SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.city_rules import LandUseRule, MunicipalService, RuleMaker
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.settlement import BuildMaterial
from aerona.domain.enums.urban import Morphology
from aerona.engine.city_rules.book import CityTally
from aerona.engine.city_rules.effects import rules_of
from aerona.engine.context import TickContext
from aerona.engine.primitives.mirrors import close_legacy, first_sight
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.recording.record import record

LEGACY_FIXUP = "land_use_rules.legacy_planned"
PLANNED_FAMILY = "land_use_rules.planned"
EVADED = 50
PLAN_STRENGTH = 50
CROWDED_LEVELS = 6
RM = RuleMaker
MAKER_ENFORCEMENT = total(RuleMaker, {RM.COUNCIL: 50, RM.RULER: 70, RM.GUILD: 40, RM.FAITH: 60})


async def set_rule(
    ctx: TickContext,
    town: EntityRow,
    rule: LandUseRule,
    values: dict[str, int | str | list[str]],
    tally: CityTally,
    *,
    maker: RuleMaker = RuleMaker.COUNCIL,
    by: int | None = None,
    district: int | None = None,
) -> LandUseRuleRow:
    found = next((row for row in await rules_of(ctx.session, town.id) if row.rule is rule and row.district_id == district), None)
    row = found or LandUseRuleRow(settlement_entity_id=town.id, district_id=district, rule=rule, locked=[])
    if "values" not in (row.locked or []):
        row.values = dict(values)
    row.maker, row.maker_node_id, row.set_epoch = maker, by, ctx.epoch
    if found is None:
        row.enforcement = MAKER_ENFORCEMENT[maker]
        ctx.session.add(row)
    await ctx.session.flush()
    tally.rules_set += 1
    await record(ctx, "city.rule_set", roles={IncidentRole.SUBJECT: town.id, IncidentRole.ACTOR: by}, facts={"rule": rule, "maker": maker})
    return row


async def land_value(ctx: TickContext, settlement_id: int) -> int:
    values = list(await ctx.session.scalars(select(DistrictRow.land_value).where(DistrictRow.settlement_entity_id == settlement_id)))
    return sum(values) // len(values) if values else 0


async def weigh_evasion(ctx: TickContext, row: LandUseRuleRow, value: int, tally: CityTally) -> None:
    if "evasion" in (row.locked or []):
        return
    before = row.evasion
    row.evasion = clamp_int(round_half_up((PERCENT - row.enforcement) * value * ctx.rules.city_rules.evasion_per_land_value_pct / (PERCENT * 10)), 0, PERCENT)
    if row.evasion >= EVADED > before:
        tally.evaded += 1
        await record(ctx, "city.rule_evaded", roles={IncidentRole.SUBJECT: row.settlement_entity_id}, facts={"rule": row.rule, "evasion": row.evasion})


async def rebuild(ctx: TickContext, town: EntityRow, profile: SettlementProfileRow, tally: CityTally) -> None:
    table = ctx.rules.city_rules
    if not await rules_of(ctx.session, town.id) or "morphology" in (profile.locked or []):
        return
    query = select(DistrictRow).where(DistrictRow.settlement_entity_id == town.id, DistrictRow.condition < table.rebuild_condition)
    wrecked = list(await ctx.session.scalars(query.order_by(DistrictRow.id)))
    if not wrecked or "treasury" in (profile.locked or []) or profile.treasury < table.rebuild_cost:
        return
    profile.treasury -= table.rebuild_cost
    for district in wrecked:
        if "condition" not in (district.locked or []):
            district.condition = PERCENT
        if "material" not in (district.locked or []):
            district.material = BuildMaterial.STONE
    profile.morphology = Morphology.PLANNED
    tally.rebuilt += 1
    await record(ctx, "city.planned_rebuild", roles={IncidentRole.SUBJECT: town.id}, facts={"districts": len(wrecked)})


async def order_kept(ctx: TickContext, town_id: int, profile: SettlementProfileRow) -> int:
    watch = select(MunicipalServiceRow).where(MunicipalServiceRow.settlement_entity_id == town_id, MunicipalServiceRow.service == MunicipalService.NIGHT_WATCH)
    found = await ctx.session.scalar(watch.order_by(MunicipalServiceRow.id).limit(1))
    covered = list((found.coverage or {}).values()) if found is not None and found.failed_epoch is None else []
    guarded = sum(int(share) for share in covered) // len(covered) if covered else 0
    return clamp_int(PERCENT - profile.crime + guarded // 2, 0, PERCENT)


async def tend_rules(ctx: TickContext, tally: CityTally) -> None:
    towns = sorted(set(await ctx.session.scalars(select(LandUseRuleRow.settlement_entity_id))))
    for town_id in towns:
        town = await ctx.session.get(EntityRow, town_id)
        profile = await ctx.session.get(SettlementProfileRow, town_id)
        if town is None or profile is None or held(town_id) or town.status is not EntityStatus.CANON:
            continue
        value = await land_value(ctx, town_id)
        order = await order_kept(ctx, town_id, profile)
        for row in await rules_of(ctx.session, town_id):
            if "enforcement" not in (row.locked or []):
                row.enforcement = clamp_int(
                    row.enforcement + round_half_up((order - row.enforcement) * ctx.rules.city_rules.enforcement_follow_pct / PERCENT), 0, PERCENT
                )
            await weigh_evasion(ctx, row, value, tally)
        await rebuild(ctx, town, profile, tally)


async def crowded_towns(ctx: TickContext, tally: CityTally) -> None:
    query = select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    for town in list(await ctx.session.scalars(query)):
        if held(town.id) or await rules_of(ctx.session, town.id):
            continue
        levels = sum(await ctx.session.scalars(select(DistrictRow.level).where(DistrictRow.settlement_entity_id == town.id)))
        if levels >= CROWDED_LEVELS and ctx.rng(f"city.rule.{town.id}.{ctx.epoch}").chance(ctx.rules.city_rules.rule_start_chance_pct):
            await set_rule(ctx, town, LandUseRule.FIRE_SPACING, {}, tally)


async def plan_rules(ctx: TickContext, tally: CityTally) -> None:
    made = 0
    planned = select(SettlementProfileRow.settlement_entity_id).where(SettlementProfileRow.morphology == Morphology.PLANNED)
    for town_id in list(await ctx.session.scalars(planned.order_by(SettlementProfileRow.settlement_entity_id))):
        town = await ctx.session.get(EntityRow, town_id)
        if town is None or town.status is not EntityStatus.CANON or held(town_id) or not await first_sight(ctx.session, PLANNED_FAMILY, town_id):
            continue
        if await rules_of(ctx.session, town_id):
            continue
        for rule in (LandUseRule.FIRE_SPACING, LandUseRule.FRONTAGE_RULE):
            row = await set_rule(ctx, town, rule, {}, tally)
            row.strength = PLAN_STRENGTH
            made += 1
    await close_legacy(ctx.session, LEGACY_FIXUP, {"rules": made})
    await ctx.session.flush()
