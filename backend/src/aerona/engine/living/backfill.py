from sqlalchemy import select

from aerona.catalog.domestication import HOUSED_STAGES
from aerona.db.fixups import fixup_due
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.cuisine import DishRow
from aerona.db.tables.ecology import SpeciesProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.industry import CommunityMethodRow
from aerona.db.tables.living import GeneBankRow, LivingLineRow, LivingProfileRow
from aerona.db.tables.regime import BreedingPlanRow
from aerona.db.tables.structures import StructureDesignRow, StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.cuisine import CookingMethod
from aerona.domain.enums.ecology import Temperament
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.industry import MethodKind, ProcessKind
from aerona.domain.enums.living import CultivationMethod, Fertility, GrowthStage, Metabolism
from aerona.domain.enums.structure import BuildingForm, StructureKind
from aerona.domain.enums.vehicles import VehicleFrame
from aerona.engine.context import TickContext
from aerona.engine.living.society import doctrine_stances

LEGACY_FIXUP = "living.legacy_backfill"
BRED = HOUSED_STAGES
BRED_STABILITY = 70
VESSEL_LIFESPAN = 80
GROWN_LIFESPAN = 200
FULL_SIZE = 100


def alive(thing_id: int, metabolism: Metabolism, lifespan: int, temperament: Temperament | None, epoch: int) -> LivingProfileRow:
    return LivingProfileRow(
        thing_node_id=thing_id,
        metabolism=metabolism,
        feed_commodity=CommodityKind.FODDER if metabolism is Metabolism.FEEDING else None,
        feed_per_season=1,
        growth_stage=GrowthStage.GROWN,
        size_pct=FULL_SIZE,
        regeneration=30,
        health=100,
        temperament=temperament,
        bond=50,
        fertility=Fertility.STERILE,
        lifespan_years=lifespan,
        age_seasons=0,
        planted_epoch=epoch,
        locked=[],
    )


async def bioships(ctx: TickContext) -> int:
    made = 0
    for vessel in list(
        await ctx.session.scalars(select(VesselProfileRow).where(VesselProfileRow.frame == VehicleFrame.BIOSHIP).order_by(VesselProfileRow.entity_id))
    ):
        if held(vessel.entity_id) or await ctx.session.get(LivingProfileRow, vessel.entity_id) is not None:
            continue
        ctx.session.add(alive(vessel.entity_id, Metabolism.FEEDING, VESSEL_LIFESPAN, Temperament.PLACID, ctx.epoch))
        made += 1
    return made


async def grown_works(ctx: TickContext) -> int:
    made = 0
    grown = select(StructureDesignRow.id).where(StructureDesignRow.form == BuildingForm.GROWN)
    profiles = select(StructureProfileRow).where(StructureProfileRow.design_id.in_(grown)).order_by(StructureProfileRow.structure_entity_id)
    for work in list(await ctx.session.scalars(profiles)):
        if held(work.structure_entity_id) or await ctx.session.get(LivingProfileRow, work.structure_entity_id) is not None:
            continue
        ctx.session.add(alive(work.structure_entity_id, Metabolism.LIGHT, GROWN_LIFESPAN, None, ctx.epoch))
        made += 1
    return made


async def banks(ctx: TickContext) -> int:
    made = 0
    rows = await ctx.session.scalars(
        select(EntityRow)
        .join(StructureProfileRow, StructureProfileRow.structure_entity_id == EntityRow.id)
        .where(StructureProfileRow.kind == StructureKind.CLONING_FACILITY, EntityRow.status == EntityStatus.CANON)
        .order_by(StructureProfileRow.structure_entity_id)
    )
    for entity in list(rows):
        if held(entity.id) or await ctx.session.get(GeneBankRow, entity.id) is not None:
            continue
        ctx.session.add(
            GeneBankRow(
                structure_entity_id=entity.id,
                holder_node_id=entity.affiliated_entity_id,
                upkeep=ctx.rules.genome_design.bank_upkeep,
                unpaid_epochs=0,
                locked=[],
            )
        )
        made += 1
    return made


async def bred_species_lines(ctx: TickContext) -> int:
    made = 0
    lined = set(await ctx.session.scalars(select(LivingLineRow.species_entity_id).where(LivingLineRow.species_entity_id.is_not(None))))
    bred = select(SpeciesProfileRow.species_entity_id).where(SpeciesProfileRow.stage.in_(list(BRED))).order_by(SpeciesProfileRow.species_entity_id)
    for species_id in list(await ctx.session.scalars(bred)):
        species = await ctx.session.get(EntityRow, species_id)
        if species is None or species.status is not EntityStatus.CANON or species_id in lined or held(species_id):
            continue
        ctx.session.add(
            LivingLineRow(
                name=f"the bred line of {species.name}",
                method=CultivationMethod.SELECTIVE_BREEDING,
                species_entity_id=species_id,
                stability=BRED_STABILITY,
                fertility=Fertility.BREEDS_TRUE,
                founded_epoch=ctx.epoch,
                locked=[],
            )
        )
        made += 1
    return made


async def bred_lines(ctx: TickContext) -> int:
    made = await bred_species_lines(ctx)
    housed = set(
        await ctx.session.scalars(
            select(LivingLineRow.owner_node_id).where(LivingLineRow.method == CultivationMethod.SELECTIVE_BREEDING, LivingLineRow.species_entity_id.is_(None))
        )
    )
    for plan in list(await ctx.session.scalars(select(BreedingPlanRow).order_by(BreedingPlanRow.plan_id))):
        house = await ctx.session.get(EntityRow, plan.house_entity_id)
        if house is None or held(house.id) or house.id in housed:
            continue
        housed.add(house.id)
        ctx.session.add(
            LivingLineRow(
                name=f"the line {house.name} seeks by marriage",
                method=CultivationMethod.SELECTIVE_BREEDING,
                owner_node_id=house.id,
                maker_node_id=house.id,
                stability=BRED_STABILITY,
                fertility=Fertility.BREEDS_TRUE,
                founded_epoch=ctx.epoch,
                locked=[],
            )
        )
        made += 1
    return made


async def vat_food(ctx: TickContext) -> int:
    made = 0
    towns = select(DishRow.origin_node_id).where(DishRow.method == CookingMethod.VAT_GROWN, DishRow.origin_node_id.is_not(None)).distinct()
    farming = set(await ctx.session.scalars(select(CommunityMethodRow.community_node_id).where(CommunityMethodRow.process == ProcessKind.FARMING)))
    for town_id in list(await ctx.session.scalars(towns)):
        town = await ctx.session.get(EntityRow, town_id) if town_id is not None else None
        if town is None or town.entity_type is not EntityType.SETTLEMENT or town.id in farming or held(town.id):
            continue
        ctx.session.add(
            CommunityMethodRow(community_node_id=town.id, process=ProcessKind.FARMING, method=MethodKind.VAT_CULTURE, adopted_epoch=ctx.epoch, locked=[])
        )
        made += 1
    return made


async def keep_kinds_alive(ctx: TickContext) -> int:
    return await bioships(ctx) + await grown_works(ctx) + await banks(ctx) + await bred_lines(ctx) + await vat_food(ctx) + await doctrine_stances(ctx)


async def legacy_backfill(ctx: TickContext) -> int:
    if not await fixup_due(ctx.session, LEGACY_FIXUP):
        return 0
    result = {
        "bioships": await bioships(ctx),
        "grown_works": await grown_works(ctx),
        "banks": await banks(ctx),
        "bred_lines": await bred_lines(ctx),
        "vat_food": await vat_food(ctx),
        "stances": await doctrine_stances(ctx),
    }
    ctx.session.add(AppliedFixupRow(key=LEGACY_FIXUP, result=result))
    await ctx.session.flush()
    return sum(result.values())
