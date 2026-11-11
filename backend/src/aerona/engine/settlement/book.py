from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.settlement import DistrictDesignRow, DistrictRow, SettlementInfrastructureRow, SettlementProfileRow, SettlementTreasuryRow
from aerona.domain.enums.settlement import TIER_ORDER, BuildMaterial, DistrictKind, SizeTier, TreasuryEntry, WaterSupply
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.context import TickContext
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.stats import stat
from aerona.engine.settlement.districts import DistrictEffects, designs_for, effects_of
from aerona.engine.urban.coverage import UrbanState, urban_state
from aerona.rules.registry import Rules


@dataclass
class Town:
    entity: EntityRow
    profile: SettlementProfileRow
    infrastructure: SettlementInfrastructureRow
    districts: list[DistrictRow]
    work_used: int = 0
    designs: dict[int, DistrictDesignRow] = field(default_factory=dict)
    urban: UrbanState = field(default_factory=UrbanState)

    def effects(self, rules: Rules) -> DistrictEffects:
        return effects_of(rules, self.districts, self.designs)

    def levels(self, kind: DistrictKind) -> int:
        return sum(district.level for district in self.districts if district.kind is kind)

    def tier_index(self) -> int:
        return TIER_ORDER.index(self.profile.size_tier)


def tier_for(rules: Rules, population: int, infrastructure: SettlementInfrastructureRow, granary: int) -> SizeTier:
    table = rules.urban
    water = infrastructure.water
    if population >= table.metropolis_population and water is WaterSupply.AQUEDUCT and infrastructure.sewers:
        return SizeTier.METROPOLIS
    if population >= table.city_population and water in {WaterSupply.CISTERN, WaterSupply.AQUEDUCT} and granary > 0:
        return SizeTier.CITY
    if population >= table.town_population and infrastructure.roads >= 1:
        return SizeTier.TOWN
    if population >= table.village_population:
        return SizeTier.VILLAGE
    return SizeTier.HAMLET


def fresh_infrastructure(rules: Rules, settlement: EntityRow, knowledge: KnowledgeMap) -> SettlementInfrastructureRow:
    table = rules.urban
    architecture = knowledge.level(settlement.id, KnowledgeBranch.ARCHITECTURE)
    defense = stat(settlement, "defense") or 0
    water = WaterSupply.AQUEDUCT if architecture >= table.aqueduct_level else WaterSupply.CISTERN if architecture >= table.cistern_level else WaterSupply.WELL
    population = stat(settlement, "population") or 0
    return SettlementInfrastructureRow(
        settlement_entity_id=settlement.id,
        walls_level=min(5, defense // max(1, table.walls_per_level)),
        walls_material=BuildMaterial.STONE if architecture >= rules.fire.stone_level else BuildMaterial.TIMBER,
        walls_condition=100,
        gates=1 if defense > 0 else 0,
        roads=min(5, 1 + architecture // 2) if population >= table.town_population else 0,
        water=water,
        sewers=architecture >= table.sewer_level and population >= table.city_population,
        granary_capacity=0,
        warehouse_capacity=0,
        harbour_capacity=0,
        towers=min(20, defense // 20),
        locked=[],
    )


def starting_districts(rules: Rules, settlement: EntityRow, epoch: int) -> list[DistrictKind]:
    population = stat(settlement, "population") or 0
    kinds = [DistrictKind.FARMLAND]
    if population >= rules.urban.town_population:
        kinds.append(DistrictKind.MARKET)
    if population >= rules.urban.city_population:
        kinds.extend([DistrictKind.CRAFT_QUARTER, DistrictKind.TEMPLE_QUARTER])
    return kinds


async def town_of(ctx: TickContext, settlement: EntityRow, knowledge: KnowledgeMap) -> Town:
    session = ctx.session
    profile = await session.get(SettlementProfileRow, settlement.id)
    infrastructure = await session.get(SettlementInfrastructureRow, settlement.id)
    if infrastructure is None:
        infrastructure = fresh_infrastructure(ctx.rules, settlement, knowledge)
        session.add(infrastructure)
    districts = list(await session.scalars(select(DistrictRow).where(DistrictRow.settlement_entity_id == settlement.id).order_by(DistrictRow.id)))
    if profile is None:
        for kind in starting_districts(ctx.rules, settlement, ctx.epoch):
            district = DistrictRow(
                settlement_entity_id=settlement.id, kind=kind, level=1, condition=100, material=infrastructure.walls_material, built_epoch=ctx.epoch
            )
            session.add(district)
            districts.append(district)
        granary = sum(district.level for district in districts if district.kind in {DistrictKind.FARMLAND, DistrictKind.MARKET})
        profile = SettlementProfileRow(
            settlement_entity_id=settlement.id,
            size_tier=tier_for(ctx.rules, stat(settlement, "population") or 0, infrastructure, granary),
            treasury=0,
            tax_rate=ctx.rules.taxation.default_tax,
            public_order=ctx.rules.crime.order_base,
            crime=10,
            unrest=10,
            sanitation=ctx.rules.sanitation.base,
            fire_risk=ctx.rules.fire.timber_risk,
            prestige=0,
            militia=0,
            free_city=False,
            foreigners={},
            updated_epoch=ctx.epoch,
            locked=[],
        )
        session.add(profile)
        await session.flush()
    urban = await urban_state(session, settlement.id, profile, districts, stat(settlement, "population") or 0)
    return Town(settlement, profile, infrastructure, districts, designs=await designs_for(session, districts), urban=urban)


def ledger(ctx: TickContext, town: Town, entry: TreasuryEntry, amount: int, note: str | None = None) -> int:
    if amount == 0:
        return 0
    spent = amount if amount > 0 else -min(-amount, max(0, town.profile.treasury))
    if spent == 0:
        return 0
    town.profile.treasury += spent
    ctx.session.add(
        SettlementTreasuryRow(
            settlement_entity_id=town.entity.id, epoch=ctx.epoch, entry=entry, amount=spent, balance=town.profile.treasury, note=(note or "")[:120] or None
        )
    )
    return spent


async def credit(ctx: TickContext, settlement: EntityRow, entry: TreasuryEntry, amount: int, note: str | None = None) -> None:
    profile = await ctx.session.get(SettlementProfileRow, settlement.id)
    if profile is None or amount <= 0:
        return
    profile.treasury += amount
    ctx.session.add(SettlementTreasuryRow(settlement_entity_id=settlement.id, epoch=ctx.epoch, entry=entry, amount=amount, balance=profile.treasury, note=note))


async def towns(session: AsyncSession) -> dict[int, SettlementProfileRow]:
    return {row.settlement_entity_id: row for row in await session.scalars(select(SettlementProfileRow))}
