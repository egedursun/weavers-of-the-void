from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.catalog.life.arts import ROLE_WEIGHT
from aerona.constants.units import PERCENT
from aerona.db.tables.affairs import CourtRow
from aerona.db.tables.arts import ArtPriceRow, ArtSaleRow, CanonWorkRow, CollectorRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import ArtworkProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.gatherings import GatheringRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.arts import ArtMarketRole
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import FactUnit, StepAction
from aerona.engine.arts.market_roles import appoint_critics, appoint_curators, backfill_curators, keep_reviews, show_collections
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import coin_of, receive_coin, take_coin
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import close, connect, living_entity
from aerona.engine.primitives.quota import WorldQuota
from aerona.engine.recording.record import StepDraft, record
from aerona.engine.sacred.places import realm_of_town, region_of, town_of

MIDDLING = 50
COLLECTOR_ROLES = {
    EntityType.POLITY: ArtMarketRole.PATRON,
    EntityType.HOUSE: ArtMarketRole.PATRON,
    EntityType.CULT: ArtMarketRole.COLLECTOR,
    EntityType.FACTION: ArtMarketRole.DEALER,
}


@dataclass
class MarketTally:
    collectors: int = 0
    priced: int = 0
    sales: int = 0
    coin: int = 0
    lured: int = 0
    reviews: int = 0
    shown: int = 0


async def owner_of(ctx: TickContext, artwork_id: int) -> int | None:
    found = await ctx.session.scalar(
        select(BondRow.source_node_id)
        .where(BondRow.target_node_id == artwork_id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE)
        .order_by(BondRow.id.desc())
        .limit(1)
    )
    if found is not None:
        return int(found)
    profile = await ctx.session.get(ArtworkProfileRow, artwork_id)
    if profile is None:
        return None
    return profile.patron_entity_id or profile.author_entity_id


async def gather_collectors(ctx: TickContext, tally: MarketTally) -> None:
    table = ctx.rules.art_markets
    known = select(CollectorRow.holder_entity_id)
    guilds = select(FactionProfileRow.faction_entity_id).where(FactionProfileRow.kind == FactionKind.MERCHANT_GUILD)
    candidates = await ctx.session.scalars(
        select(EntityRow)
        .where(
            EntityRow.status == EntityStatus.CANON,
            EntityRow.id.not_in(known),
            (EntityRow.entity_type.in_([EntityType.POLITY, EntityType.HOUSE, EntityType.CULT])) | (EntityRow.id.in_(guilds)),
        )
        .order_by(EntityRow.id)
    )
    quota = WorldQuota(table.collectors_per_epoch)
    for holder in ctx.rng("collector.order").shuffled(candidates):
        if quota.full(holder.world_id):
            continue
        if held(holder.id) or not ctx.rng(f"collector.{holder.id}").chance(table.collector_chance):
            continue
        await start_collection(ctx, holder, None)
        quota.take(holder.world_id)
        tally.collectors += 1


async def start_collection(ctx: TickContext, holder: EntityRow, taste: int | None) -> CollectorRow:
    rng = ctx.rng(f"collector.taste.{holder.id}")
    discernment = rng.integer(MIDDLING // 2, PERCENT - MIDDLING // 2)
    role = COLLECTOR_ROLES.get(holder.entity_type, ArtMarketRole.COLLECTOR)
    if role is ArtMarketRole.COLLECTOR and discernment >= ctx.rules.art_markets.connoisseur_at:
        role = ArtMarketRole.CONNOISSEUR
    row = CollectorRow(
        holder_entity_id=holder.id,
        role=role,
        taste_form_entity_id=taste,
        connoisseurship=discernment,
        since_epoch=ctx.epoch,
        locked=[],
    )
    if taste is None:
        form = await ctx.session.scalar(
            select(ArtworkProfileRow.art_form_entity_id)
            .where(ArtworkProfileRow.art_form_entity_id.is_not(None))
            .group_by(ArtworkProfileRow.art_form_entity_id)
            .order_by(func.count().desc(), ArtworkProfileRow.art_form_entity_id)
            .limit(1)
        )
        row.taste_form_entity_id = int(form) if form is not None else None
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def interest_in(ctx: TickContext, profile: ArtworkProfileRow) -> int:
    if profile.art_form_entity_id is None:
        return 0
    roles = list(await ctx.session.execute(select(CollectorRow.role, CollectorRow.taste_form_entity_id)))
    wanting = sum(ROLE_WEIGHT[role] for role, form in roles if form == profile.art_form_entity_id)
    every = sum(ROLE_WEIGHT[role] for role, _ in roles)
    return clamp_int(round_half_up(wanting * PERCENT / max(1, every)), 0, PERCENT)


async def appraise(ctx: TickContext, artwork: EntityRow, profile: ArtworkProfileRow) -> ArtPriceRow:
    table = ctx.rules.art_markets
    row = await ctx.session.get(ArtPriceRow, artwork.id)
    if row is None:
        row = ArtPriceRow(artwork_entity_id=artwork.id, updated_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    author = await ctx.session.get(MortalProfileRow, profile.author_entity_id) if profile.author_entity_id is not None else None
    renown = author.renown if author is not None else 0
    canon = (
        profile.canon
        or await ctx.session.scalar(select(CanonWorkRow.people_entity_id).where(CanonWorkRow.artwork_entity_id == artwork.id).limit(1)) is not None
    )
    if "interest" not in row.locked:
        row.interest = await interest_in(ctx, profile)
    price = table.base_price * profile.quality / MIDDLING
    price *= 1 + table.renown_pct * renown / PERCENT / PERCENT
    price *= 1 + (table.canon_pct / PERCENT if canon else 0)
    price *= 1 + table.provenance_pct * row.provenance / PERCENT
    price *= 1 + table.interest_pct * row.interest / PERCENT / PERCENT
    price *= max(0.0, 1 + (row.acclaim or 0) / PERCENT)
    if "price" not in row.locked:
        row.price = max(0, round_half_up(price))
    row.updated_epoch = ctx.epoch
    return row


async def fair_regions(ctx: TickContext) -> dict[int, int]:
    regions: dict[int, int] = {}
    rows = await ctx.session.execute(
        select(GatheringRow.id, GatheringRow.place_entity_id)
        .where(GatheringRow.epoch == ctx.epoch, GatheringRow.place_entity_id.is_not(None))
        .order_by(GatheringRow.id)
    )
    for _, place_id in rows:
        place = await ctx.session.get(EntityRow, place_id)
        region = await region_of(ctx.session, place) if place is not None else None
        if region is not None and place is not None:
            regions.setdefault(region.id, place.id)
    return regions


async def bidders_for(ctx: TickContext, row: ArtPriceRow, profile: ArtworkProfileRow, seller_id: int | None) -> list[tuple[int, int, int, EntityRow]]:
    found: list[tuple[int, int, int, EntityRow]] = []
    for collector in list(await ctx.session.scalars(select(CollectorRow).order_by(CollectorRow.holder_entity_id))):
        if collector.holder_entity_id == seller_id or held(collector.holder_entity_id):
            continue
        holder = await living_entity(ctx.session, collector.holder_entity_id)
        purse = await coin_of(ctx.session, ctx.rules, holder) if holder is not None else 0
        if holder is None or purse < row.price:
            continue
        found.append((1 if collector.taste_form_entity_id == profile.art_form_entity_id else 0, collector.connoisseurship, purse, holder))
    return sorted(found, key=lambda item: (-item[0], -item[1], item[3].id))


async def bidder_for(ctx: TickContext, row: ArtPriceRow, profile: ArtworkProfileRow, seller_id: int | None, *, auction: bool) -> EntityRow | None:
    bidders = await bidders_for(ctx, row, profile, seller_id)
    if not bidders:
        return None
    _, _, purse, winner = bidders[0]
    if auction and len(bidders) > 1 and "price" not in row.locked:
        raised = round_half_up(row.price * (1 + ctx.rules.art_markets.auction_pct * (len(bidders) - 1) / PERCENT))
        row.price = min(purse, raised)
    return winner


async def sell(
    ctx: TickContext, artwork: EntityRow, row: ArtPriceRow, buyer: EntityRow, *, seller_id: int | None, fair_place_id: int | None
) -> ArtSaleRow | None:
    if not await take_coin(ctx.session, ctx.rules, buyer, row.price):
        return None
    seller = await living_entity(ctx.session, seller_id)
    if seller is not None:
        await receive_coin(ctx.session, ctx.rules, seller, row.price)
        for bond in await ctx.session.scalars(
            select(BondRow).where(BondRow.target_node_id == artwork.id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE)
        ):
            await close(ctx.session, bond, ctx.epoch, "sold")
    await connect(ctx.session, buyer.id, artwork.id, BondKind.OWNS, ctx.epoch, description="bought")
    sale = ArtSaleRow(
        artwork_entity_id=artwork.id,
        seller_node_id=seller.id if seller is not None else None,
        buyer_node_id=buyer.id,
        price=row.price,
        fair_place_entity_id=fair_place_id,
        epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(sale)
    if "provenance" not in row.locked:
        row.provenance += 1
    row.last_buyer_node_id = buyer.id
    row.last_sale_epoch = ctx.epoch
    await ctx.session.flush()
    await record(
        ctx,
        "arts.sold",
        roles={IncidentRole.BUYER: buyer.id, IncidentRole.SELLER: sale.seller_node_id, IncidentRole.PRODUCT: artwork.id},
        facts={"price": row.price, "provenance": row.provenance},
        steps=(StepDraft(StepAction.PAY, actor=buyer.id, target=sale.seller_node_id, amount=row.price, unit=FactUnit.COIN),),
        place=sale.fair_place_entity_id,
    )
    return sale


async def trade_works(ctx: TickContext, tally: MarketTally) -> None:
    table = ctx.rules.art_markets
    fairs = await fair_regions(ctx)
    works = await ctx.session.execute(
        select(EntityRow, ArtworkProfileRow)
        .join(ArtworkProfileRow, ArtworkProfileRow.artwork_entity_id == EntityRow.id)
        .where(EntityRow.status == EntityStatus.CANON, ArtworkProfileRow.performed.is_(False))
        .order_by(EntityRow.id)
    )
    quota = WorldQuota(table.sales_per_epoch)
    for artwork, profile in ctx.rng("sale.order").shuffled(works):
        if held(artwork.id):
            continue
        row = await appraise(ctx, artwork, profile)
        tally.priced += 1
        if quota.full(artwork.world_id) or row.price <= 0:
            continue
        region = await region_of(ctx.session, artwork)
        chance = table.sale_chance * (table.gathering_pct / PERCENT if region is not None and region.id in fairs else 1)
        if not ctx.rng(f"sale.{artwork.id}").chance(chance):
            continue
        seller = await owner_of(ctx, artwork.id)
        buyer = await bidder_for(ctx, row, profile, seller, auction=region is not None and region.id in fairs)
        if buyer is None:
            continue
        sale = await sell(ctx, artwork, row, buyer, seller_id=seller, fair_place_id=fairs.get(region.id) if region is not None else None)
        if sale is not None:
            quota.take(artwork.world_id)
            tally.sales += 1
            tally.coin += sale.price


async def held_works(ctx: TickContext, holder_id: int) -> int:
    count = await ctx.session.scalar(
        select(func.count())
        .select_from(BondRow)
        .join(EntityRow, EntityRow.id == BondRow.target_node_id)
        .where(
            BondRow.source_node_id == holder_id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE, EntityRow.entity_type == EntityType.ARTWORK
        )
    )
    return int(count or 0)


async def court_patronage(ctx: TickContext, tally: MarketTally) -> None:
    table = ctx.rules.art_markets
    courts = list(await ctx.session.scalars(select(CourtRow).order_by(CourtRow.polity_entity_id)))
    grandest: dict[int, tuple[int, int]] = {}
    for court in courts:
        if held(court.polity_entity_id):
            continue
        works = await held_works(ctx, court.polity_entity_id)
        if works and "grandeur" not in court.locked:
            court.grandeur = clamp_int(court.grandeur + works * table.grandeur_per_work, 0, PERCENT)
        realm = await ctx.session.get(EntityRow, court.polity_entity_id)
        if realm is not None and realm.world_id is not None:
            best = grandest.get(realm.world_id)
            if best is None or court.grandeur > best[0]:
                grandest[realm.world_id] = (court.grandeur, realm.id)
    authors = select(ArtworkProfileRow.author_entity_id).where(ArtworkProfileRow.author_entity_id.is_not(None))
    artists = await ctx.session.execute(
        select(EntityRow, MortalProfileRow)
        .join(MortalProfileRow, MortalProfileRow.entity_id == EntityRow.id)
        .where(EntityRow.id.in_(authors), EntityRow.status == EntityStatus.CANON, MortalProfileRow.renown >= table.lure_renown)
        .order_by(EntityRow.id)
    )
    for artist, _ in list(artists):
        target = grandest.get(artist.world_id or 0)
        if target is None or held(artist.id) or not ctx.rng(f"lure.{artist.id}").chance(table.lure_chance):
            continue
        home = await town_of(ctx.session, artist)
        if home is not None and await realm_of_town(ctx.session, home.id) == target[1]:
            continue
        seat = await ctx.session.get(PolityProfileRow, target[1])
        capital = seat.capital_entity_id if seat is not None else None
        if capital is None or held(capital):
            continue
        artist.location_id = int(capital)
        tally.lured += 1
        await record(
            ctx,
            "arts.lured",
            roles={IncidentRole.SUBJECT: artist.id, IncidentRole.PATRON: target[1], IncidentRole.DESTINATION: int(capital)},
            steps=(StepDraft(StepAction.ARRIVE, actor=artist.id, target=int(capital)),),
            place=int(capital),
        )


async def keep_roles(ctx: TickContext, tally: MarketTally) -> None:
    await backfill_curators(ctx)
    tally.collectors += await appoint_curators(ctx) + await appoint_critics(ctx)
    tally.reviews += await keep_reviews(ctx)
    tally.shown += await show_collections(ctx)
    await ctx.session.flush()


async def keep_market(ctx: TickContext, tally: MarketTally) -> None:
    await gather_collectors(ctx, tally)
    await keep_roles(ctx, tally)
    await trade_works(ctx, tally)
    await court_patronage(ctx, tally)
    await ctx.session.flush()
