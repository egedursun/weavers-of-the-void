from collections.abc import Awaitable, Callable, Mapping

from sqlalchemy import or_, select

from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.economy import TradeRouteProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.law_depth import RegistryRow
from aerona.db.tables.networks import NetworkNodeRow, NetworkOutageRow
from aerona.db.tables.powers import PowerSourceRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.economy import GoodsFlow
from aerona.domain.enums.military import SabotageKind
from aerona.domain.enums.networks import OutageCause
from aerona.domain.enums.society import Commodity
from aerona.engine.context import TickContext
from aerona.engine.lore.civics import holders_know
from aerona.engine.mortal.standing import shift_standing
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.society import shift_stock
from aerona.engine.primitives.stats import shift_stat

Strike = Callable[[TickContext, EntityRow, EntityRow], Awaitable[None]]
Fits = Callable[[TickContext, EntityRow], Awaitable[bool]]


async def networks_at(ctx: TickContext, target: EntityRow) -> list[int]:
    return sorted(set(await ctx.session.scalars(select(NetworkNodeRow.network_entity_id).where(NetworkNodeRow.member_node_id == target.id))))


async def sources_at(ctx: TickContext, target: EntityRow) -> list[PowerSourceRow]:
    scopes = [target.id, *([target.world_id] if target.world_id is not None else [])]
    return list(await ctx.session.scalars(select(PowerSourceRow).where(or_(PowerSourceRow.scope_node_id.in_(scopes))).order_by(PowerSourceRow.id)))


async def food_of(ctx: TickContext, target: EntityRow) -> int:
    society = await ctx.session.get(CommunitySocietyRow, target.id)
    return society.stock_food if society is not None else 0


async def attack_network(ctx: TickContext, _spymaster: EntityRow, target: EntityRow) -> None:
    rules = ctx.rules.espionage
    for network in await networks_at(ctx, target):
        if not held(network):
            ctx.session.add(
                NetworkOutageRow(
                    network_entity_id=network,
                    cause=OutageCause.SABOTAGE,
                    epoch=ctx.epoch,
                    epochs=rules.sabotage_outage_epochs,
                    severity=rules.sabotage_outage_severity,
                )
            )


async def break_bridges(ctx: TickContext, _spymaster: EntityRow, target: EntityRow) -> None:
    profile = await ctx.session.get(SettlementProfileRow, target.id)
    if profile is not None and "hauling_capacity" not in profile.locked:
        profile.hauling_capacity = max(0, profile.hauling_capacity - round_half_up(profile.hauling_capacity * ctx.rules.espionage.haul_damage / PERCENT))


async def release_blight(ctx: TickContext, _spymaster: EntityRow, target: EntityRow) -> None:
    lost = round_half_up(await food_of(ctx, target) * ctx.rules.espionage.blight_pct / PERCENT)
    await shift_stock(ctx.session, ctx.rules, target.id, Commodity.FOOD, -lost, epoch=ctx.epoch, flow=GoodsFlow.LOSS)
    shift_stat(target, "prosperity", -ctx.rules.espionage.spy_sabotage_damage, 0)


async def steal_supplies(ctx: TickContext, spymaster: EntityRow, target: EntityRow) -> None:
    taken = round_half_up(await food_of(ctx, target) * ctx.rules.espionage.theft_pct / PERCENT)
    await shift_stock(ctx.session, ctx.rules, target.id, Commodity.FOOD, -taken, epoch=ctx.epoch, flow=GoodsFlow.LOSS)
    if not held(spymaster.id):
        await shift_standing(ctx.session, spymaster, "wealth", ctx.rules.espionage.spy_sabotage_damage, ctx.epoch, default=0)


async def incite_mutiny(ctx: TickContext, _spymaster: EntityRow, target: EntityRow) -> None:
    profile = await ctx.session.get(SettlementProfileRow, target.id)
    if profile is not None:
        if "militia" not in profile.locked:
            profile.militia = max(0, profile.militia - round_half_up(profile.militia * ctx.rules.espionage.mutiny_militia / PERCENT))
        if "unrest" not in profile.locked:
            profile.unrest = clamp_int(profile.unrest + ctx.rules.espionage.mutiny_unrest, 0, PERCENT)


async def disrupt_rites(ctx: TickContext, _spymaster: EntityRow, target: EntityRow) -> None:
    await shift_standing(ctx.session, target, "piety", -ctx.rules.espionage.rite_piety, ctx.epoch, default=0)


async def poison_sources(ctx: TickContext, _spymaster: EntityRow, target: EntityRow) -> None:
    for source in await sources_at(ctx, target):
        if "stability" not in source.locked:
            source.stability = clamp_int(source.stability - ctx.rules.espionage.source_damage, 0, PERCENT)


async def seize_machines(ctx: TickContext, spymaster: EntityRow, target: EntityRow) -> None:
    shift_stat(target, "prosperity", -ctx.rules.espionage.spy_sabotage_damage, 0)
    if not held(spymaster.id):
        await shift_standing(ctx.session, spymaster, "wealth", ctx.rules.espionage.spy_sabotage_damage // 2, ctx.epoch, default=0)


async def tamper_records(ctx: TickContext, spymaster: EntityRow, target: EntityRow) -> None:
    row = await ctx.session.scalar(
        select(RegistryRow).where(RegistryRow.holder_entity_id == target.id, RegistryRow.owner_entity_id.is_not(None)).order_by(RegistryRow.id).limit(1)
    )
    if row is not None and "owner_entity_id" not in row.locked:
        row.owner_entity_id = spymaster.id


async def block_routes(ctx: TickContext, _spymaster: EntityRow, target: EntityRow) -> None:
    rows = await ctx.session.scalars(
        select(TradeRouteProfileRow)
        .where(or_(TradeRouteProfileRow.first_market_id == target.id, TradeRouteProfileRow.second_market_id == target.id))
        .order_by(TradeRouteProfileRow.route_entity_id)
    )
    for row in list(rows):
        if not held(row.route_entity_id) and "danger_bandits" not in row.locked:
            row.danger_bandits = clamp_int(row.danger_bandits + ctx.rules.espionage.route_block_danger, 0, PERCENT)


async def has_records(ctx: TickContext, target: EntityRow) -> bool:
    return await ctx.session.scalar(select(RegistryRow.id).where(RegistryRow.holder_entity_id == target.id).limit(1)) is not None


async def has_routes(ctx: TickContext, target: EntityRow) -> bool:
    found = await ctx.session.scalar(
        select(TradeRouteProfileRow.route_entity_id)
        .where(or_(TradeRouteProfileRow.first_market_id == target.id, TradeRouteProfileRow.second_market_id == target.id))
        .limit(1)
    )
    return found is not None


async def has_networks(ctx: TickContext, target: EntityRow) -> bool:
    return bool(await networks_at(ctx, target))


async def has_crossings(ctx: TickContext, target: EntityRow) -> bool:
    profile = await ctx.session.get(SettlementProfileRow, target.id)
    return profile is not None and profile.hauling_capacity > 0


async def has_food(ctx: TickContext, target: EntityRow) -> bool:
    return await food_of(ctx, target) > 0


async def has_guard(ctx: TickContext, target: EntityRow) -> bool:
    profile = await ctx.session.get(SettlementProfileRow, target.id)
    return profile is not None and (profile.militia > 0 or profile.garrison_entity_id is not None)


async def has_rites(ctx: TickContext, target: EntityRow) -> bool:
    found = await ctx.session.scalar(
        select(BondRow.id).where(BondRow.source_node_id == target.id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE).limit(1)
    )
    return found is not None


async def has_sources(ctx: TickContext, target: EntityRow) -> bool:
    return bool(await sources_at(ctx, target))


async def has_machines(ctx: TickContext, target: EntityRow) -> bool:
    return await holders_know(ctx.session, [target.id, *([target.affiliated_entity_id] if target.affiliated_entity_id else [])], Technique.MACHINE_TOOLS)


WIDER_SABOTAGE: Mapping[SabotageKind, tuple[Strike, Fits]] = {
    SabotageKind.NETWORK_ATTACK: (attack_network, has_networks),
    SabotageKind.BRIDGE_DESTRUCTION: (break_bridges, has_crossings),
    SabotageKind.BLIGHT_RELEASE: (release_blight, has_food),
    SabotageKind.SUPPLY_THEFT: (steal_supplies, has_food),
    SabotageKind.MUTINY_INCITEMENT: (incite_mutiny, has_guard),
    SabotageKind.RITE_DISRUPTION: (disrupt_rites, has_rites),
    SabotageKind.SOURCE_POISONING: (poison_sources, has_sources),
    SabotageKind.MACHINE_SEIZURE: (seize_machines, has_machines),
    SabotageKind.RECORD_TAMPERING: (tamper_records, has_records),
    SabotageKind.ROUTE_BLOCKING: (block_routes, has_routes),
}


async def wider_choices(ctx: TickContext, target: EntityRow) -> list[SabotageKind]:
    return [kind for kind, (_, fits) in WIDER_SABOTAGE.items() if await fits(ctx, target)]
