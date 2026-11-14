from collections.abc import Mapping
from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.customs import IntoxicantCustomRow
from aerona.db.tables.economy import CommunityStockRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.gatherings import GatheringGuestRow, GatheringRow
from aerona.db.tables.sacred import MysticRow
from aerona.db.write_guard import held
from aerona.domain.enums.affliction import PackageKind, Transmission
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.customs import Intoxicant, IntoxicantUse
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import ValueAxis, ValueHolder
from aerona.engine.body.afflictions import afflict
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.mind.book import stored_values
from aerona.engine.notes import note
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.stats import stat_or

PACKAGES: Mapping[Intoxicant, PackageKind] = {
    Intoxicant.BREW: PackageKind.DRINK_DEPENDENCE,
    Intoxicant.WINE: PackageKind.DRINK_DEPENDENCE,
    Intoxicant.SPIRITS: PackageKind.DRINK_DEPENDENCE,
    Intoxicant.SMOKE: PackageKind.DRUG_DEPENDENCE,
    Intoxicant.LEAF: PackageKind.DRUG_DEPENDENCE,
    Intoxicant.FUNGUS: PackageKind.DRUG_DEPENDENCE,
    Intoxicant.ESSENCE: PackageKind.VIS_DEPENDENCE,
}
HUNDRED = 100
DRINKS = frozenset({Intoxicant.BREW, Intoxicant.WINE, Intoxicant.SPIRITS})


@dataclass
class IntoxicationTally:
    seeded: int = 0
    habits: int = 0
    brawls: int = 0
    visions: int = 0
    brewed: int = 0


async def customs_of(ctx: TickContext, people_id: int) -> list[IntoxicantCustomRow]:
    return list(
        await ctx.session.scalars(select(IntoxicantCustomRow).where(IntoxicantCustomRow.people_entity_id == people_id).order_by(IntoxicantCustomRow.intoxicant))
    )


async def seed_customs(ctx: TickContext, people: EntityRow, tally: IntoxicationTally) -> list[IntoxicantCustomRow]:
    found = await customs_of(ctx, people.id)
    if found:
        return found
    values = await stored_values(ctx.session, ValueHolder.CULTURE, people.id)
    rng = ctx.rng(seed_of("intoxicants", people.id))
    leisure, piety = values.get(ValueAxis.LEISURE, 0), values.get(ValueAxis.PIETY, 0)
    for intoxicant in rng.sample(list(Intoxicant), min(len(Intoxicant), ctx.rules.intoxication.customs_per_people)):
        use = IntoxicantUse.RITE if piety > leisure and rng.chance(50) else IntoxicantUse.DAILY if leisure > 0 and rng.chance(50) else IntoxicantUse.FEAST
        row = IntoxicantCustomRow(people_entity_id=people.id, intoxicant=intoxicant, use=use, acceptance=max(0, min(PERCENT, 50 + leisure // 2)), locked=[])
        ctx.session.add(row)
        found.append(row)
    tally.seeded += 1
    return found


async def habits(ctx: TickContext, people: EntityRow, row: IntoxicantCustomRow, tally: IntoxicationTally) -> None:
    folk = await ctx.session.scalars(
        select(EntityRow)
        .where(await present_among(ctx.session, [people.id]), EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    chance = ctx.rules.intoxication.habit_chance * row.acceptance / PERCENT
    for mortal in list(folk):
        if held(mortal.id) or not ctx.rng(seed_of("habit", mortal.id, row.intoxicant.value, ctx.epoch)).chance(chance):
            continue
        if await afflict(ctx, mortal, PACKAGES[row.intoxicant], Transmission.INGESTION) is not None:
            tally.habits += 1


async def brawls(ctx: TickContext, people: EntityRow, tally: IntoxicationTally) -> None:
    towns = list(
        await ctx.session.scalars(select(EntityRow.id).where(EntityRow.affiliated_entity_id == people.id, EntityRow.entity_type == EntityType.SETTLEMENT))
    )
    if not towns:
        return
    for gathering in list(
        await ctx.session.scalars(
            select(GatheringRow).where(GatheringRow.epoch == ctx.epoch, GatheringRow.place_entity_id.in_(towns)).order_by(GatheringRow.id)
        )
    ):
        if not ctx.rng(seed_of("brawl", gathering.id)).chance(ctx.rules.intoxication.brawl_chance):
            continue
        guests = list(
            await ctx.session.scalars(
                select(GatheringGuestRow.node_id).where(GatheringGuestRow.gathering_id == gathering.id, GatheringGuestRow.attended.is_(True))
            )
        )
        hurt = await ctx.session.get(EntityRow, ctx.rng(seed_of("brawl.hurt", gathering.id)).pick(guests)) if guests else None
        if hurt is None or held(hurt.id) or hurt.entity_type is not EntityType.MORTAL:
            continue
        await apply_hits(
            ctx, hurt, Harm(damage=ctx.rules.intoxication.brawl_damage, cause=HarmCause.ACCIDENT, death_cause="died of a brawl at a gathering"), lethal=False
        )
        tally.brawls += 1
        await note(ctx, f"Drink ran high at a gathering and {hurt.name} was hurt in a brawl.", key="intoxication.brawl", ids=[hurt.id])


async def visions(ctx: TickContext, people: EntityRow, tally: IntoxicationTally) -> None:
    seekers = await ctx.session.scalars(
        select(MysticRow)
        .join(EntityRow, EntityRow.id == MysticRow.mortal_entity_id)
        .where(await present_among(ctx.session, [people.id]), EntityRow.status == EntityStatus.CANON)
    )
    for mystic in list(seekers):
        if held(mystic.mortal_entity_id) or not ctx.rng(seed_of("vision.intoxicant", mystic.mortal_entity_id, ctx.epoch)).chance(
            ctx.rules.intoxication.vision_chance
        ):
            continue
        if "visions" not in mystic.locked:
            mystic.visions += 1
        mystic.last_vision_epoch = ctx.epoch
        tally.visions += 1


async def brew(ctx: TickContext, people: EntityRow, tally: IntoxicationTally) -> None:
    for town in list(
        await ctx.session.scalars(
            select(EntityRow).where(
                EntityRow.affiliated_entity_id == people.id, EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON
            )
        )
    ):
        if held(town.id):
            continue
        want = round_half_up(stat_or(town, "population", 0) / HUNDRED * ctx.rules.intoxication.brew_per_100)
        lot = await ctx.session.scalar(
            select(CommunityStockRow)
            .where(CommunityStockRow.community_entity_id == town.id, CommunityStockRow.commodity == CommodityKind.BREW_BASE, CommunityStockRow.held.is_(False))
            .limit(1)
        )
        taken = min(want, lot.quantity) if lot is not None else 0
        if lot is not None and taken > 0:
            lot.quantity -= taken
            tally.brewed += taken


async def keep_intoxication(ctx: TickContext, tally: IntoxicationTally) -> None:
    for people in list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    ):
        if held(people.id):
            continue
        rows = await seed_customs(ctx, people, tally)
        uses = {row.use for row in rows}
        for row in rows:
            if row.use is IntoxicantUse.DAILY:
                await habits(ctx, people, row, tally)
        if IntoxicantUse.FEAST in uses and any(row.intoxicant in DRINKS for row in rows):
            await brawls(ctx, people, tally)
        if IntoxicantUse.RITE in uses:
            await visions(ctx, people, tally)
        if uses & {IntoxicantUse.DAILY, IntoxicantUse.FEAST}:
            await brew(ctx, people, tally)
    await ctx.session.flush()
