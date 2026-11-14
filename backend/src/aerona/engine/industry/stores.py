from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.catalog.methods import FUEL_FAMILY, FUEL_HEAT, METHODS, PERISHABLE, default_method
from aerona.constants.units import PERCENT
from aerona.db.tables.ecology import HerdRow, SpeciesProfileRow, SpeciesRangeRow, SpeciesUseRow
from aerona.db.tables.economy import CommunityStockRow, ProductionRunRow
from aerona.db.tables.entities import EntityRow, EntityTraitRow
from aerona.db.tables.industry import CommunityIndustryRow
from aerona.db.write_guard import held
from aerona.domain.enums.divine import DomainHook
from aerona.domain.enums.ecology import Diet, SizeClass, SpeciesClass, SpeciesUse
from aerona.domain.enums.economy import CommodityKind, GoodsFlow, WorkshopKind
from aerona.domain.enums.industry import EnergyKind, ProcessKind, QualityTier
from aerona.domain.enums.society import CreatureTrait, SocialClass
from aerona.engine.context import TickContext
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.stocks import goods_of, lots_of
from aerona.engine.environment.years import world_years
from aerona.engine.industry.energy import scale_by_energy
from aerona.engine.industry.methods import allowed, feed, local_price, method_for
from aerona.engine.industry.quality import at_least
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import headcount

TENTH = 10
THOUSAND = 1000
HUNTER_DIETS = (Diet.CARNIVORE, Diet.OMNIVORE)
HUNTER_SIZES = (SizeClass.TINY, SizeClass.SMALL)
DRINK_STEPS = ("brew", "press_fruit", "brew_base")
STORED_GRAINS = frozenset({CommodityKind.GRAIN, CommodityKind.TUBERS})
LIGHT_STEP = "lighting"


@dataclass
class StoreTally:
    preserved: int = 0
    spoiled: int = 0
    worn: int = 0
    burned: int = 0
    coarse: int = 0


async def vermin_in(ctx: TickContext, region_id: int | None) -> bool:
    if region_id is None:
        return False
    traited = select(EntityTraitRow.entity_id).where(EntityTraitRow.trait == CreatureTrait.CROP_PEST)
    vermin = select(SpeciesProfileRow.species_entity_id).where(SpeciesProfileRow.species_class == SpeciesClass.VERMIN)
    pests = traited.union(vermin)
    found = await ctx.session.scalar(
        select(SpeciesRangeRow.species_entity_id)
        .where(SpeciesRangeRow.region_entity_id == region_id, SpeciesRangeRow.abundance > 0, SpeciesRangeRow.species_entity_id.in_(pests))
        .limit(1)
    )
    return found is not None


async def pest_hunters(ctx: TickContext, community_id: int) -> bool:
    sized = select(SpeciesProfileRow.species_entity_id).where(SpeciesProfileRow.diet.in_(HUNTER_DIETS), SpeciesProfileRow.size_class.in_(HUNTER_SIZES))
    hunters = sized.union(select(SpeciesUseRow.species_entity_id).where(SpeciesUseRow.use == SpeciesUse.PEST_CONTROL))
    found = await ctx.session.scalar(
        select(HerdRow.species_entity_id).where(HerdRow.community_entity_id == community_id, HerdRow.head > 0, HerdRow.species_entity_id.in_(hunters)).limit(1)
    )
    return found is not None


async def perishables(ctx: TickContext, community_id: int) -> list[CommunityStockRow]:
    lots: list[CommunityStockRow] = []
    for commodity in PERISHABLE:
        lots.extend(row for row in await lots_of(ctx.session, community_id, commodity) if row.quantity > 0)
    for row in lots:
        row.preserved = min(row.preserved, row.quantity)
    return lots


async def preserve(ctx: TickContext, book: EconomyBook, community: EntityRow, row: CommunityIndustryRow, tally: StoreTally) -> int:
    spec = method_for(book, community.id, ProcessKind.PRESERVING)
    if allowed(book, community, spec) is not None:
        spec = default_method(ProcessKind.PRESERVING)
    lots = [lot for lot in await perishables(ctx, community.id) if not lot.held]
    fresh = sum(lot.quantity - lot.preserved for lot in lots)
    want = fresh * ctx.rules.stores.preserve_pct / PERCENT * spec.output_pct / PERCENT
    if want <= 0:
        return 0
    keep = round_half_up(want * scale_by_energy(book, community.id, spec.energy, spec.energy_need * -(-round_half_up(want) // TENTH)))
    keep = round_half_up(keep * await feed(ctx, community.id, spec, keep))
    if keep <= 0:
        return 0
    kept = 0
    for lot in lots:
        part = min(lot.quantity - lot.preserved, round_half_up(keep * (lot.quantity - lot.preserved) / fresh))
        lot.preserved += part
        kept += part
    if "preserved" not in row.locked:
        row.preserved += kept
    ctx.session.add(
        ProductionRunRow(
            epoch=ctx.epoch,
            community_entity_id=community.id,
            step="preserve",
            output=lots[0].commodity,
            quantity=kept,
            quality=lots[0].quality,
            inputs={},
            workers=0,
            method=spec.kind,
        )
    )
    tally.preserved += kept
    return kept


async def spoil(ctx: TickContext, book: EconomyBook, community: EntityRow, row: CommunityIndustryRow, tally: StoreTally) -> int:
    table = ctx.rules.stores
    region = book.ground.region_of(community.id)
    vermin = await vermin_in(ctx, region.entity_id if region is not None else None)
    hunters = await pest_hunters(ctx, community.id)
    granary = book.workshop(community.id, WorkshopKind.GRANARY)
    shelter = max(0.0, 1 - (granary.level if granary is not None else 0) * table.granary_pct / PERCENT)
    shelter *= await ctx.hook_easing(community.id, DomainHook.PRESERVATION)
    ledger = goods_of(ctx.session, ctx.epoch)
    years = max(1, len(world_years(ctx.environment, community.world_id or 0, "stores")))
    lost_total = 0
    for lot in await perishables(ctx, community.id):
        if lot.held:
            continue
        rate = 1 - (1 - getattr(table, PERISHABLE[lot.commodity]) / PERCENT * shelter) ** years
        if lot.commodity in STORED_GRAINS:
            rate = min(1.0, rate * ((1 + table.vermin_pct / PERCENT) if vermin else 1.0) * ((1 - table.hunters_pct / PERCENT) if hunters else 1.0))
        lost = min(lot.quantity - lot.preserved, round_half_up((lot.quantity - lot.preserved) * rate))
        if lost <= 0:
            continue
        lost_total -= await ledger.shift_lot(lot, -lost, GoodsFlow.DECAY)
    if "spoiled" not in row.locked:
        row.spoiled += lost_total
    tally.spoiled += lost_total
    return lost_total


async def wear_tools(ctx: TickContext, book: EconomyBook, community: EntityRow, row: CommunityIndustryRow, tally: StoreTally) -> int:
    table = ctx.rules.stores
    per_batch = max(1, ctx.rules.refining.workers_per_batch)
    need = 0.0
    runs = await ctx.session.scalars(
        select(ProductionRunRow).where(
            ProductionRunRow.epoch == ctx.epoch, ProductionRunRow.community_entity_id == community.id, ProductionRunRow.method.is_not(None)
        )
    )
    for run in runs:
        wear = METHODS[run.method].tool_wear if run.method is not None else 0
        if run.resource_entity_id is not None or run.step == "harvest":
            rate = table.tools_per_1000_farmers if run.step == "harvest" else table.tools_per_1000_workers
            need += run.workers * rate * wear / THOUSAND
        else:
            need += run.workers / per_batch * table.tools_per_10_batches * wear / TENTH
    units = round_half_up(need)
    if units <= 0:
        return 0
    taken = sum(lot.quantity for lot in await goods_of(ctx.session, ctx.epoch).take(community.id, CommodityKind.TOOLS, units, GoodsFlow.TOOL, best_first=False))
    if "tools_worn" not in row.locked:
        row.tools_worn += taken
    tally.worn += taken
    return taken


async def burn_fuel(ctx: TickContext, book: EconomyBook, community: EntityRow, row: CommunityIndustryRow, tally: StoreTally) -> int:
    table = ctx.rules.energy
    heat = row.spent.get(EnergyKind.HEAT.value, 0)
    if heat <= 0:
        return 0
    per_heat = {kind: int(getattr(table, key)) for kind, key in FUEL_HEAT.items()}
    order = sorted(
        (kind for kind in FUEL_FAMILY if per_heat[kind] > 0),
        key=lambda kind: (local_price(book, community.id, kind) * ctx.rules.substitution.price_pct / PERCENT / per_heat[kind], kind.value),
    )
    ledger = goods_of(ctx.session, ctx.epoch)
    burned = 0
    for kind in order:
        if heat <= 0:
            break
        units = sum(lot.quantity for lot in await ledger.take(community.id, kind, -(-heat // per_heat[kind]), GoodsFlow.INPUT, best_first=False))
        heat -= units * per_heat[kind]
        burned += units
    tally.burned += burned
    return burned


async def noble_taste(ctx: TickContext, book: EconomyBook, community: EntityRow, tally: StoreTally) -> bool:
    society = book.societies.get(community.id)
    if society is None or society.share(SocialClass.NOBLE) <= 0 or held(community.id):
        return False
    lots = [lot for lot in await lots_of(ctx.session, community.id, CommodityKind.LUXURIES) if lot.quantity > 0]
    if any(at_least(ctx.rules, lot.quality, QualityTier.FINE) for lot in lots):
        return False
    society.satisfaction_noble = clamp_int(society.satisfaction_noble - ctx.rules.quality.noble_coarse_satisfaction, 0, PERCENT)
    tally.coarse += 1
    return True


async def pour_drink(ctx: TickContext, community: EntityRow, row: CommunityIndustryRow) -> int:
    brewed = await ctx.session.scalar(
        select(func.coalesce(func.sum(ProductionRunRow.quantity), 0)).where(
            ProductionRunRow.epoch == ctx.epoch, ProductionRunRow.community_entity_id == community.id, ProductionRunRow.step.in_(DRINK_STEPS)
        )
    )
    want = max(1, headcount(community) * ctx.rules.drink.per_1000 // THOUSAND)
    if "drink" not in row.locked:
        row.drink = clamp_int(int(brewed or 0) * PERCENT / want, 0, PERCENT)
    return row.drink


async def kindle(ctx: TickContext, book: EconomyBook, community: EntityRow, row: CommunityIndustryRow) -> int:
    spec = method_for(book, community.id, ProcessKind.LIGHTING)
    if allowed(book, community, spec) is not None:
        spec = default_method(ProcessKind.LIGHTING)
    want = max(1, headcount(community) * ctx.rules.energy.light_per_1000 // THOUSAND)
    powered = scale_by_energy(book, community.id, spec.energy, spec.energy_need * -(-want // TENTH))
    fed = await feed(ctx, community.id, spec, want)
    light = clamp_int(spec.output_pct * min(powered, fed), 0, PERCENT)
    if "light" not in row.locked:
        row.light = light
    ctx.session.add(
        ProductionRunRow(
            epoch=ctx.epoch,
            community_entity_id=community.id,
            step=LIGHT_STEP,
            output=CommodityKind.LUXURIES,
            quantity=round_half_up(want * min(powered, fed)),
            quality=PERCENT // 2,
            inputs={},
            workers=0,
            method=spec.kind,
        )
    )
    return row.light
