from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.city_rules import MunicipalServiceRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.settlement import DistrictRow, SettlementInfrastructureRow, SettlementProfileRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.city_rules import MunicipalService
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.settlement import WaterSupply
from aerona.domain.enums.structure import StructureKind
from aerona.engine.city_rules.book import CityTally
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import held_coin, take_coin
from aerona.engine.primitives.mirrors import close_legacy, first_sight
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import shift_stat, stat_or
from aerona.engine.recording.record import record
from aerona.engine.urban.coverage import people_of_districts

LEGACY_FIXUP = "municipal_services.legacy"
WATER_FAMILY = "municipal_services.water"
POST_FAMILY = "municipal_services.post"
THOUSAND = 1000
LEGACY_OF = {
    StructureKind.WATCHTOWER: MunicipalService.NIGHT_WATCH,
    StructureKind.CEMETERY: MunicipalService.BURIAL_GROUND,
    StructureKind.TOMB: MunicipalService.BURIAL_GROUND,
}
STARTING_BUDGET = 100


async def found_service(
    ctx: TickContext, town: EntityRow, service: MunicipalService, tally: CityTally, *, provider: int | None = None, budget: int = STARTING_BUDGET
) -> MunicipalServiceRow:
    query = select(MunicipalServiceRow).where(MunicipalServiceRow.settlement_entity_id == town.id, MunicipalServiceRow.service == service)
    found = await ctx.session.scalar(query.order_by(MunicipalServiceRow.id).limit(1))
    row = found or MunicipalServiceRow(settlement_entity_id=town.id, service=service, coverage={}, founded_epoch=ctx.epoch, locked=[])
    row.provider_node_id, row.budget, row.failed_epoch = provider if provider is not None else town.id, budget, None
    if found is None:
        ctx.session.add(row)
    await ctx.session.flush()
    tally.services += 1
    await record(
        ctx,
        "city.service_founded",
        roles={IncidentRole.SUBJECT: town.id, IncidentRole.ACTOR: row.provider_node_id},
        facts={"service": service, "budget": budget},
    )
    return row


async def pay(ctx: TickContext, row: MunicipalServiceRow, town: EntityRow, wanted: int) -> int:
    provider = await living_entity(ctx.session, row.provider_node_id) if row.provider_node_id is not None else None
    payer = provider or town
    if payer.id == town.id:
        profile = await ctx.session.get(SettlementProfileRow, town.id)
        if profile is None or "treasury" in (profile.locked or []):
            return 0
        paid = min(wanted, held_coin(profile.treasury))
        profile.treasury -= paid
        return paid
    return wanted if await take_coin(ctx.session, ctx.rules, payer, wanted) else 0


async def run_service(ctx: TickContext, row: MunicipalServiceRow, town: EntityRow, tally: CityTally) -> None:
    table = ctx.rules.city_rules
    districts = list(await ctx.session.scalars(select(DistrictRow).where(DistrictRow.settlement_entity_id == town.id).order_by(DistrictRow.id)))
    people = people_of_districts(ctx.rules, stat_or(town, "population", 0), districts)
    needed = max(1, round_half_up(sum(people.values()) * table.service_cost_per_thousand / THOUSAND))
    paid = await pay(ctx, row, town, min(row.budget, needed))
    row.cost = paid
    share = clamp_int(paid * PERCENT // needed, 0, PERCENT)
    locked = row.locked or []
    if "budget" not in locked:
        row.budget = max(0, row.budget + round_half_up((needed - row.budget) * table.budget_follow_pct / PERCENT))
    if "quality" not in locked:
        row.quality = clamp_int(row.quality + round_half_up(table.quality_step * (2 * share - PERCENT) / PERCENT), 0, PERCENT)
    if "coverage" not in locked:
        row.coverage = {str(district.id): share for district in districts}
    if not share and row.failed_epoch is None:
        row.failed_epoch = ctx.epoch
        tally.failed += 1
        await record(ctx, "city.service_failed", roles={IncidentRole.SUBJECT: town.id}, facts={"service": row.service})
        return
    await act(ctx, row, town, share)


async def act(ctx: TickContext, row: MunicipalServiceRow, town: EntityRow, share: int) -> None:
    table = ctx.rules.city_rules
    profile = await ctx.session.get(SettlementProfileRow, town.id)
    if profile is None:
        return
    reach = share * row.quality // PERCENT
    if row.service is MunicipalService.REFUSE and "sanitation" not in (profile.locked or []):
        profile.sanitation = clamp_int(profile.sanitation + table.refuse_disease_cut_pct * reach // PERCENT, 0, PERCENT)
    elif row.service is MunicipalService.LIGHTING:
        if "crime" not in (profile.locked or []):
            profile.crime = clamp_int(profile.crime - table.lighting_crime_cut_pct * reach // PERCENT, 0, PERCENT)
        shift_stat(town, "prosperity", table.lighting_prosperity * reach // PERCENT)


async def tend_services(ctx: TickContext, tally: CityTally) -> None:
    query = select(MunicipalServiceRow).order_by(MunicipalServiceRow.id)
    for row in list(await ctx.session.scalars(query)):
        town = await ctx.session.get(EntityRow, row.settlement_entity_id)
        if town is None or town.status is not EntityStatus.CANON or held(town.id) or (row.failed_epoch is not None and not row.budget):
            continue
        await run_service(ctx, row, town, tally)


async def towns_found_services(ctx: TickContext, tally: CityTally) -> None:
    query = select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    for town in list(await ctx.session.scalars(query)):
        if held(town.id) or not ctx.rng(f"city.service.{town.id}.{ctx.epoch}").chance(ctx.rules.city_rules.service_start_chance_pct):
            continue
        have = set(await ctx.session.scalars(select(MunicipalServiceRow.service).where(MunicipalServiceRow.settlement_entity_id == town.id)))
        missing = [service for service in MunicipalService if service not in have]
        chosen = ctx.rng(f"city.service.which.{town.id}.{ctx.epoch}").pick_or_none(missing)
        if chosen is not None:
            await found_service(ctx, town, chosen, tally)


async def town_services(ctx: TickContext, tally: CityTally) -> None:
    before = tally.services
    wells = select(SettlementInfrastructureRow.settlement_entity_id).where(SettlementInfrastructureRow.water != WaterSupply.NONE)
    for town_id in list(await ctx.session.scalars(wells.order_by(SettlementInfrastructureRow.settlement_entity_id))):
        town = await living_entity(ctx.session, town_id)
        if town is not None and not held(town.id) and await first_sight(ctx.session, WATER_FAMILY, town.id):
            await founded_once(ctx, town, MunicipalService.WATER_DISTRIBUTION, tally)
    posts = select(StructureProfileRow).where(StructureProfileRow.kind.in_(sorted(LEGACY_OF))).order_by(StructureProfileRow.structure_entity_id)
    for structure in list(await ctx.session.scalars(posts)):
        town = await living_entity(ctx.session, structure.host_entity_id) if structure.host_entity_id is not None else None
        if town is None or town.entity_type is not EntityType.SETTLEMENT or held(town.id):
            continue
        if await first_sight(ctx.session, POST_FAMILY, structure.structure_entity_id):
            await founded_once(ctx, town, LEGACY_OF[structure.kind], tally)
    await close_legacy(ctx.session, LEGACY_FIXUP, {"services": tally.services - before})
    await ctx.session.flush()


async def founded_once(ctx: TickContext, town: EntityRow, service: MunicipalService, tally: CityTally) -> None:
    query = select(MunicipalServiceRow.id).where(MunicipalServiceRow.settlement_entity_id == town.id, MunicipalServiceRow.service == service)
    if await ctx.session.scalar(query.limit(1)) is None:
        await found_service(ctx, town, service, tally)
