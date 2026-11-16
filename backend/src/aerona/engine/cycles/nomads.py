from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.grammar import several
from aerona.db.tables.cycles import CampRow, ConfederationRow
from aerona.db.tables.demography import LabourRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.cycles import MobilityMode
from aerona.domain.enums.demography import Job
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.nature import PlantDefence
from aerona.domain.enums.settlement import SizeTier
from aerona.engine.body.customs import people_of
from aerona.engine.collective.book import population_of, shift
from aerona.engine.context import TickContext
from aerona.engine.cycles.asabiyya import asabiyya_row
from aerona.engine.economy.purse import coin_of, receive_coin, take_coin
from aerona.engine.nature.cover import cover_of, grazing
from aerona.engine.notes import note
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import present_in
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import stat_or
from aerona.engine.services.community_relations import change_relation
from aerona.engine.services.war import active_tribute, impose_tribute

SMALL = frozenset({SizeTier.HAMLET, SizeTier.VILLAGE})
MOVING = frozenset({MobilityMode.NOMADIC, MobilityMode.TRANSHUMANT})
TRANSHUMANT_STOPS = 2


@dataclass
class NomadTally:
    camps: int = 0
    moved: int = 0
    settled: int = 0
    tributes: int = 0
    raids: int = 0
    trades: int = 0
    rerouted: int = 0
    confederations: int = 0
    fragmented: int = 0


async def herding_share(ctx: TickContext, town_id: int) -> int:
    rows = list(await ctx.session.scalars(select(LabourRow).where(LabourRow.community_entity_id == town_id)))
    total = sum(row.workers for row in rows)
    herders = sum(row.workers for row in rows if row.job is Job.HERDING)
    return round_half_up(herders * PERCENT / total) if total else 0


async def pasture(ctx: TickContext, region: RegionEnvironmentRow | None) -> int:
    if region is None:
        return 0
    spoiled = grazing(ctx.rules, await cover_of(ctx.session, region.entity_id, PlantDefence.THORNS))
    return clamp_int(((region.moisture + region.soil_fertility) / 2 - region.grazed / 2) * spoiled, 0, PERCENT)


def water_of(region: RegionEnvironmentRow | None) -> int:
    if region is None:
        return 0
    return clamp_int((region.moisture + region.rainfall) / 2, 0, PERCENT)


async def circuit_for(ctx: TickContext, atlas: RegionAtlas, region_id: int, mode: MobilityMode, herd: int = 0) -> list[int]:
    table = ctx.rules.nomadism
    length = table.circuit_stops + min(table.circuit_stops, herd // max(1, table.herd_scale)) if mode is MobilityMode.NOMADIC else TRANSHUMANT_STOPS
    scored = []
    for near in atlas.neighbours(region_id):
        land = await ctx.session.get(RegionEnvironmentRow, near)
        scored.append((await pasture(ctx, land) + water_of(land), near))
    best = [near for _, near in sorted(scored, key=lambda item: (-item[0], item[1]))]
    return [region_id, *best[: max(0, length - 1)]]


async def found_camps(ctx: TickContext, atlas: RegionAtlas, tally: NomadTally) -> None:
    table = ctx.rules.nomadism
    towns = await ctx.session.execute(
        select(EntityRow, SettlementProfileRow)
        .join(SettlementProfileRow, SettlementProfileRow.settlement_entity_id == EntityRow.id)
        .where(EntityRow.status == EntityStatus.CANON, SettlementProfileRow.size_tier.in_(list(SMALL)))
        .order_by(EntityRow.id)
    )
    for town, _ in towns.all():
        if held(town.id) or await ctx.session.get(CampRow, town.id) is not None:
            continue
        share = await herding_share(ctx, town.id)
        region = atlas.top_region(town.id)
        if share < table.pastoral_pct or region is None:
            continue
        mode = MobilityMode.NOMADIC if share >= table.nomadic_pct else MobilityMode.TRANSHUMANT
        ground = await ctx.session.get(RegionEnvironmentRow, region)
        ctx.session.add(
            CampRow(
                settlement_entity_id=town.id,
                mode=mode,
                circuit=await circuit_for(ctx, atlas, region, mode, round_half_up(population_of(town) * table.herd_per_dweller / PERCENT)),
                season_index=0,
                herd=round_half_up(population_of(town) * table.herd_per_dweller / PERCENT),
                grazing=await pasture(ctx, ground),
                water=water_of(ground),
                last_moved_epoch=None,
                locked=[],
            )
        )
        tally.camps += 1
        await note(ctx, f"{town.name} took to the move with its herds, following the pastures.", key="nomads.camp", ids=[town.id])


async def graze(ctx: TickContext, camp: CampRow, region: RegionEnvironmentRow | None) -> None:
    table = ctx.rules.nomadism
    if "grazing" not in camp.locked:
        camp.grazing = await pasture(ctx, region)
    if "water" not in camp.locked:
        camp.water = water_of(region)
    if "herd" not in camp.locked:
        growth = table.herd_growth_pct * (camp.grazing + camp.water) / (2 * PERCENT) - table.herd_loss_pct
        camp.herd = clamp_int(camp.herd * (1 + growth / PERCENT), 0, 10**9)
    if region is not None and not held(region.entity_id):
        shift(region, "grazed", camp.herd * table.graze_pressure / max(1, table.herd_scale))


async def reroute(ctx: TickContext, atlas: RegionAtlas, town: EntityRow, camp: CampRow, tally: NomadTally) -> None:
    if camp.grazing >= ctx.rules.nomadism.reroute_at or "circuit" in camp.locked or not camp.circuit:
        return
    here = camp.circuit[camp.season_index % len(camp.circuit)]
    fresh = await circuit_for(ctx, atlas, here, camp.mode, camp.herd)
    if fresh == camp.circuit:
        return
    camp.circuit = fresh
    camp.season_index = 0
    tally.rerouted += 1
    await note(
        ctx,
        f"With its pastures grazed bare, {town.name} set out on a new round of {several(len(fresh), 'pasture', 'pastures')}.",
        key="nomads.rerouted",
        ids=[town.id],
    )


async def move(ctx: TickContext, town: EntityRow, camp: CampRow, tally: NomadTally) -> None:
    if not camp.circuit or "season_index" in camp.locked:
        return
    camp.season_index = (camp.season_index + 1) % len(camp.circuit)
    target = camp.circuit[camp.season_index]
    if await ctx.session.get(EntityRow, target) is None or town.location_id == target:
        return
    town.location_id = target
    camp.last_moved_epoch = ctx.epoch
    tally.moved += 1


async def settle_or_roam(ctx: TickContext, town: EntityRow, camp: CampRow, tally: NomadTally) -> None:
    table = ctx.rules.nomadism
    if "mode" in camp.locked:
        return
    share = await herding_share(ctx, town.id)
    if camp.mode in MOVING and share < table.settle_pct:
        camp.mode = MobilityMode.SEDENTARY
        tally.settled += 1
        await note(ctx, f"{town.name} put down roots and wandered no more.", key="nomads.settled", ids=[town.id])
    elif camp.mode is MobilityMode.SEDENTARY and share >= table.pastoral_pct:
        camp.mode = MobilityMode.NOMADIC if share >= table.nomadic_pct else MobilityMode.TRANSHUMANT


def riders(ctx: TickContext, town: EntityRow, camp: CampRow) -> int:
    table = ctx.rules.nomadism
    return round_half_up(population_of(town) * table.rider_pct / PERCENT + camp.herd * table.rider_per_herd / PERCENT)


async def sedentary_near(ctx: TickContext, atlas: RegionAtlas, town: EntityRow) -> list[tuple[EntityRow, SettlementProfileRow]]:
    region = atlas.top_region(town.id)
    if region is None:
        return []
    near = {region, *atlas.neighbours(region)}
    rows = await ctx.session.execute(
        select(EntityRow, SettlementProfileRow)
        .join(SettlementProfileRow, SettlementProfileRow.settlement_entity_id == EntityRow.id)
        .where(EntityRow.status == EntityStatus.CANON, EntityRow.id != town.id)
        .order_by(EntityRow.id)
    )
    found = []
    for other, profile in rows.all():
        camp = await ctx.session.get(CampRow, other.id)
        if (camp is None or camp.mode is MobilityMode.SEDENTARY) and atlas.top_region(other.id) in near:
            found.append((other, profile))
    return found


async def confederates(ctx: TickContext) -> dict[int, ConfederationRow]:
    found: dict[int, ConfederationRow] = {}
    for row in await ctx.session.scalars(select(ConfederationRow).where(ConfederationRow.dissolved_epoch.is_(None)).order_by(ConfederationRow.id)):
        for member in row.members:
            found[member] = row
    return found


async def strength_of(ctx: TickContext, town: EntityRow, camp: CampRow, league: ConfederationRow | None) -> int:
    if league is None:
        return riders(ctx, town, camp)
    total = 0
    for member_id in league.members:
        member = await living_entity(ctx.session, member_id)
        member_camp = await ctx.session.get(CampRow, member_id)
        if member is not None and member_camp is not None:
            total += riders(ctx, member, member_camp)
    return total


async def press(ctx: TickContext, atlas: RegionAtlas, town: EntityRow, camp: CampRow, *, league: ConfederationRow | None, tally: NomadTally) -> None:
    table = ctx.rules.nomadism
    might = await strength_of(ctx, town, camp, league)
    for other, profile in await sedentary_near(ctx, atlas, town):
        if held(other.id) or (league is not None and other.id in league.members):
            continue
        guard = profile.militia + 1
        if might >= guard * table.tribute_ratio and await active_tribute(ctx.session, other.id, town.id) is None:
            await impose_tribute(ctx, other, town, None, "tribute to the herders of the pastures")
            tally.tributes += 1
            await note(ctx, f"{other.name} bowed to the herders of {town.name} and paid them tribute.", key="nomads.tribute", ids=[other.id, town.id])
            continue
        if might >= guard and ctx.rng(f"nomads.raid.{town.id}.{other.id}.{ctx.epoch}").chance(table.raid_pct):
            taken = min(await coin_of(ctx.session, ctx.rules, other), round_half_up(might * table.raid_take / PERCENT))
            if taken > 0 and await take_coin(ctx.session, ctx.rules, other, taken):
                await receive_coin(ctx.session, ctx.rules, town, taken)
            await change_relation(ctx, other.id, town.id, -table.raid_relation, MemoryKind.HARMED_ME, note="raided by herders")
            tally.raids += 1
            await note(ctx, f"Riders of {town.name} raided {other.name} and rode off with {taken} in plunder.", key="nomads.raid", ids=[town.id, other.id])
            continue
        if ctx.rng(f"nomads.trade.{town.id}.{other.id}.{ctx.epoch}").chance(table.trade_pct):
            await trade(ctx, town, camp, other, tally)


async def trade(ctx: TickContext, town: EntityRow, camp: CampRow, other: EntityRow, tally: NomadTally) -> None:
    table = ctx.rules.nomadism
    worth = min(await coin_of(ctx.session, ctx.rules, other), round_half_up(camp.herd * table.trade_per_herd / PERCENT))
    if worth <= 0 or not await take_coin(ctx.session, ctx.rules, other, worth):
        return
    await receive_coin(ctx.session, ctx.rules, town, worth)
    await change_relation(ctx, other.id, town.id, table.trade_regard, MemoryKind.TRADED_WITH, note="trade with the herders")
    tally.trades += 1
    await note(ctx, f"The camp of {town.name} traded the yield of its herds with {other.name} for {worth}.", key="nomads.trade", ids=[town.id, other.id])


async def charismatic(ctx: TickContext, town: EntityRow) -> EntityRow | None:
    return await ctx.session.scalar(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, await present_in(ctx.session, town))
        .order_by(EntityRow.importance.desc(), EntityRow.id)
        .limit(1)
    )


async def confederate(
    ctx: TickContext, atlas: RegionAtlas, camps: list[tuple[EntityRow, CampRow]], leagues: dict[int, ConfederationRow], tally: NomadTally
) -> None:
    table = ctx.rules.nomadism
    for town, _ in camps:
        if town.id in leagues or held(town.id):
            continue
        leader = await charismatic(ctx, town)
        if leader is None or stat_or(leader, "charisma", 0) < table.leader_charisma:
            continue
        region = atlas.top_region(town.id)
        near = {region, *atlas.neighbours(region)} if region is not None else set()
        joined = [other.id for other, other_camp in camps if other.id not in leagues and other_camp.mode in MOVING and atlas.top_region(other.id) in near]
        if len(joined) < table.confederation_min:
            continue
        row = ConfederationRow(
            name=f"The confederation of {leader.name}", leader_entity_id=leader.id, members=sorted(joined), formed_epoch=ctx.epoch, locked=[]
        )
        ctx.session.add(row)
        for member in joined:
            leagues[member] = row
        tally.confederations += 1
        await note(
            ctx,
            f"{leader.name} gathered {several(len(joined), 'wandering camp', 'wandering camps')} under one rule.",
            key="nomads.confederation",
            ids=[leader.id, *joined],
        )


async def fragment(ctx: TickContext, tally: NomadTally) -> None:
    for row in await ctx.session.scalars(select(ConfederationRow).where(ConfederationRow.dissolved_epoch.is_(None)).order_by(ConfederationRow.id)):
        if "dissolved_epoch" in row.locked or any(held(member) for member in row.members):
            continue
        leader = await living_entity(ctx.session, row.leader_entity_id) if row.leader_entity_id is not None else None
        if leader is not None:
            continue
        row.dissolved_epoch = ctx.epoch
        tally.fragmented += 1
        await note(ctx, f"With its leader gone, {row.name} broke apart into its camps.", key="nomads.fragmented", ids=list(row.members))


async def keep_nomads(ctx: TickContext, tally: NomadTally) -> None:
    table = ctx.rules.nomadism
    atlas = await RegionAtlas.load(ctx.session)
    await found_camps(ctx, atlas, tally)
    await fragment(ctx, tally)
    rows = await ctx.session.execute(
        select(EntityRow, CampRow)
        .join(CampRow, CampRow.settlement_entity_id == EntityRow.id)
        .where(EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    camps = [(town, camp) for town, camp in rows.all() if not held(town.id)]
    leagues = await confederates(ctx)
    await confederate(ctx, atlas, camps, leagues, tally)
    for town, camp in camps:
        await settle_or_roam(ctx, town, camp, tally)
        if camp.mode not in MOVING:
            continue
        await reroute(ctx, atlas, town, camp, tally)
        await move(ctx, town, camp, tally)
        region = camp.circuit[camp.season_index % len(camp.circuit)] if camp.circuit else atlas.top_region(town.id)
        await graze(ctx, camp, await ctx.session.get(RegionEnvironmentRow, region) if region is not None else None)
        await press(ctx, atlas, town, camp, league=leagues.get(town.id), tally=tally)
        people = await people_of(ctx.session, town)
        if people is not None and not held(people.id):
            shift(await asabiyya_row(ctx, people.id), "value", table.steppe_asabiyya)
    await ctx.session.flush()
