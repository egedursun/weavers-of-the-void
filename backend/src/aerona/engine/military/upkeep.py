from sqlalchemy import func, select

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.military import ArmyProfileRow, MercenaryContractRow, OccupationRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.warfare import ArmyRow, WarRow, WarSideRow
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.entity import EngineKind, EntityStatus, EntityType
from aerona.domain.enums.military import ContractStatus, Stance
from aerona.domain.enums.war import WarCause, WarStatus
from aerona.engine.context import TickContext
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.military.campaign import bring_home_loot, drill, heal_plunder
from aerona.engine.military.finance import mercenary_pay
from aerona.engine.military.units import profile_of, resize, stacks_of
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.levies import levies_from, levy
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import stat
from aerona.engine.primitives.strength import MilitaryStrength
from aerona.engine.services.sides import SideIndex
from aerona.engine.services.war import declare_war, ongoing_wars, raise_army, soldier_count
from aerona.engine.services.war_geography import Neighbourhood

COMPANY_KINDS = frozenset({EngineKind.WARRIOR_BAND})


async def heal_lands(ctx: TickContext) -> int:
    regions = list(await ctx.session.scalars(select(RegionEnvironmentRow)))
    return heal_plunder(ctx.rules, regions)


async def drill_armies(ctx: TickContext) -> int:
    drilled = 0
    for row in list(await ctx.session.scalars(select(ArmyRow).where(ArmyRow.disbanded_epoch.is_(None)).order_by(ArmyRow.entity_id))):
        army = await living_entity(ctx.session, row.entity_id)
        owner = await living_entity(ctx.session, row.owner_entity_id)
        if army is None or owner is None:
            continue
        profile = await profile_of(ctx, army, owner)
        if row.war_id is not None and profile.stance is not Stance.GARRISON:
            continue
        if await drill(ctx, owner, profile, await stacks_of(ctx.session, army.id)):
            drilled += 1
        if row.war_id is None:
            await bring_home_loot(ctx, owner, profile)
    return drilled


async def hire_mercenaries(ctx: TickContext) -> int:
    hired = 0
    table = ctx.rules.war_finance
    taken: set[int] = set(
        await ctx.session.scalars(
            select(MercenaryContractRow.company_entity_id).where(MercenaryContractRow.status.in_([ContractStatus.ACTIVE, ContractStatus.UNPAID]))
        )
    )
    companies = [
        company
        for company in await ctx.session.scalars(
            select(EntityRow).where(
                EntityRow.entity_type == EntityType.FACTION, EntityRow.status == EntityStatus.CANON, EntityRow.engine_kind.in_(COMPANY_KINDS)
            )
        )
        if company.id not in taken
    ]
    if not companies:
        return 0
    neighbourhood = await Neighbourhood.load(ctx.session, ctx.rules)
    strength = await MilitaryStrength.load(ctx.session, ctx.rules)
    sides = await SideIndex.load(ctx.session, neighbourhood)
    for item in await ongoing_wars(ctx.session):
        for side_id, enemy_id in ((item.attacker_id, item.defender_id), (item.defender_id, item.attacker_id)):
            employer = await living_entity(ctx.session, side_id)
            company = next((found for found in companies if employer is not None and found.world_id == employer.world_id), None)
            if employer is None or company is None or not await outnumbered(ctx, item.war, side_id, enemy_id):
                continue
            soldiers = await company_size(ctx, strength, company)
            pay = mercenary_pay(table.mercenary_pay_per_100, soldiers)
            if (stat(employer, "wealth") or 0) < pay * 2:
                continue
            await hire(ctx, strength, sides, employer=employer, company=company, war=item.war, pay=pay)
            companies.remove(company)
            hired += 1
    return hired


async def company_size(ctx: TickContext, strength: MilitaryStrength, company: EntityRow) -> int:
    return soldier_count(ctx.rules, strength, company)


async def outnumbered(ctx: TickContext, war: WarRow, side_id: int, enemy_id: int) -> bool:
    mine = await side_soldiers(ctx, war, side_id)
    theirs = await side_soldiers(ctx, war, enemy_id)
    return theirs * 2 > mine * 3


async def side_soldiers(ctx: TickContext, war: WarRow, side_id: int) -> int:
    total = 0
    for row in await ctx.session.scalars(
        select(ArmyRow).where(ArmyRow.war_id == war.id, ArmyRow.owner_entity_id == side_id, ArmyRow.disbanded_epoch.is_(None))
    ):
        army = await living_entity(ctx.session, row.entity_id)
        total += (stat(army, "size") or 0) if army is not None else 0
    return total


async def hire(
    ctx: TickContext, strength: MilitaryStrength, sides: SideIndex, *, employer: EntityRow, company: EntityRow, war: WarRow, pay: int
) -> MercenaryContractRow:
    army, row = await raise_army(ctx, strength, sides, company, war)
    row.owner_entity_id = employer.id
    contract = MercenaryContractRow(
        employer_entity_id=employer.id,
        company_entity_id=company.id,
        army_entity_id=army.id,
        war_id=war.id,
        soldiers=stat(army, "size") or 0,
        pay_per_season=pay,
        seasons_left=ctx.rules.war_finance.mercenary_seasons,
        loyalty=PERCENT * 3 // 5,
        unpaid_seasons=0,
        status=ContractStatus.ACTIVE,
        since_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(contract)
    await ctx.session.flush()
    await ctx.chronicle(
        ChronicleKind.WAR,
        f"{employer.name} hired {company.name} by contract; {army.name} now marches for pay.",
        template_key="war.mercenaries_hired",
        entity_ids=(employer.id, company.id, army.id),
        feed_category=FeedCategory.WAR,
    )
    return contract


async def occupation_levies(ctx: TickContext, atlas: RegionAtlas) -> int:
    table = ctx.rules.levies
    raised = 0
    for occupation in list(await ctx.session.scalars(select(OccupationRow).order_by(OccupationRow.region_entity_id))):
        army_row = await ctx.session.scalar(
            select(ArmyRow)
            .join(ArmyProfileRow, ArmyProfileRow.army_entity_id == ArmyRow.entity_id)
            .where(ArmyRow.owner_entity_id == occupation.occupier_entity_id, ArmyRow.disbanded_epoch.is_(None))
            .where(ArmyProfileRow.region_entity_id == occupation.region_entity_id)
            .limit(1)
        )
        army = await living_entity(ctx.session, army_row.entity_id) if army_row is not None else None
        if army is None:
            continue
        for community_id in atlas.communities_in(occupation.region_entity_id):
            community = await living_entity(ctx.session, community_id)
            if community is None or not levies_from(community) or community.id == occupation.occupier_entity_id:
                continue
            wanted = round_half_up((stat(community, "population") or 0) * table.occupation_levy_pct / PERCENT * occupation.control / PERCENT)
            if wanted <= 0:
                continue
            taken = levy(ctx.rules, community, wanted)
            with flowing(FlowCategory.LEVY):
                await resize(ctx.session, ctx.rules, army, (stat(army, "size") or 0) + taken)
            raised += taken
    return raised


async def occupation_revolts(ctx: TickContext, atlas: RegionAtlas) -> int:
    table = ctx.rules.occupation
    revolts = 0
    for occupation in list(await ctx.session.scalars(select(OccupationRow).order_by(OccupationRow.region_entity_id))):
        if occupation.resistance < table.revolt_resistance:
            continue
        if not ctx.rng(f"occupation_revolt.{occupation.region_entity_id}.{ctx.epoch}").chance(table.revolt_chance):
            continue
        for community_id in atlas.communities_in(occupation.region_entity_id):
            if community_id == occupation.occupier_entity_id:
                continue
            reason = "rose against the occupier"
            if await declare_war(ctx, community_id, occupation.occupier_entity_id, reason, cause=WarCause.LIBERATION, world_cap=False):
                occupation.control = clamp_int(occupation.control - table.control_gain, 0, PERCENT)
                revolts += 1
                break
    return revolts


async def war_taxes(ctx: TickContext, side: WarSideRow) -> int:
    town = await ctx.session.get(SettlementProfileRow, side.entity_id)
    rate = town.tax_rate if town is not None else 0
    return round_half_up(ctx.rules.war_finance.war_tax_weariness * rate / max(1, PERCENT // 10))


async def lost_trade(ctx: TickContext, side: WarSideRow) -> int:
    blockades = await ctx.session.scalar(select(func.count()).select_from(ArmyProfileRow).where(ArmyProfileRow.blockade_entity_id == side.entity_id))
    return int(blockades or 0) * ctx.rules.war_finance.lost_trade_weariness


async def open_wars(ctx: TickContext) -> list[WarRow]:
    return list(await ctx.session.scalars(select(WarRow).where(WarRow.status == WarStatus.ONGOING)))
