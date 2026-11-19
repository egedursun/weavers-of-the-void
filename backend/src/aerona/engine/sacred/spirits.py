from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.catalog.sacred import PLACE_SPIRITS, SPIRIT_RANKS, WOODLAND_SPIRITS
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.industry import RegionPollutionRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.place import PlaceProfileRow
from aerona.db.tables.sacred import GeniusLocusRow, SpiritOfficeRow
from aerona.db.write_guard import held
from aerona.domain.enums.economy import GoodsFlow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.sacred import BureauRank, GeniusLocusKind, SpiritOffence
from aerona.domain.enums.society import Commodity
from aerona.domain.models.entity_stats import SpiritStats
from aerona.engine.context import TickContext
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.numbers import clamp_int, round_half_up, scaled_cap
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.society import shift_stock, stock
from aerona.engine.primitives.stats import set_stats, stat_or
from aerona.engine.recording.record import record
from aerona.engine.sacred.places import region_of

PLACE_SPIRIT = "place spirit"
RANKS = tuple(BureauRank)
SPIRIT_STRENGTH = 40
TEN = 10
TWENTY = 20
THOUSAND = 1000


@dataclass
class SpiritTally:
    bound: int = 0
    offerings: int = 0
    offended: int = 0
    favoured: int = 0
    misfortunes: int = 0


def rank_above(rank: BureauRank) -> BureauRank | None:
    index = RANKS.index(rank)
    return RANKS[index + 1] if index + 1 < len(RANKS) else None


def rank_below(rank: BureauRank) -> BureauRank | None:
    index = RANKS.index(rank)
    return RANKS[index - 1] if index > 0 else None


async def town_near(ctx: TickContext, place: EntityRow) -> EntityRow | None:
    if place.entity_type is EntityType.SETTLEMENT:
        return place
    holder = await ctx.session.get(EntityRow, place.location_id) if place.location_id is not None else None
    if holder is not None and holder.entity_type is EntityType.SETTLEMENT:
        return holder
    region = await region_of(ctx.session, place)
    if region is None:
        return None
    towns = list(
        await ctx.session.scalars(
            select(EntityRow)
            .where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON, EntityRow.location_id == region.id)
            .order_by(EntityRow.id)
        )
    )
    return max(towns, key=lambda town: (stat_or(town, "population", 0), -town.id), default=None)


async def overseer_of(ctx: TickContext, community: EntityRow | None) -> int | None:
    if community is None:
        return None
    book = await ctx.divine()
    gods, _ = await book.faithful_of(ctx.session, community.id)
    return min(gods) if gods else None


async def superior_for(ctx: TickContext, rank: BureauRank, community: EntityRow | None, region: EntityRow | None) -> int | None:
    above = rank_above(rank)
    if above is None:
        return None
    places = [item.id for item in (community, region) if item is not None]
    if not places:
        return None
    statement = (
        select(SpiritOfficeRow.spirit_entity_id)
        .where(SpiritOfficeRow.jurisdiction_entity_id.in_(places), SpiritOfficeRow.dismissed.is_(False))
        .order_by(SpiritOfficeRow.spirit_entity_id)
    )
    offices = list(await ctx.session.scalars(statement))
    rows = [await ctx.session.get(SpiritOfficeRow, office) for office in offices]
    higher = [row for row in rows if row is not None and RANKS.index(row.rank) > RANKS.index(rank)]
    return min(higher, key=lambda row: (RANKS.index(row.rank), row.spirit_entity_id)).spirit_entity_id if higher else None


async def bind_spirit(ctx: TickContext, place: EntityRow, kind: GeniusLocusKind, community: EntityRow | None, *, son_id: int | None = None) -> GeniusLocusRow:
    spirit = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.SPIRIT,
            name=f"Spirit of {place.name}",
            body=f"A spirit dwells in {place.name}.",
            stats=SpiritStats(strength=SPIRIT_STRENGTH, unrest=0),
            power=max(1, place.power_level),
            location_id=place.id,
            world_id=place.world_id,
            subtype=PLACE_SPIRIT,
            creator_son_id=son_id,
        ),
    )
    rng = ctx.rng(f"genius.{place.id}")
    row = GeniusLocusRow(
        spirit_entity_id=spirit.id,
        place_entity_id=place.id,
        community_entity_id=community.id if community is not None else None,
        kind=kind,
        temperament=rng.below(PERCENT + 1),
        contentment=ctx.rules.genius_loci.content_at,
        bound_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    rank = SPIRIT_RANKS[kind]
    region = await region_of(ctx.session, place)
    ctx.session.add(
        SpiritOfficeRow(
            spirit_entity_id=spirit.id,
            rank=rank,
            superior_spirit_id=await superior_for(ctx, rank, community, region),
            overseer_node_id=son_id if son_id is not None else await overseer_of(ctx, community),
            jurisdiction_entity_id=(community or region or place).id,
            appointed_epoch=ctx.epoch,
            locked=[],
        )
    )
    await ctx.session.flush()
    await record(ctx, "sacred.spirit_bound", roles={IncidentRole.SUBJECT: [place.id, spirit.id]})
    return row


async def unspirited(ctx: TickContext) -> list[tuple[EntityRow, GeniusLocusKind, EntityRow | None]]:
    table = ctx.rules.genius_loci
    bound = select(GeniusLocusRow.place_entity_id).where(GeniusLocusRow.place_entity_id.is_not(None))
    found: list[tuple[EntityRow, GeniusLocusKind, EntityRow | None]] = []
    places = await ctx.session.execute(
        select(EntityRow, PlaceProfileRow.kind)
        .join(PlaceProfileRow, PlaceProfileRow.entity_id == EntityRow.id)
        .where(EntityRow.status == EntityStatus.CANON, EntityRow.id.not_in(bound), PlaceProfileRow.kind.in_(list(PLACE_SPIRITS)))
        .order_by(EntityRow.id)
    )
    for place, kind in places:
        found.append((place, PLACE_SPIRITS[kind], await town_near(ctx, place)))
    towns = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON, EntityRow.id.not_in(bound))
        .order_by(EntityRow.id)
    )
    found.extend((town, GeniusLocusKind.CITY, town) for town in towns if stat_or(town, "population", 0) >= table.city_population)
    houses = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.HOUSE, EntityRow.status == EntityStatus.CANON, EntityRow.id.not_in(bound))
        .order_by(EntityRow.id)
    )
    for house in houses:
        found.append((house, GeniusLocusKind.HEARTH, await town_near(ctx, house)))
    return found


async def raise_spirits(ctx: TickContext, tally: SpiritTally) -> None:
    table = ctx.rules.genius_loci
    places = ctx.rng("genius.order").shuffled(await unspirited(ctx))
    limit = scaled_cap(table.binds_per_epoch, table.binds_place_divisor, len(places))
    for place, kind, community in places:
        if tally.bound >= limit:
            return
        if held(place.id) or not ctx.rng(f"genius.bind.{place.id}").chance(table.bind_chance):
            continue
        await bind_spirit(ctx, place, kind, community)
        tally.bound += 1


def expected(ctx: TickContext, row: GeniusLocusRow) -> int:
    table = ctx.rules.genius_loci
    touchy = table.hunger * (PERCENT + (table.touchy_hunger_pct - PERCENT) * row.temperament / PERCENT) / PERCENT
    return max(0, round_half_up(touchy))


async def spirits_kept(ctx: TickContext, community_id: int) -> int:
    statement = select(func.count()).select_from(GeniusLocusRow).where(GeniusLocusRow.community_entity_id == community_id)
    return max(1, int(await ctx.session.scalar(statement) or 0))


async def bring_offerings(ctx: TickContext, row: GeniusLocusRow, community: EntityRow | None) -> int:
    table = ctx.rules.genius_loci
    if community is None or held(community.id) or stat_or(community, "piety", 0) < table.offering_piety:
        return 0
    people = stat_or(community, "population", 0)
    kept = await spirits_kept(ctx, community.id)
    rate = table.offering_per_thousand * stat_or(community, "piety", 0) / PERCENT / kept
    given = max(1, round_half_up(people * rate / THOUSAND))
    food = await stock(ctx.session, ctx.rules, community.id, Commodity.FOOD)
    cost = round_half_up(rate * table.offering_food)
    if cost > food:
        given, cost = given * food // max(1, cost), food
    if given <= 0:
        return 0
    if cost:
        await shift_stock(ctx.session, ctx.rules, community.id, Commodity.FOOD, -cost, epoch=ctx.epoch, flow=GoodsFlow.OFFERING)
    return given


async def land_offence(ctx: TickContext, row: GeniusLocusRow, place: EntityRow) -> SpiritOffence | None:
    table = ctx.rules.genius_loci
    region = await region_of(ctx.session, place)
    if region is None:
        return None
    pollution = await ctx.session.get(RegionPollutionRow, region.id)
    if pollution is not None and max(pollution.air, pollution.water, pollution.soil) >= table.pollution_offence:
        return SpiritOffence.POLLUTION
    land = await ctx.session.get(RegionEnvironmentRow, region.id)
    if row.kind in WOODLAND_SPIRITS and land is not None and land.forest_cover < table.clearing_offence:
        return SpiritOffence.CLEARING
    return None


async def offence_of(ctx: TickContext, row: GeniusLocusRow, place: EntityRow | None) -> SpiritOffence | None:
    table = ctx.rules.genius_loci
    if row.owed > expected(ctx, row) * table.unpaid_epochs:
        return SpiritOffence.UNPAID
    if place is None:
        return None
    built = await ctx.session.scalar(
        select(func.count())
        .select_from(EntityRow)
        .where(EntityRow.entity_type == EntityType.STRUCTURE, EntityRow.location_id == place.id, EntityRow.birth_epoch == ctx.epoch)
    )
    if built and place.entity_type is EntityType.PLACE:
        return SpiritOffence.TABOO
    return await land_offence(ctx, row, place)


async def bless(ctx: TickContext, row: GeniusLocusRow, community: EntityRow) -> None:
    table = ctx.rules.genius_loci
    food = row.favour // TEN * table.favour_food
    if food:
        await shift_stock(ctx.session, ctx.rules, community.id, Commodity.FOOD, food, epoch=ctx.epoch, flow=GoodsFlow.OFFERING)
    lift = row.favour // TWENTY * table.favour_prosperity
    if lift:
        set_stats(community, prosperity=clamp_int(stat_or(community, "prosperity", 0) + lift, 0, PERCENT))


async def strike(ctx: TickContext, community: EntityRow) -> None:
    table = ctx.rules.genius_loci
    people = stat_or(community, "population", 0)
    lost = round_half_up(people * table.misfortune_per_mille / THOUSAND)
    if lost:
        set_stats(community, population=max(0, people - lost))
    mortals = select(EntityRow.id).where(
        EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, await present_among(ctx.session, [community.id])
    )
    for profile in await ctx.session.scalars(select(MortalProfileRow).where(MortalProfileRow.entity_id.in_(mortals)).order_by(MortalProfileRow.entity_id)):
        if not held(profile.entity_id) and "health" not in profile.locked:
            profile.health = max(0, profile.health - table.misfortune_health)


async def tend_spirit(ctx: TickContext, row: GeniusLocusRow, tally: SpiritTally) -> None:
    table = ctx.rules.genius_loci
    place = await living_entity(ctx.session, row.place_entity_id)
    community = await living_entity(ctx.session, row.community_entity_id)
    given = await bring_offerings(ctx, row, community)
    if given:
        row.offerings += given
        row.last_offering_epoch = ctx.epoch
        tally.offerings += given
    if "owed" not in row.locked:
        row.owed += expected(ctx, row)
    paid = min(row.offerings, row.owed)
    row.offerings -= paid
    if "owed" not in row.locked:
        row.owed -= paid
    offence = await offence_of(ctx, row, place)
    if offence is not None:
        if "offended" not in row.locked:
            row.offended = offence
        tally.offended += 1
    if "contentment" not in row.locked:
        step = table.contentment_step if offence is None and row.owed == 0 else -table.contentment_step
        row.contentment = clamp_int(row.contentment + step, 0, PERCENT)
    if offence is None and row.contentment >= table.content_at and "offended" not in row.locked:
        row.offended = None
    if "favour" not in row.locked:
        grows = row.offended is None and row.contentment >= table.content_at
        row.favour = clamp_int(row.favour + (table.favour_gain if grows else -table.favour_gain), 0, PERCENT)
    if community is None or held(community.id):
        return
    if row.offended is not None:
        await strike(ctx, community)
        tally.misfortunes += 1
    elif row.favour > 0:
        await bless(ctx, row, community)
        tally.favoured += 1


async def keep_place_spirits(ctx: TickContext, tally: SpiritTally) -> None:
    await raise_spirits(ctx, tally)
    for row in list(await ctx.session.scalars(select(GeniusLocusRow).order_by(GeniusLocusRow.spirit_entity_id))):
        if held(row.spirit_entity_id) or await living_entity(ctx.session, row.spirit_entity_id) is None:
            continue
        await tend_spirit(ctx, row, tally)
    await ctx.session.flush()
