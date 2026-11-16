from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.military import ArmyProfileRow, CaptiveCohortRow, CommanderTraitRow
from aerona.db.tables.settlement import DistrictRow, SettlementInfrastructureRow, SettlementProfileRow
from aerona.db.tables.warfare import ArmyRow, SiegeRow, WarRow, WarSideRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.couplings import FieldAgreementState
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.environment import SoilKind
from aerona.domain.enums.faith import TenetKind
from aerona.domain.enums.military import CaptiveFate, CommanderTrait, DefenderAction, SackChoice, SiegeAction, SiegeWork, Stance, StarvationStage
from aerona.domain.enums.mind import MemoryKind, ValueAxis
from aerona.domain.enums.settlement import BuildMaterial, WaterSupply
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.war import SiegeStatus
from aerona.engine.body.cohorts import return_maimed
from aerona.engine.context import TickContext
from aerona.engine.couplings.field import break_terms, under_terms
from aerona.engine.economy.stocks import goods_of, holding
from aerona.engine.faith.book import faith_tenets
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.mind.book import values_for
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity, spoken_language
from aerona.engine.primitives.stats import shift_stat, stat
from aerona.engine.services.community_relations import change_relation

SOFT_GROUND = frozenset({SoilKind.LOAM, SoilKind.CLAY, SoilKind.SAND, SoilKind.PEAT, SoilKind.ASH, SoilKind.BONE})
WATER_DAYS = {WaterSupply.NONE: 60, WaterSupply.WELL: 100, WaterSupply.CISTERN: 160, WaterSupply.AQUEDUCT: 220}
ACTION_WORKS = {
    SiegeAction.BLOCKADE: (SiegeWork.CIRCUMVALLATION,),
    SiegeAction.BOMBARD: (SiegeWork.TOWERS, SiegeWork.RAMS),
    SiegeAction.MINE: (SiegeWork.MINES,),
    SiegeAction.ASSAULT: (SiegeWork.LADDERS, SiegeWork.RAMS),
    SiegeAction.NEGOTIATE: (),
}
MERCIFUL_TENETS = frozenset({TenetKind.PACIFISM})


def wall_material(walls: SettlementInfrastructureRow | None, siege: SiegeRow) -> BuildMaterial:
    if siege.wall_material:
        try:
            return BuildMaterial(siege.wall_material)
        except ValueError:
            pass
    return walls.walls_material if walls is not None else BuildMaterial.TIMBER


def bombard_factor(ctx: TickContext, material: BuildMaterial) -> float:
    table = ctx.rules.siege_depth
    return (table.timber_bombard_pct if material is BuildMaterial.TIMBER else table.stone_bombard_pct) / PERCENT


def repair_factor(ctx: TickContext, material: BuildMaterial) -> float:
    table = ctx.rules.siege_depth
    return (table.timber_repair_pct if material is BuildMaterial.TIMBER else table.stone_repair_pct) / PERCENT


def mining_factor(ctx: TickContext, region: RegionEnvironmentRow | None) -> float:
    table = ctx.rules.siege_depth
    if region is None:
        return 1.0
    return (table.soil_mine_pct if region.soil in SOFT_GROUND else table.rock_mine_pct) / PERCENT


def build_works(ctx: TickContext, siege: SiegeRow, action: SiegeAction) -> list[SiegeWork]:
    works = dict(siege.works)
    done: list[SiegeWork] = []
    for work in ACTION_WORKS.get(action, ()):
        before = int(works.get(work.value, 0))
        works[work.value] = min(PERCENT, before + ctx.rules.siege_depth.work_progress)
        if before < PERCENT <= works[work.value]:
            done.append(work)
    siege.works = works
    return done


def countermine(ctx: TickContext, siege: SiegeRow) -> bool:
    works = dict(siege.works)
    if int(works.get(SiegeWork.MINES.value, 0)) <= 0:
        return False
    works[SiegeWork.COUNTERMINES.value] = min(PERCENT, int(works.get(SiegeWork.COUNTERMINES.value, 0)) + ctx.rules.siege_depth.work_progress)
    if int(works[SiegeWork.COUNTERMINES.value]) >= PERCENT:
        works[SiegeWork.MINES.value] = 0
    siege.works = works
    return True


def finished_works(siege: SiegeRow) -> list[SiegeWork]:
    return [work for work in SiegeWork if work is not SiegeWork.COUNTERMINES and int(siege.works.get(work.value, 0)) >= PERCENT]


def works_breach(ctx: TickContext, siege: SiegeRow) -> float:
    return len(finished_works(siege)) * ctx.rules.siege_depth.work_breach_pct / PERCENT


def encircled(siege: SiegeRow) -> bool:
    return int(siege.works.get(SiegeWork.CIRCUMVALLATION.value, 0)) >= PERCENT


async def taboo_holds(ctx: TickContext, besieged: EntityRow) -> bool:
    values = await values_for(ctx.session, besieged.id)
    return values.get(ValueAxis.PURITY, 0) >= ctx.rules.siege_depth.taboo_value


async def siege_sickness(ctx: TickContext, siege: SiegeRow, besieged: EntityRow) -> int:
    table = ctx.rules.siege_depth
    town = await ctx.session.get(SettlementProfileRow, besieged.id)
    walls = await ctx.session.get(SettlementInfrastructureRow, besieged.id)
    sanitation = town.sanitation if town is not None else PERCENT // 5
    if walls is not None and walls.sewers:
        sanitation = min(PERCENT, sanitation + PERCENT // 4)
    clean = walls is not None and walls.water in {WaterSupply.CISTERN, WaterSupply.AQUEDUCT}
    gain = ctx.rules.siegecraft.camp_disease_gain * (1 - table.sanitation_disease_pct / PERCENT * sanitation / PERCENT) * (0.5 if clean else 1.0)
    siege.disease_inside = clamp_int(siege.disease_inside + round_half_up(gain), 0, PERCENT)
    if town is not None:
        town.siege_disease = siege.disease_inside
    return siege.disease_inside


async def hunger_betrayal(ctx: TickContext, siege: SiegeRow, besieged: EntityRow) -> bool:
    if siege.starvation not in {StarvationStage.FAMINE, StarvationStage.TABOO_BROKEN}:
        return False
    town = await ctx.session.get(SettlementProfileRow, besieged.id)
    unrest = town.unrest if town is not None else PERCENT // 2
    chance = ctx.rules.siege_depth.betrayal_hunger_pct * (PERCENT + unrest) / (2 * PERCENT)
    return ctx.rng(f"hunger_betrayal.{siege.id}.{siege.rounds}").chance(chance)


async def mason_repair(ctx: TickContext, siege: SiegeRow, besieged: EntityRow, walls: SettlementInfrastructureRow | None) -> int:
    if walls is None or "walls_condition" in (walls.locked or []):
        return 0
    table = ctx.rules.siege_depth
    stone = await holding(ctx.session, besieged.id, CommodityKind.STONE)
    if stone < table.stone_per_repair:
        return 0
    await goods_of(ctx.session, ctx.epoch).take_units(besieged.id, CommodityKind.STONE, table.stone_per_repair, GoodsFlow.SIEGE)
    gain = round_half_up(table.mason_repair_pct * repair_factor(ctx, wall_material(walls, siege)))
    walls.walls_condition = clamp_int(walls.walls_condition + gain, 0, PERCENT)
    return gain


async def relief_army(ctx: TickContext, siege: SiegeRow, besieged: EntityRow, atlas: RegionAtlas) -> EntityRow | None:
    region = atlas.top_region(besieged.id)
    war = await ctx.session.get(WarRow, siege.war_id)
    if region is None or war is None:
        return None
    side = await ctx.session.get(WarSideRow, (war.id, besieged.id))
    friends = [besieged.id]
    if side is not None:
        friends.extend(
            await ctx.session.scalars(
                select(WarSideRow.entity_id).where(WarSideRow.war_id == war.id, WarSideRow.side == side.side, WarSideRow.left_epoch.is_(None))
            )
        )
    rows = await ctx.session.scalars(select(ArmyRow).where(ArmyRow.owner_entity_id.in_(friends), ArmyRow.disbanded_epoch.is_(None)).order_by(ArmyRow.entity_id))
    for row in rows:
        profile = await ctx.session.get(ArmyProfileRow, row.entity_id)
        army = await living_entity(ctx.session, row.entity_id)
        if army is None or profile is None or profile.region_entity_id is None:
            continue
        hops = atlas.region_hops(profile.region_entity_id, region)
        if hops is not None and hops <= ctx.rules.siege_depth.relief_reach and profile.region_entity_id != region:
            if "target_id" not in profile.locked:
                profile.target_entity_id = region
            if "stance" not in profile.locked:
                profile.stance = Stance.MARCH
            return army
    return None


async def seek_relief(ctx: TickContext, siege: SiegeRow, besieged: EntityRow, atlas: RegionAtlas) -> EntityRow | None:
    army = await relief_army(ctx, siege, besieged, atlas)
    if army is None:
        return None
    if "relief_army_id" not in siege.locked:
        if siege.relief_army_id != army.id:
            hearten(ctx, besieged)
        siege.relief_army_id = army.id
    return army


def hearten(ctx: TickContext, besieged: EntityRow) -> None:
    key = next((key for key in ("morale", "stability") if stat(besieged, key) is not None), None)
    if key is not None:
        shift_stat(besieged, key, ctx.rules.siege_depth.relief_morale)


async def relief_arrived(ctx: TickContext, siege: SiegeRow, besieged: EntityRow, besiegers: EntityRow, atlas: RegionAtlas) -> bool:
    if siege.relief_army_id is None or encircled(siege):
        return False
    army = await living_entity(ctx.session, siege.relief_army_id)
    profile = await ctx.session.get(ArmyProfileRow, siege.relief_army_id)
    if army is None or profile is None or profile.region_entity_id != atlas.top_region(besieged.id):
        return False
    if (stat(army, "size") or 0) * 5 < (stat(besiegers, "size") or 0) * 3:
        return False
    siege.status, siege.ended_epoch = SiegeStatus.LIFTED, ctx.epoch
    await ctx.chronicle(
        ChronicleKind.WAR,
        f"{army.name} came to the relief of {besieged.name}; the besiegers broke camp and the siege was lifted.",
        template_key="war.siege.relieved",
        entity_ids=(army.id, besieged.id),
        feed_category=FeedCategory.WAR,
        place_entity_id=besieged.id,
    )
    return True


async def sack_choice(ctx: TickContext, siege: SiegeRow, victor: EntityRow, commander_id: int | None) -> SackChoice:
    if siege.choice is not None and "choice" in siege.locked:
        return siege.choice
    table = ctx.rules.siege_depth
    mercy = (await values_for(ctx.session, victor.id)).get(ValueAxis.MERCY, 0)
    traits = (
        set(await ctx.session.scalars(select(CommanderTraitRow.trait).where(CommanderTraitRow.mortal_entity_id == commander_id))) if commander_id else set()
    )
    tenets = await faith_tenets(ctx.session, victor.id)
    if CommanderTrait.BRUTAL in traits or mercy <= table.raze_value:
        choice = SackChoice.RAZE
    elif mercy >= table.mercy_value or tenets & MERCIFUL_TENETS or CommanderTrait.INSPIRING in traits:
        choice = SackChoice.MERCY
    else:
        choice = SackChoice.SACK
    terms = await under_terms(ctx, siege.war_id, siege.besieged_entity_id)
    if terms is not None and terms.state is FieldAgreementState.KEPT and choice is not SackChoice.MERCY:
        if CommanderTrait.BRUTAL in traits:
            await break_terms(ctx, terms, commander_id or victor.id)
        else:
            choice = SackChoice.MERCY
    siege.choice = choice
    return choice


async def plunder_relics(ctx: TickContext, besieged: EntityRow, victor: EntityRow) -> int:
    bonds = BondRepository(ctx.session)
    taken = 0
    items = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.ITEM, EntityRow.status == EntityStatus.CANON, EntityRow.location_id == besieged.id)
    )
    for item in list(items):
        if not ctx.rng(f"sack_relic.{item.id}.{ctx.epoch}").chance(ctx.rules.siege_depth.relic_chance):
            continue
        for bond in await bonds.incoming(item.id, BondKind.OWNS):
            await bonds.deactivate(bond, ctx.epoch, f"carried off in the sack of {besieged.name}")
        await bonds.connect(BondDraft(victor.id, item.id, BondKind.OWNS, ctx.epoch, f"loot of {besieged.name}"))
        item.location_id = victor.id if victor.entity_type is EntityType.SETTLEMENT else victor.location_id
        taken += 1
    return taken


async def burn_districts(ctx: TickContext, besieged: EntityRow, depth: int) -> int:
    burned = 0
    for district in await ctx.session.scalars(select(DistrictRow).where(DistrictRow.settlement_entity_id == besieged.id).order_by(DistrictRow.id)):
        if ctx.rng(f"burn_district.{district.id}.{ctx.epoch}").chance(PERCENT // 2):
            district.condition = clamp_int(district.condition - depth * (2 if district.material is BuildMaterial.TIMBER else 1), 0, PERCENT)
            burned += 1
    return burned


async def mass_captives(ctx: TickContext, besieged: EntityRow, victor: EntityRow, war_id: int, share_pct: int) -> int:
    population = stat(besieged, "population") or 0
    count = round_half_up(population * share_pct / PERCENT)
    if count <= 0:
        return 0
    with flowing(FlowCategory.CASUALTY):
        shift_stat(besieged, "population", -count)
    language = await spoken_language(ctx.session, besieged.id)
    ctx.session.add(
        CaptiveCohortRow(
            captor_entity_id=victor.id,
            origin_entity_id=besieged.id,
            war_id=war_id,
            language_entity_id=language.id if language is not None else None,
            count=count,
            social_class=SocialClass.FARMER,
            fate=CaptiveFate.HELD,
            since_epoch=ctx.epoch,
        )
    )
    return count


async def maim(ctx: TickContext, besieged: EntityRow) -> int:
    population = stat(besieged, "population") or 0
    table = ctx.rules.siege_depth
    lost = round_half_up(population * table.maim_pct / PERCENT * PERCENT / max(1, ctx.rules.maimed.return_pct))
    return await return_maimed(ctx, besieged, lost)


async def infamy(ctx: TickContext, besieged: EntityRow, victor: EntityRow, atlas: RegionAtlas) -> int:
    region = atlas.top_region(besieged.id)
    if region is None:
        return 0
    witnesses = 0
    neighbours = await ctx.session.scalars(
        select(EntityRow.id).where(
            EntityRow.world_id == besieged.world_id, EntityRow.status == EntityStatus.CANON, EntityRow.entity_type.in_(list(COMMUNITY_TYPES))
        )
    )
    for community_id in list(neighbours):
        hops = atlas.region_hops(atlas.top_region(community_id), region)
        if community_id in {victor.id, besieged.id} or hops is None or hops > 1:
            continue
        await change_relation(ctx, community_id, victor.id, -ctx.rules.siege_depth.infamy, MemoryKind.ILL_WILL, note=f"sacked {besieged.name}")
        witnesses += 1
    return witnesses


def defender_choice(ctx: TickContext, siege: SiegeRow, garrison: int, besiegers: int, walls: SettlementInfrastructureRow | None) -> DefenderAction:
    table = ctx.rules.siegecraft
    if siege.last_defence is not None and "last_defence" in siege.locked:
        return siege.last_defence
    condition = walls.walls_condition if walls is not None else PERCENT
    if besiegers and garrison * PERCENT >= besiegers * table.sally_ratio_pct:
        return DefenderAction.SALLY
    if siege.breaches > 0 or condition < table.breach_condition:
        return DefenderAction.REPAIR
    if siege.supplies < ctx.rules.urban.ration_supplies_days:
        return DefenderAction.RATION
    return DefenderAction.SEEK_RELIEF


def water_days(walls: SettlementInfrastructureRow | None) -> int:
    return WATER_DAYS[walls.water if walls is not None else WaterSupply.WELL]
