from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.materials import MATERIALS
from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.constructs import ConstructRow, InstructionOrderRow, InstructionSetRow
from aerona.db.tables.ecology import BeastProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.intrigue import SchemeRow
from aerona.db.tables.military import ArmyProfileRow, ArmyUnitRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.constructs import CommandToken, MindWill, OrderCondition, OrderKind
from aerona.domain.enums.culture import MagicSource
from aerona.domain.enums.ecology import BeastTemper
from aerona.domain.enums.economy import GoodsFlow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.society import Commodity
from aerona.domain.enums.structure import ConstructionState
from aerona.engine.constructs.making import Design, make_construct
from aerona.engine.constructs.wards import realm_of_army
from aerona.engine.context import TickContext
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import connect, living_entity
from aerona.engine.primitives.records import heir_of, retire_in, valid_location
from aerona.engine.primitives.society import shift_stock, stock
from aerona.engine.primitives.stats import set_stats, stat_or
from aerona.engine.sacred.places import at_war, realm_for, realm_of_town, region_of, ruler_of, town_of

PER_MILLE = 1000
LITERAL = 50
WILL_LADDER = (MindWill.INSTRUCTED, MindWill.EMERGENT, MindWill.FULL, MindWill.EXCEEDING)
FREE_WILLS = frozenset({MindWill.FULL, MindWill.EXCEEDING})
OWNED_TOKENS = frozenset({CommandToken.ITEM, CommandToken.NETWORK_KEY})


@dataclass
class OrderTally:
    acted: int = 0
    lapsed: int = 0
    seized: int = 0
    woke: int = 0
    freed: int = 0
    killed: int = 0
    ran_down: int = 0
    replicated: int = 0
    risen: int = 0


@dataclass
class Charge:
    construct: EntityRow
    row: ConstructRow
    rules: InstructionSetRow
    order: InstructionOrderRow
    target: EntityRow | None
    holder: EntityRow | None


async def owner_of_item(ctx: TickContext, item_id: int | None) -> int | None:
    if item_id is None:
        return None
    found = await ctx.session.scalar(
        select(BondRow.source_node_id)
        .where(BondRow.target_node_id == item_id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE)
        .order_by(BondRow.id.desc())
        .limit(1)
    )
    return int(found) if found is not None else None


async def holder_of(ctx: TickContext, rules: InstructionSetRow) -> int | None:
    if rules.command_token in OWNED_TOKENS:
        return await owner_of_item(ctx, rules.token_entity_id)
    if rules.command_token is CommandToken.OFFICE:
        return await ruler_of(ctx.session, rules.token_entity_id)
    current = await ctx.session.get(EntityRow, rules.holder_node_id) if rules.holder_node_id is not None else None
    if rules.command_token is CommandToken.BLOODLINE and current is not None and await living_entity(ctx.session, current.id) is None:
        heir = await heir_of(ctx.session, current)
        return heir.id if heir is not None and heir.entity_type is EntityType.MORTAL else None
    return current.id if current is not None and await living_entity(ctx.session, current.id) is not None else None


async def resolve_holder(ctx: TickContext, construct: EntityRow, rules: InstructionSetRow, tally: OrderTally) -> EntityRow | None:
    found = await holder_of(ctx, rules)
    if found != rules.holder_node_id and "holder_node_id" not in rules.locked:
        if found is not None and rules.holder_node_id is not None:
            tally.seized += 1
            await note(ctx, f"{construct.name} answers a new holder.", key="construct.seized", ids=[construct.id, found])
        rules.holder_node_id = found
    return await living_entity(ctx.session, rules.holder_node_id)


async def holds(ctx: TickContext, charge: Charge) -> bool:
    order, rules = charge.order, charge.rules
    if order.condition is OrderCondition.ALWAYS:
        return True
    if order.condition is OrderCondition.WHILE_MAKER_LIVES:
        return await living_entity(ctx.session, charge.row.maker_entity_id) is not None
    if order.condition is OrderCondition.UNTIL_DATE:
        return order.until_epoch is None or ctx.epoch <= order.until_epoch
    if order.condition is OrderCondition.WHEN_ATTACKED:
        ward = charge.target or charge.holder
        town = await town_of(ctx.session, ward) if ward is not None else None
        realm = await realm_of_town(ctx.session, town.id) if town is not None else None
        return realm is not None and await at_war(ctx.session, realm)
    if rules.holder_node_id is None or charge.holder is None:
        return False
    return await town_of(ctx.session, charge.holder) == await town_of(ctx.session, charge.construct)


def lapses(ctx: TickContext, order: InstructionOrderRow, maker_alive: bool) -> bool:
    if order.condition is OrderCondition.WHILE_MAKER_LIVES:
        return not maker_alive
    return order.condition is OrderCondition.UNTIL_DATE and order.until_epoch is not None and ctx.epoch > order.until_epoch


async def town_target(ctx: TickContext, charge: Charge) -> EntityRow | None:
    return await town_of(ctx.session, charge.target) if charge.target is not None else None


async def do_guard(ctx: TickContext, charge: Charge) -> bool:
    ward = charge.target
    if ward is None or held(ward.id) or stat_or(ward, "defense", -1) < 0:
        return False
    set_stats(ward, defense=clamp_int(stat_or(ward, "defense", 0) + ctx.rules.constructs.guard_defense, 0, PERCENT))
    return True


async def do_serve(ctx: TickContext, charge: Charge) -> bool:
    town = await town_target(ctx, charge)
    if town is None or held(town.id):
        return False
    return await shift_stock(ctx.session, ctx.rules, town.id, Commodity.GOODS, ctx.rules.constructs.serve_goods, epoch=ctx.epoch, flow=GoodsFlow.PRODUCTION)


async def do_gather(ctx: TickContext, charge: Charge) -> bool:
    town = await town_target(ctx, charge)
    if town is None or held(town.id):
        return False
    return await shift_stock(ctx.session, ctx.rules, town.id, Commodity.ORE, ctx.rules.constructs.gather_ore, epoch=ctx.epoch, flow=GoodsFlow.EXTRACTION)


async def works_at(ctx: TickContext, charge: Charge, states: tuple[ConstructionState, ...]) -> list[StructureProfileRow]:
    if charge.target is None:
        return []
    if charge.target.entity_type is EntityType.STRUCTURE:
        own = await ctx.session.get(StructureProfileRow, charge.target.id)
        return [own] if own is not None and own.construction_state in states else []
    town = await town_target(ctx, charge)
    if town is None:
        return []
    rows = await ctx.session.scalars(
        select(StructureProfileRow)
        .where(StructureProfileRow.host_entity_id == town.id, StructureProfileRow.construction_state.in_(list(states)))
        .order_by(StructureProfileRow.structure_entity_id)
        .limit(1)
    )
    return list(rows)


async def do_build(ctx: TickContext, charge: Charge) -> bool:
    for work in await works_at(ctx, charge, (ConstructionState.PLANNED, ConstructionState.BUILDING)):
        if held(work.structure_entity_id) or "progress" in work.locked:
            continue
        work.progress = clamp_int(work.progress + ctx.rules.constructs.build_progress, 0, PERCENT)
        return True
    return False


async def do_maintain(ctx: TickContext, charge: Charge) -> bool:
    for work in await works_at(ctx, charge, (ConstructionState.COMPLETE, ConstructionState.DAMAGED)):
        if held(work.structure_entity_id) or "condition" in work.locked:
            continue
        work.condition = clamp_int(work.condition + ctx.rules.constructs.maintain_repair, 0, PERCENT)
        return True
    return False


async def do_protect(ctx: TickContext, charge: Charge) -> bool:
    ward = charge.target or charge.holder
    if ward is None or held(ward.id) or ward.entity_type is not EntityType.MORTAL:
        return False
    set_stats(ward, hp=stat_or(ward, "hp", 0) + ctx.rules.constructs.protect_health)
    return True


async def do_destroy(ctx: TickContext, charge: Charge) -> bool:
    table = ctx.rules.constructs
    foe = charge.target
    if foe is None or held(foe.id) or foe.id == charge.construct.id:
        return False
    if foe.entity_type is EntityType.STRUCTURE:
        work = await ctx.session.get(StructureProfileRow, foe.id)
        if work is None or "condition" in work.locked:
            return False
        work.condition = clamp_int(work.condition - table.destroy_harm, 0, PERCENT)
        return True
    if foe.entity_type is EntityType.SETTLEMENT:
        people = stat_or(foe, "population", 0)
        set_stats(foe, population=max(0, people - round_half_up(people * table.destroy_per_mille / PER_MILLE)))
        return True
    if stat_or(foe, "defense", -1) >= 0:
        set_stats(foe, defense=clamp_int(stat_or(foe, "defense", 0) - table.destroy_harm, 0, PERCENT))
        return True
    return False


async def do_report(ctx: TickContext, charge: Charge) -> bool:
    ward = charge.target or charge.holder
    if ward is None or charge.holder is None:
        return False
    found = False
    for scheme in await ctx.session.scalars(
        select(SchemeRow).where(SchemeRow.target_node_id == ward.id, SchemeRow.ended_epoch.is_(None)).order_by(SchemeRow.id)
    ):
        if held(scheme.owner_node_id) or charge.holder.id in scheme.discovered_by or "discovered_by" in scheme.locked:
            continue
        if ctx.rng(f"construct.report.{charge.construct.id}.{scheme.id}.{ctx.epoch}").chance(ctx.rules.constructs.report_chance):
            scheme.discovered_by = [*scheme.discovered_by, charge.holder.id]
            found = True
    return found


async def do_replicate(ctx: TickContext, charge: Charge) -> bool:
    table = ctx.rules.constructs
    town = await town_of(ctx.session, charge.construct)
    maker = charge.holder
    if town is None or maker is None or held(town.id) or held(maker.id):
        return False
    if await stock(ctx.session, ctx.rules, town.id, Commodity.ORE) < table.replicate_ore:
        return False
    await shift_stock(ctx.session, ctx.rules, town.id, Commodity.ORE, -table.replicate_ore, epoch=ctx.epoch, flow=GoodsFlow.CONSTRUCTION)
    orders = list(await ctx.session.scalars(select(InstructionOrderRow).where(InstructionOrderRow.set_id == charge.rules.id).order_by(InstructionOrderRow.id)))
    made = await make_construct(
        ctx,
        maker,
        Design(
            material=charge.row.material,
            source=charge.row.power_source,
            token=charge.rules.command_token,
            orders=[(order.kind, order.priority) for order in orders],
        ),
    )
    copy = await ctx.session.scalar(select(InstructionSetRow).where(InstructionSetRow.owner_entity_id == made.entity_id).limit(1))
    if copy is not None and charge.rules.command_token in OWNED_TOKENS:
        copy.token_entity_id = charge.rules.token_entity_id
    return True


async def do_follow(ctx: TickContext, charge: Charge) -> bool:
    lead = charge.target or charge.holder
    place = await valid_location(ctx.session, charge.construct.entity_type, lead.location_id) if lead is not None else None
    if place is None or charge.construct.location_id == place.id:
        return False
    charge.construct.location_id = place.id
    return True


async def do_forbid(ctx: TickContext, charge: Charge) -> bool:
    ward = charge.target or charge.construct
    region = await region_of(ctx.session, ward)
    if region is None:
        return False
    own_realm = await realm_for(ctx.session, ward)
    hurt = False
    for army, unit in await ctx.session.execute(
        select(ArmyProfileRow, ArmyUnitRow)
        .join(ArmyUnitRow, ArmyUnitRow.army_entity_id == ArmyProfileRow.army_entity_id)
        .where(ArmyProfileRow.region_entity_id == region.id)
        .order_by(ArmyUnitRow.id)
    ):
        host = await ctx.session.get(EntityRow, army.army_entity_id)
        if host is None or held(host.id) or "organisation" in unit.locked or await realm_of_army(ctx, host.id) == own_realm:
            continue
        unit.organisation = clamp_int(unit.organisation - ctx.rules.constructs.forbid_organisation, 0, PERCENT)
        hurt = True
    return hurt


async def do_nothing(ctx: TickContext, charge: Charge) -> bool:
    return charge.holder is not None and ctx.epoch >= 0


EFFECTS: dict[OrderKind, Callable[[TickContext, Charge], Awaitable[bool]]] = {
    OrderKind.GUARD: do_guard,
    OrderKind.SERVE: do_serve,
    OrderKind.OBEY_HOLDER: do_nothing,
    OrderKind.BUILD: do_build,
    OrderKind.GATHER: do_gather,
    OrderKind.PROTECT: do_protect,
    OrderKind.DESTROY: do_destroy,
    OrderKind.REPORT: do_report,
    OrderKind.MAINTAIN: do_maintain,
    OrderKind.REPLICATE: do_replicate,
    OrderKind.HOLD_STILL: do_nothing,
    OrderKind.FOLLOW: do_follow,
    OrderKind.FORBID: do_forbid,
}


async def target_for(ctx: TickContext, rules: InstructionSetRow, order: InstructionOrderRow, holder: EntityRow | None) -> EntityRow | None:
    if order.target_node_id is not None:
        found = await living_entity(ctx.session, order.target_node_id)
        if found is not None:
            return found
    return holder if order.target_node_id is not None and rules.literalness < LITERAL else None


async def obey(ctx: TickContext, construct: EntityRow, row: ConstructRow, rules: InstructionSetRow, tally: OrderTally) -> None:
    holder = await resolve_holder(ctx, construct, rules, tally)
    beast = await ctx.session.get(BeastProfileRow, construct.id)
    if beast is not None and row.will not in FREE_WILLS and "bound_to_node_id" not in beast.locked:
        beast.bound_to_node_id = holder.id if holder is not None else beast.bound_to_node_id
    maker_alive = await living_entity(ctx.session, row.maker_entity_id) is not None
    orders = list(
        await ctx.session.scalars(
            select(InstructionOrderRow)
            .where(InstructionOrderRow.set_id == rules.id, InstructionOrderRow.lapsed.is_(False))
            .order_by(InstructionOrderRow.priority, InstructionOrderRow.id)
        )
    )
    for order in orders:
        if lapses(ctx, order, maker_alive) and "lapsed" not in order.locked:
            order.lapsed = True
            tally.lapsed += 1
            continue
        if order.kind is OrderKind.OBEY_HOLDER and row.will in FREE_WILLS:
            continue
        charge = Charge(construct, row, rules, order, await target_for(ctx, rules, order, holder), holder)
        if not await holds(ctx, charge):
            continue
        if order.kind is OrderKind.HOLD_STILL:
            return
        if await EFFECTS[order.kind](ctx, charge):
            tally.acted += 1
            tally.replicated += order.kind is OrderKind.REPLICATE


async def grow_will(ctx: TickContext, construct: EntityRow, row: ConstructRow, tally: OrderTally) -> None:
    if row.soul_entity_id is None or row.will not in WILL_LADDER or row.will is MindWill.EXCEEDING or "will" in row.locked:
        return
    if not ctx.rng(f"construct.will.{construct.id}.{ctx.epoch}").chance(ctx.rules.constructs.will_chance):
        return
    row.will = WILL_LADDER[WILL_LADDER.index(row.will) + 1]
    tally.woke += 1
    await note(ctx, f"{construct.name} grew in will.", key="construct.will", ids=[construct.id])
    if row.will is MindWill.EXCEEDING:
        beast = await ctx.session.get(BeastProfileRow, construct.id)
        if beast is not None and "temper" not in beast.locked:
            beast.temper, beast.bound_to_node_id = BeastTemper.TERRITORIAL, None
        tally.freed += 1
        await note(ctx, f"{construct.name} slipped every order it was given.", key="construct.freed", ids=[construct.id])
        maker = await living_entity(ctx.session, row.maker_entity_id)
        if maker is not None and not held(maker.id):
            await connect(ctx.session, construct.id, maker.id, BondKind.ENEMY, ctx.epoch, description="rose against its maker")
            tally.risen += 1
            await note(ctx, f"{construct.name} rose against {maker.name}, who made it.", key="construct.risen", ids=[construct.id, maker.id])


async def pull_switch(ctx: TickContext, construct: EntityRow, row: ConstructRow, rules: InstructionSetRow, tally: OrderTally) -> bool:
    if not rules.kill_switch or row.will is not MindWill.EXCEEDING:
        return False
    keeper = await owner_of_item(ctx, rules.kill_token_entity_id) if rules.kill_token_entity_id is not None else rules.holder_node_id
    if keeper is None or held(keeper) or await living_entity(ctx.session, keeper) is None:
        return False
    await unmake(ctx, construct, "stilled by its kill switch")
    tally.killed += 1
    return True


async def unmake(ctx: TickContext, construct: EntityRow, why: str) -> None:
    await retire_in(ctx, construct, why, close_bonds=True)
    await note(ctx, f"{construct.name} was {why}.", key="construct.ended", ids=[construct.id])


async def renew(ctx: TickContext, row: ConstructRow, maker: EntityRow | None) -> int:
    table = ctx.rules.constructs
    if maker is None or held(maker.id):
        return 0
    if row.power_source is MagicSource.BLOOD:
        hp = stat_or(maker, "hp", 0)
        if hp <= 1:
            return 0
        set_stats(maker, hp=max(1, hp - table.renew // 4))
    if row.power_source is MagicSource.REAGENT:
        town = await town_of(ctx.session, maker)
        if (
            town is None
            or held(town.id)
            or not await shift_stock(ctx.session, ctx.rules, town.id, Commodity.GOODS, -table.renew, epoch=ctx.epoch, flow=GoodsFlow.INPUT)
        ):
            return 0
    return table.renew


async def wear(ctx: TickContext, construct: EntityRow, row: ConstructRow, tally: OrderTally) -> bool:
    table = ctx.rules.constructs
    maker = await living_entity(ctx.session, row.maker_entity_id)
    upkeep = row.upkeep // 2 if row.power_source is MagicSource.DIVINE and maker is not None else row.upkeep
    if "power" not in row.locked:
        row.power = clamp_int(row.power - upkeep + await renew(ctx, row, maker), 0, PERCENT)
    if "decay" not in row.locked:
        hardness = MATERIALS[row.material].hardness
        row.decay = clamp_int(row.decay + max(1, round_half_up(table.wear * (PERCENT - hardness) / PERCENT * 2)), 0, PERCENT)
    if row.power > 0 and row.decay < PERCENT:
        return False
    await unmake(ctx, construct, "run down" if row.power == 0 else "worn away")
    tally.ran_down += 1
    return True


async def keep_constructs(ctx: TickContext, tally: OrderTally) -> None:
    rows = list(await ctx.session.scalars(select(ConstructRow).order_by(ConstructRow.entity_id)))
    for row in rows:
        construct = await living_entity(ctx.session, row.entity_id)
        if construct is None or held(construct.id):
            continue
        rules = await ctx.session.scalar(
            select(InstructionSetRow).where(InstructionSetRow.owner_entity_id == construct.id).order_by(InstructionSetRow.id).limit(1)
        )
        await grow_will(ctx, construct, row, tally)
        if rules is not None and await pull_switch(ctx, construct, row, rules, tally):
            continue
        if await wear(ctx, construct, row, tally):
            continue
        if rules is not None and row.will is not MindWill.EXCEEDING:
            await obey(ctx, construct, row, rules, tally)
    await ctx.session.flush()
