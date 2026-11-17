from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.constants.units import PERCENT
from aerona.db.tables.agrarian import BrandRow, KeystoneResourceRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.culture import ItemProfileRow
from aerona.db.tables.ecology import SpeciesProductRow, SpeciesRangeRow
from aerona.db.tables.economy import MarketPriceRow, ProductionRunRow, WorkshopRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.settlement import SettlementInfrastructureRow, SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.agrarian import KeystoneUse
from aerona.domain.enums.economy import CommodityKind, WorkshopKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.settlement import TreasuryEntry
from aerona.domain.enums.war import WarCause
from aerona.engine.agrarian.rings import put
from aerona.engine.collective.book import shift
from aerona.engine.context import TickContext
from aerona.engine.cycles.standing import regard
from aerona.engine.economy.purse import give_coin
from aerona.engine.faith.book import Church, FaithBook
from aerona.engine.polity.book import Realm, RealmBook
from aerona.engine.polity.governance import spend
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.records import sentence_case
from aerona.engine.primitives.stats import shift_stat
from aerona.engine.recording.record import record
from aerona.engine.services.community_relations import relation
from aerona.engine.services.war import declare_war

HALF = 50


@dataclass
class StaplesTally:
    keystones: int = 0
    designated: int = 0
    scarce: int = 0
    wars: int = 0
    brands: int = 0
    earned: int = 0
    counterfeited: int = 0


@dataclass(frozen=True)
class Candidate:
    species_id: int
    product: str
    commodity: CommodityKind | None


def holding_church(atlas: RegionAtlas, faith: FaithBook, region_id: int) -> Church | None:
    present = [(sum(1 for member in church.members if atlas.top_region(member.id) == region_id), church) for church in faith.churches.values()]
    kept = [(count, church) for count, church in present if count > 0 and not held(church.cult.id)]
    return max(kept, key=lambda item: (item[0], -item[1].cult.id))[1] if kept else None


def controller_of(book: RealmBook, region_id: int | None) -> int | None:
    if region_id is None:
        return None
    holders = [(realm.territory[region_id].control, -realm.entity.id, realm.entity.id) for realm in book.realms.values() if region_id in realm.territory]
    return max(holders)[2] if holders else None


async def candidates(ctx: TickContext) -> list[Candidate]:
    table = ctx.rules.keystone_resource
    spread = await ctx.session.execute(
        select(SpeciesRangeRow.species_entity_id, func.count(), func.max(SpeciesRangeRow.abundance))
        .where(SpeciesRangeRow.abundance > 0)
        .group_by(SpeciesRangeRow.species_entity_id)
    )
    rare = {species: abundance for species, lands, abundance in spread.all() if lands <= table.unique_ranges and abundance >= table.designate_abundance}
    if not rare:
        return []
    rows = await ctx.session.execute(
        select(SpeciesProductRow.species_entity_id, SpeciesProductRow.product, SpeciesProductRow.commodity).where(
            SpeciesProductRow.species_entity_id.in_(list(rare)), SpeciesProductRow.commodity.is_not(None)
        )
    )
    found = [Candidate(species, product, commodity) for species, product, commodity in rows.all()]
    return sorted(found, key=lambda item: (-rare[item.species_id], item.species_id, item.product))


async def designate(ctx: TickContext, atlas: RegionAtlas, faith: FaithBook, book: RealmBook, tally: StaplesTally) -> None:
    table = ctx.rules.keystone_resource
    claimed = set(await ctx.session.scalars(select(KeystoneResourceRow.world_id)))
    open_worlds = [world for world in await ctx.session.scalars(select(WorldRow).order_by(WorldRow.id)) if world.id not in claimed]
    if not open_worlds:
        return
    options = await candidates(ctx)
    for world in open_worlds:
        world_id = world.id
        young = ctx.epoch - (world.created_epoch or 0) <= table.genesis_epochs
        if not options or not ctx.rng(f"keystone.designate.{world_id}.{ctx.epoch}").chance(PERCENT if young else table.designate_pct):
            continue
        for option in options:
            species = await ctx.session.get(EntityRow, option.species_id)
            if species is None or species.world_id != world_id or held(species.id):
                continue
            source = await ctx.session.scalar(
                select(SpeciesRangeRow.region_entity_id)
                .where(SpeciesRangeRow.species_entity_id == species.id)
                .order_by(SpeciesRangeRow.abundance.desc(), SpeciesRangeRow.region_entity_id)
                .limit(1)
            )
            church = holding_church(atlas, faith, source) if source is not None else None
            if source is None or church is None:
                continue
            name = sentence_case(option.product.replace("_", " "))
            ctx.session.add(
                KeystoneResourceRow(
                    world_id=world_id,
                    name=name,
                    producer_entity_id=species.id,
                    source_region_entity_id=source,
                    commodity=option.commodity,
                    use=KeystoneUse.RITE,
                    cult_entity_id=church.cult.id,
                    controller_entity_id=controller_of(book, source),
                    designated_epoch=ctx.epoch,
                    locked=[],
                )
            )
            tally.designated += 1
            await record(
                ctx,
                "keystone.designated",
                roles={IncidentRole.SUBJECT: species.id, IncidentRole.ORIGIN: source},
                facts={"name": name, "cult": church.cult.id, "use": KeystoneUse.RITE, "commodity": option.commodity},
                place=source,
                world_id=world_id,
            )
            break


async def harvest(ctx: TickContext, row: KeystoneResourceRow) -> None:
    table = ctx.rules.keystone_resource
    found = (
        await ctx.session.get(SpeciesRangeRow, (row.producer_entity_id, row.source_region_entity_id))
        if row.producer_entity_id is not None and row.source_region_entity_id is not None
        else None
    )
    if found is None or row.producer_entity_id is None:
        drawn = row.harvest * table.harm_pct / PERCENT
        put(row, "supply", clamp_int(row.supply + table.renewal - drawn * row.supply / PERCENT, 0, PERCENT))
        return
    if not held(row.producer_entity_id) and "abundance" not in found.locked:
        found.abundance = max(0, round_half_up(found.abundance - row.harvest * table.harm_pct / PERCENT / PERCENT * found.abundance))
    put(row, "supply", clamp_int(found.abundance * PERCENT / table.full_abundance, 0, PERCENT))


async def dependents_suffer(ctx: TickContext, row: KeystoneResourceRow, book: RealmBook, faith: FaithBook) -> None:
    loss = ctx.rules.keystone_resource.dependent_loss
    realms = [realm for realm in book.realms.values() if realm.entity.world_id == row.world_id and not held(realm.entity.id)]
    if row.use is KeystoneUse.NAVIGATION:
        ports = await ctx.session.execute(
            select(EntityRow)
            .join(SettlementInfrastructureRow, SettlementInfrastructureRow.settlement_entity_id == EntityRow.id)
            .where(EntityRow.world_id == row.world_id, EntityRow.status == EntityStatus.CANON, SettlementInfrastructureRow.harbour_capacity > 0)
        )
        for port in ports.scalars():
            if not held(port.id):
                shift_stat(port, "prosperity", -loss)
    elif row.use is KeystoneUse.LONGEVITY:
        for realm in realms:
            ruler = await ctx.session.get(EntityRow, realm.ruler_id) if realm.ruler_id is not None else None
            if ruler is not None and not held(ruler.id):
                shift_stat(ruler, "hp", -loss)
    elif row.use is KeystoneUse.PRESCIENCE:
        for realm in realms:
            shift(realm.profile, "legitimacy", -loss)
    else:
        church = next((item for item in faith.churches.values() if item.cult.id == row.cult_entity_id), None)
        for member in church.members if church is not None else []:
            if member.entity_type is EntityType.SETTLEMENT and not held(member.id):
                shift_stat(member, "piety", -loss)


async def contend(ctx: TickContext, row: KeystoneResourceRow, book: RealmBook, controller: Realm | None, *, scarce: bool, tally: StaplesTally) -> None:
    table = ctx.rules.keystone_resource
    if controller is None:
        return
    rivals = [realm for realm in book.realms.values() if realm.entity.world_id == row.world_id and realm.entity.id != controller.entity.id]
    regards: list[tuple[int, int]] = []
    for realm in rivals:
        if held(realm.entity.id):
            continue
        await regard(ctx, (realm.entity.id, controller.entity.id), -table.envy, MemoryKind.HARMED_ME, f"holds the source of {row.name}")
        regards.append((await relation(ctx.session, ctx.rules, realm.entity.id, controller.entity.id), realm.entity.id))
    envious = [item for item in sorted(regards) if item[0] <= table.envy_at]
    if (
        scarce
        and envious
        and ctx.rng(f"keystone.war.{row.id}.{ctx.epoch}").chance(table.war_pct)
        and await declare_war(ctx, envious[0][1], controller.entity.id, f"to seize the source of {row.name}", cause=WarCause.RESOURCE)
    ):
        tally.wars += 1


async def keep_keystones(ctx: TickContext, atlas: RegionAtlas, faith: FaithBook, book: RealmBook, tally: StaplesTally) -> None:
    table = ctx.rules.keystone_resource
    for row in await ctx.session.scalars(select(KeystoneResourceRow).order_by(KeystoneResourceRow.id)):
        if row.source_region_entity_id is not None and held(row.source_region_entity_id):
            continue
        tally.keystones += 1
        put(row, "controller_entity_id", controller_of(book, row.source_region_entity_id))
        await harvest(ctx, row)
        put(row, "price", PERCENT + max(0, HALF - row.supply) * table.price_swing // PERCENT)
        controller = book.realms.get(row.controller_entity_id) if row.controller_entity_id is not None else None
        if controller is not None and not held(controller.entity.id):
            income = round_half_up(row.harvest * table.coin_per_point * row.supply / PERCENT * row.price / PERCENT)
            if income > 0:
                spend(ctx, controller, income, TreasuryEntry.MONOPOLY, f"the trade in {row.name}")
        scarce = row.supply < table.scarce_at
        if scarce:
            tally.scarce += 1
            await dependents_suffer(ctx, row, book, faith)
            if row.cult_entity_id is not None and controller is not None and not held(row.cult_entity_id):
                await regard(ctx, (row.cult_entity_id, controller.entity.id), -table.cult_regard, MemoryKind.HARMED_ME, f"let {row.name} run short")
        await contend(ctx, row, book, controller, scarce=scarce, tally=tally)


@dataclass(frozen=True)
class Output:
    quality: int
    quantity: int
    commodity: CommodityKind


async def outputs(ctx: TickContext) -> dict[tuple[int, WorkshopKind], Output]:
    rows = await ctx.session.execute(
        select(
            ProductionRunRow.community_entity_id, ProductionRunRow.workshop, ProductionRunRow.output, ProductionRunRow.quality, ProductionRunRow.quantity
        ).where(ProductionRunRow.epoch == ctx.epoch, ProductionRunRow.workshop.is_not(None))
    )
    weighted: dict[tuple[int, WorkshopKind], list[tuple[int, int, CommodityKind]]] = defaultdict(list)
    for community, workshop, output, quality, quantity in rows.all():
        if workshop is not None:
            weighted[(community, workshop)].append((quality, quantity, output))
    found: dict[tuple[int, WorkshopKind], Output] = {}
    for key, runs in weighted.items():
        total = sum(quantity for _, quantity, _ in runs)
        mean = sum(quality * max(1, quantity) for quality, quantity, _ in runs) / max(1, sum(max(1, quantity) for _, quantity, _ in runs))
        found[key] = Output(round_half_up(mean), total, max(runs, key=lambda item: (item[1], item[2].value))[2])
    return found


async def renowned_by(ctx: TickContext) -> dict[int, int]:
    rows = await ctx.session.execute(
        select(EntityRow.location_id, func.count())
        .join(ItemProfileRow, ItemProfileRow.maker_entity_id == EntityRow.id)
        .where(ItemProfileRow.renown >= HALF, EntityRow.location_id.is_not(None))
        .group_by(EntityRow.location_id)
    )
    return {location: int(count) for location, count in rows.all() if location is not None}


async def price_of(ctx: TickContext, community_id: int, commodity: CommodityKind) -> int:
    price = await ctx.session.scalar(
        select(MarketPriceRow.price)
        .where(MarketPriceRow.market_entity_id == community_id, MarketPriceRow.commodity == commodity)
        .order_by(MarketPriceRow.epoch.desc())
        .limit(1)
    )
    return max(1, price or 1)


async def lift_market(ctx: TickContext, community_id: int, commodity: CommodityKind, lift: float) -> None:
    row = await ctx.session.get(MarketPriceRow, (community_id, commodity, ctx.epoch))
    if row is not None and lift > 0:
        row.price = round_half_up(row.price * (1 + lift))
        row.demand = round_half_up(row.demand * (1 + lift))


async def keep_brands(ctx: TickContext, tally: StaplesTally) -> None:
    table = ctx.rules.brands
    made = await outputs(ctx)
    renowned = await renowned_by(ctx)
    brands = {row.workshop_id: row for row in await ctx.session.scalars(select(BrandRow))}
    for workshop in await ctx.session.scalars(select(WorkshopRow).order_by(WorkshopRow.id)):
        community = await ctx.session.get(EntityRow, workshop.community_entity_id)
        if community is None or held(community.id):
            continue
        run = made.get((community.id, workshop.kind))
        brand = brands.get(workshop.id)
        if brand is None:
            if run is None or workshop.level < table.level or run.quality < table.quality:
                continue
            brand = BrandRow(
                workshop_id=workshop.id,
                community_entity_id=community.id,
                owner_node_id=workshop.owner_node_id or community.id,
                name=f"{community.name} {workshop.kind.value.replace('_', ' ')}",
                quality=run.quality,
                since_epoch=ctx.epoch,
                locked=[],
            )
            ctx.session.add(brand)
            tally.earned += 1
            await record(ctx, "brands.earned", roles={IncidentRole.SUBJECT: community.id}, facts={"brand": brand.name, "quality": brand.quality})
        tally.brands += 1
        if run is not None:
            put(brand, "quality", run.quality)
        put(brand, "renowned", renowned.get(community.id, 0))
        aim = clamp_int(brand.quality + brand.renowned * table.renown_pct, 0, PERCENT)
        shift(brand, "reputation", (aim - brand.reputation) * table.drift_pct / PERCENT)
        profile = await ctx.session.get(SettlementProfileRow, community.id)
        crime = profile.crime if profile is not None else 0
        fakes = clamp_int(brand.reputation * crime / PERCENT * table.counterfeit_pct / PERCENT, 0, PERCENT)
        shift(brand, "counterfeits", (fakes - brand.counterfeits) * table.drift_pct / PERCENT)
        shift(brand, "reputation", -brand.counterfeits * table.erosion_pct / PERCENT / PERCENT * brand.reputation)
        if brand.counterfeits > 0:
            tally.counterfeited += 1
        put(brand, "owner_node_id", workshop.owner_node_id or community.id)
        owner = await ctx.session.get(EntityRow, brand.owner_node_id) if brand.owner_node_id is not None else None
        if run is not None and owner is not None and not held(owner.id):
            premium = run.quantity * await price_of(ctx, community.id, run.commodity) * brand.reputation / PERCENT * table.premium_pct / PERCENT
            await give_coin(ctx.session, ctx.rules, owner, min(table.coin_cap, round_half_up(premium)))
        if run is not None:
            await lift_market(ctx, community.id, run.commodity, brand.reputation * table.premium_pct / PERCENT / PERCENT)
        shift_stat(community, "prosperity", min(table.prosperity_cap, brand.reputation // HALF))


async def keep_staples(ctx: TickContext, tally: StaplesTally) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    faith = await FaithBook.load(ctx.session)
    book = await RealmBook.load(ctx.session)
    await designate(ctx, atlas, faith, book, tally)
    await keep_keystones(ctx, atlas, faith, book, tally)
    await keep_brands(ctx, tally)
    await ctx.session.flush()
