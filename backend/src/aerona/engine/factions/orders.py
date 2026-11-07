from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.errors import ConflictError, ValidationFailedError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.estates import HolyOrderProfileRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.warfare import ArmyRow, WarRow, WarSideRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.war import WarCause, WarSide, WarStatus
from aerona.domain.models.entity_stats import FactionStats
from aerona.engine.context import TickContext
from aerona.engine.military.orders import raise_standing_army
from aerona.engine.military.support import new_side
from aerona.engine.notes import note
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.faith import patron_node
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import active_bonds, connect, living_entity
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.society import class_shares
from aerona.engine.primitives.stats import set_stats, stat
from aerona.engine.services.war import war_event

STRENGTH = "strength"
POWER = 3
WEALTH = "wealth"
VOWED = frozenset({SocialClass.WARRIOR, SocialClass.NOBLE})
HOLY_CAUSES = frozenset({WarCause.HOLY_WAR, WarCause.SCHISM})


@dataclass
class OrderTally:
    founded: int = 0
    tithed: int = 0
    garrisoned: int = 0
    sworn: int = 0
    hosts: int = 0


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
        if cult is not None and cult.status is EntityStatus.CANON:
            await take_vows(ctx, order, row, cult, tally)
            await serve_holy_wars(ctx, order, row, cult, tally)


async def vowed_of(ctx: TickContext, order: EntityRow) -> list[int]:
    return sorted(bond.source_node_id for bond in await active_bonds(ctx.session, [BondKind.MEMBER_OF], targets=[order.id]))


async def take_vows(ctx: TickContext, order: EntityRow, row: HolyOrderProfileRow, cult: EntityRow, tally: OrderTally) -> None:
    home = row.fortress_entity_id or cult.location_id
    faith = await patron_node(ctx.session, cult)
    if home is None:
        return
    sworn = set(await vowed_of(ctx, order))
    faithful = {bond.source_node_id for bond in await active_bonds(ctx.session, [BondKind.MEMBER_OF], targets=[cult.id])}
    locals_ = await ctx.session.scalars(
        select(EntityRow)
        .where(
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.location_id == home,
            EntityRow.social_class.in_(tuple(VOWED)),
        )
        .order_by(EntityRow.id)
    )
    for mortal in list(locals_):
        if mortal.id in sworn or held(mortal.id):
            continue
        if mortal.id not in faithful and (faith is None or await patron_node(ctx.session, mortal) != faith):
            continue
        if not ctx.rng(seed_of("order.vows", order.id, mortal.id, ctx.epoch)).chance(ctx.rules.holy_orders.recruit_pct):
            continue
        await connect(ctx.session, mortal.id, order.id, BondKind.MEMBER_OF, ctx.epoch, description="took the vows of the order")
        await note(ctx, f"{mortal.name} took the vows of {order.name}.", key="orders.vows", ids=[mortal.id, order.id])
        tally.sworn += 1
        return


async def faithful_side(ctx: TickContext, sides: list[WarSideRow], faith: int) -> WarSide | None:
    for side in sides:
        entity = await ctx.session.get(EntityRow, side.entity_id)
        if entity is not None and await patron_node(ctx.session, entity) == faith:
            return side.side
    return None


async def serve_holy_wars(ctx: TickContext, order: EntityRow, row: HolyOrderProfileRow, cult: EntityRow, tally: OrderTally) -> None:
    fortress = await living_entity(ctx.session, row.fortress_entity_id) if row.fortress_entity_id is not None else None
    faith = await patron_node(ctx.session, cult)
    size = (stat(order, STRENGTH) or 0) * ctx.rules.holy_orders.host_per_strength
    if fortress is None or faith is None or held(fortress.id) or size <= 0:
        return
    wars = await ctx.session.scalars(select(WarRow).where(WarRow.status == WarStatus.ONGOING, WarRow.cause.in_(tuple(HOLY_CAUSES))).order_by(WarRow.id))
    for war in list(wars):
        sides = list(await ctx.session.scalars(select(WarSideRow).where(WarSideRow.war_id == war.id, WarSideRow.left_epoch.is_(None))))
        side = await faithful_side(ctx, sides, faith)
        served = await ctx.session.scalar(select(ArmyRow.entity_id).where(ArmyRow.war_id == war.id, ArmyRow.owner_entity_id == fortress.id).limit(1))
        if side is None or served is not None:
            continue
        if fortress.id not in {item.entity_id for item in sides}:
            ctx.session.add(new_side(ctx, war.id, fortress.id, side))
            event = await war_event(ctx.session, war)
            await connect(ctx.session, fortress.id, event.id, BondKind.PARTY_TO, ctx.epoch, description="sent the order to the holy war")
        vowed = await vowed_of(ctx, order)
        try:
            host = await raise_standing_army(
                ctx, fortress.id, size, commander_id=vowed[0] if vowed else None, war_id=war.id, name=f"the host of {order.name.removeprefix('the ')}"
            )
        except (ConflictError, ValidationFailedError):
            continue
        await note(ctx, f"{order.name} rode out to the holy war as {host.name}.", key="orders.holy_war", ids=[order.id, host.id, fortress.id])
        tally.hosts += 1
