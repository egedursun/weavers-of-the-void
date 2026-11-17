from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.customs import CommuteRow, CooperativeRow, TavernRow, WelfareRow
from aerona.db.tables.economy import CommunityStockRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.settlement import DistrictRow, SettlementInfrastructureRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.customs import CoopPurpose
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import PressureKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import StepAction
from aerona.domain.enums.structure import StructureKind
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.customs.relief import RELIEVING
from aerona.engine.economy.purse import give_coin, take_coin
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.mind.book import pressures_of
from aerona.engine.mortal.standing import add_renown
from aerona.engine.primitives.folk import present_in
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import shift_stat, stat_or
from aerona.engine.recording.record import StepDraft, record

TAVERN_KINDS = frozenset({StructureKind.TAVERN, StructureKind.INN})
WELFARE_KINDS = frozenset({StructureKind.ALMSHOUSE, StructureKind.ORPHANAGE, StructureKind.HOSPITAL})
WORKING = frozenset({CoopPurpose.MILL, CoopPurpose.BOATS, CoopPurpose.IRRIGATION})
THOUSAND = 1000


@dataclass
class TownLifeTally:
    taverns: int = 0
    brawls: int = 0
    houses: int = 0
    commutes: int = 0
    cooperatives: int = 0


async def structures(ctx: TickContext, kinds: frozenset[StructureKind]) -> list[tuple[StructureProfileRow, EntityRow]]:
    rows = await ctx.session.execute(
        select(StructureProfileRow, EntityRow)
        .join(EntityRow, EntityRow.id == StructureProfileRow.host_entity_id)
        .where(StructureProfileRow.kind.in_(list(kinds)), EntityRow.status == EntityStatus.CANON, EntityRow.entity_type == EntityType.SETTLEMENT)
        .order_by(StructureProfileRow.structure_entity_id)
    )
    return [(profile, town) for profile, town in rows.all()]


async def townsfolk(ctx: TickContext, town: EntityRow) -> list[EntityRow]:
    here = await present_in(ctx.session, town)
    return list(
        await ctx.session.scalars(
            select(EntityRow).where(here, EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    )


async def keep_taverns(ctx: TickContext, tally: TownLifeTally) -> None:
    table = ctx.rules.taverns
    for profile, town in await structures(ctx, TAVERN_KINDS):
        if held(profile.structure_entity_id) or held(town.id):
            continue
        row = await ctx.session.get(TavernRow, profile.structure_entity_id)
        if row is None:
            row = TavernRow(structure_entity_id=profile.structure_entity_id, locked=[])
            ctx.session.add(row)
        folk = await townsfolk(ctx, town)
        if row.keeper_node_id is None and folk and "keeper_node_id" not in row.locked:
            row.keeper_node_id = folk[0].id
        if "patrons" not in row.locked:
            row.patrons = round_half_up(stat_or(town, "population", 0) * table.patrons_pct / PERCENT)
        if profile.kind is StructureKind.INN and "lodging" not in row.locked:
            row.lodging = table.lodging_per_inn
            shift_stat(town, "prosperity", row.lodging / THOUSAND, low=0, high=PERCENT)
        rng = ctx.rng(seed_of("tavern", profile.structure_entity_id, ctx.epoch))
        if folk and rng.chance(table.brawl_chance):
            hurt = rng.pick(folk)
            if not held(hurt.id):
                await apply_hits(
                    ctx, hurt, Harm(damage=ctx.rules.intoxication.brawl_damage, cause=HarmCause.ACCIDENT, death_cause="died of a tavern brawl"), lethal=False
                )
                if "brawls" not in row.locked:
                    row.brawls += 1
                tally.brawls += 1
        keeper = await ctx.session.get(EntityRow, row.keeper_node_id) if row.keeper_node_id is not None else None
        if keeper is not None and keeper.status is EntityStatus.CANON and not held(keeper.id) and row.rumours:
            await add_renown(ctx.session, keeper.id, min(row.rumours, table.keeper_renown), ctx.epoch, rules=ctx.rules)
        tally.taverns += 1


async def keep_welfare(ctx: TickContext, tally: TownLifeTally) -> None:
    table = ctx.rules.welfare
    for profile, town in await structures(ctx, WELFARE_KINDS):
        if held(profile.structure_entity_id) or held(town.id):
            continue
        row = await ctx.session.get(WelfareRow, profile.structure_entity_id)
        if row is None:
            row = WelfareRow(structure_entity_id=profile.structure_entity_id, patron_node_id=profile.builder_entity_id, locked=[])
            ctx.session.add(row)
        poverty = (await pressures_of(ctx.session, town.id)).get(PressureKind.POVERTY, 0)
        if "inmates" not in row.locked:
            row.inmates = round_half_up(table.inmates_per_house * poverty / PERCENT)
        if "upkeep" not in row.locked:
            row.upkeep = round_half_up(row.inmates * table.upkeep_per_inmate / PERCENT)
        patron = await ctx.session.get(EntityRow, row.patron_node_id) if row.patron_node_id is not None else None
        living = patron is not None and patron.status is EntityStatus.CANON and not held(patron.id)
        payer = patron if living and patron is not None else town
        if not await take_coin(ctx.session, ctx.rules, payer, row.upkeep) and "inmates" not in row.locked:
            row.inmates = 0
        if living and patron is not None and patron.entity_type is EntityType.MORTAL and row.inmates:
            await add_renown(ctx.session, patron.id, table.patron_renown, ctx.epoch, rules=ctx.rules)
        tally.houses += 1


async def keep_commutes(ctx: TickContext, tally: TownLifeTally) -> None:
    table = ctx.rules.commuting
    counts = dict((await ctx.session.execute(select(DistrictRow.settlement_entity_id, func.count()).group_by(DistrictRow.settlement_entity_id))).all())
    for town in list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    ):
        districts = int(counts.get(town.id, 0))
        if districts <= 1 or held(town.id):
            continue
        works = await ctx.session.get(SettlementInfrastructureRow, town.id)
        relief = (works.roads + works.bridges) * table.road_relief if works is not None else 0
        row = await ctx.session.get(CommuteRow, town.id)
        if row is None:
            row = CommuteRow(settlement_entity_id=town.id, locked=[])
            ctx.session.add(row)
        if "distance" not in row.locked:
            row.distance = clamp_int((districts - 1) * table.district_distance - relief, 0, PERCENT)
        if "worker_camp" not in row.locked:
            row.worker_camp = row.distance >= table.camp_from
        if "labour_lost" not in row.locked:
            lost = row.distance * table.lost_per_distance_pct / PERCENT
            row.labour_lost = clamp_int(round_half_up(lost / 2 if row.worker_camp else lost), 0, PERCENT)
        row.updated_epoch = ctx.epoch
        tally.commutes += 1


async def purpose_for(ctx: TickContext, town: EntityRow) -> CoopPurpose:
    stocks = dict(
        (
            await ctx.session.execute(select(CommunityStockRow.commodity, CommunityStockRow.quantity).where(CommunityStockRow.community_entity_id == town.id))
        ).all()
    )
    if stocks.get(CommodityKind.FISH, 0):
        return CoopPurpose.BOATS
    if stocks.get(CommodityKind.GRAIN, 0):
        return CoopPurpose.MILL
    return ctx.rng(seed_of("cooperative", town.id)).pick([CoopPurpose.INSURANCE, CoopPurpose.BURIAL, CoopPurpose.CREDIT, CoopPurpose.IRRIGATION])


async def members_of(ctx: TickContext, faction: EntityRow) -> list[EntityRow]:
    found: list[EntityRow] = []
    for member_id in await ctx.session.scalars(
        select(BondRow.source_node_id)
        .where(BondRow.target_node_id == faction.id, BondRow.kind == BondKind.MEMBER_OF, BondRow.state == BondState.ACTIVE)
        .order_by(BondRow.source_node_id)
    ):
        member = await ctx.session.get(EntityRow, member_id)
        if member is not None and member.status is EntityStatus.CANON and not held(member.id):
            found.append(member)
    return found


async def collect_dues(ctx: TickContext, members: list[EntityRow], dues: int) -> int:
    paid = 0
    for member in members:
        if await take_coin(ctx.session, ctx.rules, member, dues):
            paid += dues
    return paid


async def pay_out(ctx: TickContext, members: list[EntityRow], pool: int, each: int) -> int:
    spent = 0
    for member in members:
        if pool - spent < each or each <= 0:
            break
        await give_coin(ctx.session, ctx.rules, member, each)
        spent += each
    return spent


async def keep_cooperatives(ctx: TickContext, tally: TownLifeTally) -> None:
    table = ctx.rules.cooperatives
    pooled = set(await ctx.session.scalars(select(CooperativeRow.faction_entity_id)))
    for town in list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    ):
        if held(town.id):
            continue
        factions = list(
            await ctx.session.scalars(
                select(EntityRow)
                .where(EntityRow.entity_type == EntityType.FACTION, EntityRow.status == EntityStatus.CANON, EntityRow.location_id == town.id)
                .order_by(EntityRow.id)
            )
        )
        poverty = (await pressures_of(ctx.session, town.id)).get(PressureKind.POVERTY, 0)
        if poverty >= table.found_from and factions and not any(item.id in pooled for item in factions) and not held(factions[0].id):
            purpose = await purpose_for(ctx, town)
            ctx.session.add(CooperativeRow(faction_entity_id=factions[0].id, purpose=purpose, locked=[]))
            pooled.add(factions[0].id)
            await record(
                ctx,
                "cooperatives.founded",
                roles={IncidentRole.PRODUCT: factions[0].id, IncidentRole.PLACE: town.id},
                facts={"purpose": purpose, "poverty": poverty},
                steps=(StepDraft(StepAction.FOUND, target=factions[0].id),),
                place=town.id,
            )
    await ctx.session.flush()
    for row in list(await ctx.session.scalars(select(CooperativeRow).order_by(CooperativeRow.faction_entity_id))):
        faction = await ctx.session.get(EntityRow, row.faction_entity_id)
        if faction is None or held(faction.id):
            continue
        members = int(
            await ctx.session.scalar(
                select(func.count())
                .select_from(BondRow)
                .where(BondRow.target_node_id == faction.id, BondRow.kind == BondKind.MEMBER_OF, BondRow.state == BondState.ACTIVE)
            )
            or 0
        )
        if "members" not in row.locked:
            row.members = members
        if "pool" not in row.locked:
            paying = await members_of(ctx, faction)
            if row.purpose in RELIEVING:
                row.pool -= await pay_out(ctx, paying, row.pool, table.payout)
            row.pool += await collect_dues(ctx, paying, table.dues)
        home = await ctx.session.get(EntityRow, faction.location_id) if faction.location_id is not None else None
        if home is not None and row.purpose in WORKING and row.members > 0 and not held(home.id):
            shift_stat(home, "prosperity", table.relief / 10, low=0, high=PERCENT)
        tally.cooperatives += 1


async def keep_town_life(ctx: TickContext, tally: TownLifeTally) -> None:
    await keep_taverns(ctx, tally)
    await keep_welfare(ctx, tally)
    await keep_commutes(ctx, tally)
    await keep_cooperatives(ctx, tally)
    await ctx.session.flush()
