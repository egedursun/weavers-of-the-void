from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.estates import HolyOrderProfileRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.society import SocialClass
from aerona.domain.models.entity_stats import FactionStats
from aerona.engine.context import TickContext
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.faith import patron_node
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.society import class_shares
from aerona.engine.primitives.stats import set_stats, stat

POWER = 3
WEALTH = "wealth"


@dataclass
class OrderTally:
    founded: int = 0
    tithed: int = 0
    garrisoned: int = 0


async def ordered(ctx: TickContext, cult_id: int) -> bool:
    found = await ctx.session.scalar(select(HolyOrderProfileRow.faction_entity_id).where(HolyOrderProfileRow.cult_entity_id == cult_id).limit(1))
    return found is not None


async def border_town(ctx: TickContext, atlas: RegionAtlas, cult: EntityRow, towns: list[EntityRow]) -> EntityRow | None:
    god = await patron_node(ctx.session, cult)
    patrons = {town.id: await patron_node(ctx.session, town) for town in towns}
    faithful = [town for town in towns if patrons[town.id] == god]
    for town in faithful:
        region = atlas.top_region(town.id)
        neighbours = set(atlas.neighbour_regions(region)) if region is not None else set()
        if any(patrons[other.id] != god for other in towns if atlas.top_region(other.id) in neighbours):
            return town
    return faithful[0] if faithful else None


async def found_orders(ctx: TickContext, atlas: RegionAtlas, tally: OrderTally) -> None:
    table = ctx.rules.holy_orders
    towns = list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    )
    for cult in list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.CULT, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    ):
        if held(cult.id) or await ordered(ctx, cult.id) or cult.location_id is None:
            continue
        shares = await class_shares(ctx.session, ctx.rules, cult.location_id)
        if shares.get(SocialClass.WARRIOR, 0.0) < table.warrior_share or not ctx.rng(seed_of("order.found", cult.id, ctx.epoch)).chance(table.found_pct):
            continue
        fortress = await border_town(ctx, atlas, cult, towns)
        faction = await create_record(
            ctx,
            RecordSpec(
                entity_type=EntityType.FACTION,
                name=f"the Holy Order of {cult.name}",
                body=f"Sworn warriors of {cult.name}, keeping its borders and fighting its wars.",
                stats=FactionStats(strength=PERCENT * 2 // 5, wealth=PERCENT // 5, sway=PERCENT // 5),
                power=POWER,
                location_id=fortress.id if fortress is not None else cult.location_id,
                world_id=cult.world_id,
                subtype="holy order",
                affiliated_entity_id=cult.id,
            ),
        )
        ctx.session.add(
            FactionProfileRow(
                faction_entity_id=faction.id,
                kind=FactionKind.HOLY_ORDER,
                home_entity_id=fortress.id if fortress else cult.location_id,
                influence_over={},
                armed=True,
                locked=[],
            )
        )
        ctx.session.add(
            HolyOrderProfileRow(
                faction_entity_id=faction.id, cult_entity_id=cult.id, fortress_entity_id=fortress.id if fortress else None, tithe_share=PERCENT // 10, locked=[]
            )
        )
        tally.founded += 1


async def tend_orders(ctx: TickContext, tally: OrderTally) -> None:
    table = ctx.rules.holy_orders
    await found_orders(ctx, await RegionAtlas.load(ctx.session), tally)
    for row in list(await ctx.session.scalars(select(HolyOrderProfileRow).order_by(HolyOrderProfileRow.faction_entity_id))):
        order = await ctx.session.get(EntityRow, row.faction_entity_id)
        if order is None or order.status is not EntityStatus.CANON or held(order.id):
            continue
        cult = await ctx.session.get(EntityRow, row.cult_entity_id) if row.cult_entity_id is not None else None
        if cult is not None and cult.status is EntityStatus.CANON:
            gift = table.tithe_wealth * row.tithe_share // (PERCENT // 10)
            set_stats(order, wealth=clamp_int((stat(order, WEALTH) or 0) + gift, 0, PERCENT))
            tally.tithed += 1
        town = await ctx.session.get(SettlementProfileRow, row.fortress_entity_id) if row.fortress_entity_id is not None else None
        fortress = await ctx.session.get(EntityRow, row.fortress_entity_id) if row.fortress_entity_id is not None else None
        if town is not None and fortress is not None and not held(fortress.id):
            set_stats(fortress, defense=clamp_int((stat(fortress, "defense") or 0) + table.fortress_defense, 0, PERCENT))
            tally.garrisoned += 1
