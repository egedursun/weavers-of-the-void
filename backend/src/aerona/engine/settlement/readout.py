from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.economy import WorkshopRow
from aerona.db.tables.settlement import DistrictDesignRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.domain.enums.economy import WorkshopKind
from aerona.domain.enums.settlement import BuildMaterial
from aerona.domain.enums.society import Commodity, KnowledgeBranch, SocialClass
from aerona.engine.body.customs import people_of
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.settlement.book import Town
from aerona.engine.settlement.districts import AdminParts, DistrictEffects, admin_parts, parameters_of
from aerona.engine.settlement.storage import StorageParts, design_for, settlement_store, store_kind
from aerona.rules.registry import Rules


@dataclass(frozen=True)
class Defences:
    wall_pct: int
    tower_pct: int
    batter_pct: int
    gate_weakness_pct: int


@dataclass(frozen=True)
class PlanReadout:
    admin: AdminParts
    effects: DistrictEffects
    food: StorageParts
    goods: StorageParts
    defences: Defences
    prestige_pull_pct: int
    prestige_investment_pct: int
    district_effects: dict[int, dict[str, int]]
    designs: list[DistrictDesignRow]


def defences_of(rules: Rules, town: Town) -> Defences:
    table = rules.districts
    walls = town.infrastructure
    stone = walls.walls_material is BuildMaterial.STONE
    material = table.stone_wall_pct if stone else table.timber_wall_pct
    return Defences(
        wall_pct=round(walls.walls_level * rules.siegecraft.wall_defence_pct * material / PERCENT),
        tower_pct=walls.towers * table.tower_defence_pct,
        batter_pct=table.stone_batter_pct if stone else table.timber_batter_pct,
        gate_weakness_pct=max(0, walls.gates - 1) * table.gate_breach_pct,
    )


async def plan_readout(session: AsyncSession, rules: Rules, town: Town) -> PlanReadout:
    entity = town.entity
    people = await people_of(session, entity)
    culture = await session.get(PeopleCultureRow, people.id) if people is not None else None
    society = await session.get(CommunitySocietyRow, entity.id)
    knowledge = await KnowledgeMap.load(session)
    effects = town.effects(rules)
    stores = {
        row.kind: row
        for row in await session.scalars(
            select(WorkshopRow).where(WorkshopRow.community_entity_id == entity.id, WorkshopRow.kind.in_([WorkshopKind.GRANARY, WorkshopKind.WAREHOUSE]))
        )
    }
    designs = list(await session.scalars(select(DistrictDesignRow).where(DistrictDesignRow.world_id == entity.world_id).order_by(DistrictDesignRow.id)))
    granary = stores.get(store_kind(Commodity.FOOD))
    warehouse = stores.get(store_kind(Commodity.GOODS))
    food = settlement_store(rules, effects.food_store, granary, Commodity.FOOD, design=await design_for(session, granary))
    goods = settlement_store(rules, effects.goods_store, warehouse, Commodity.GOODS, design=await design_for(session, warehouse))
    return PlanReadout(
        admin=admin_parts(
            rules,
            literacy=culture.literacy if culture is not None else 0,
            scribe_share=society.share(SocialClass.SCRIBE) if society is not None else 0.0,
            writing=knowledge.level(entity.id, KnowledgeBranch.WRITING),
            palace_pct=effects.admin_pct,
        ),
        effects=effects,
        food=StorageParts(food.districts, food.workshops, max(0, town.infrastructure.granary_capacity - food.districts - food.workshops)),
        goods=StorageParts(goods.districts, goods.workshops, max(0, town.infrastructure.warehouse_capacity - goods.districts - goods.workshops)),
        defences=defences_of(rules, town),
        prestige_pull_pct=round(town.profile.prestige * rules.districts.prestige_pull_pct / PERCENT),
        prestige_investment_pct=round(town.profile.prestige * rules.districts.prestige_investment_pct / PERCENT),
        district_effects={
            district.id: {
                key: value * district.level
                for key, value in parameters_of(rules, district.kind, town.designs.get(district.design_id) if district.design_id is not None else None).items()
                if value
            }
            for district in town.districts
        },
        designs=designs,
    )
