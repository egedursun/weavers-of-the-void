from aerona.engine.body.decline import run_decline
from aerona.engine.collective.embodied import align_made
from aerona.engine.context import TickContext
from aerona.engine.cosmos.being_wounds import tend_beings
from aerona.engine.cuisine.dishes import run_kitchens
from aerona.engine.equipment.stores import forge_all
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.military.unit_types import run_unit_types
from aerona.engine.military.units import equip_bare_stacks
from aerona.engine.mortal.attraction import assign_attraction
from aerona.engine.phase import Phase
from aerona.engine.phases.dominion import count
from aerona.engine.structures.megastructures import run_megastructures
from aerona.engine.vehicles.fixups import made_kinds_fixup
from aerona.engine.vehicles.production import vehicle_works


@reads(
    "table.army_unit_equipment",
    "table.community_stocks",
    "table.designs",
    "table.dishes",
    "table.equipment_models",
    "table.equipment_stores",
    "table.goods_flows",
    "table.holder_levels",
    "table.language_profiles",
    "table.lexemes",
    "table.name_registry",
    "table.node_materials",
    "table.polity_members",
    "table.structure_designs",
    "table.unit_design_equipment",
    "table.unit_designs",
    "table.world_materials",
)
@writes("table.community_stocks", "table.entities", "table.equipment_models", "table.equipment_stores", "table.goods_flows", "table.name_registry")
async def equipment_forging(ctx: TickContext) -> None:
    count(ctx, "equipment_forging", await forge_all(ctx))
    ctx.count("equipment_issued", await equip_bare_stacks(ctx))


@reads(
    "table.applied_fixups",
    "table.armies",
    "table.army_templates",
    "table.army_units",
    "table.bonds",
    "table.designs",
    "table.dishes",
    "table.epoch_year_cursors",
    "table.equipment_models",
    "table.holder_levels",
    "table.language_profiles",
    "table.lexemes",
    "table.name_registry",
    "table.node_materials",
    "table.people_culture",
    "table.polity_members",
    "table.structure_designs",
    "table.unit_design_equipment",
    "table.unit_design_techniques",
    "table.unit_designs",
    "table.world_materials",
)
@writes(
    "table.applied_fixups",
    "table.army_units",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.epoch_year_cursors",
    "table.equipment_models",
    "table.incident_participants",
    "table.incidents",
    "table.name_registry",
    "table.unit_design_equipment",
    "table.unit_design_techniques",
    "table.unit_designs",
)
async def unit_types(ctx: TickContext) -> None:
    count(ctx, "unit_types", await run_unit_types(ctx))


@reads(
    "table.applied_fixups",
    "table.armies",
    "table.army_profiles",
    "table.design_components",
    "table.design_mounts",
    "table.design_sections",
    "table.design_techniques",
    "table.designs",
    "table.dishes",
    "table.equipment_models",
    "table.goods_flows",
    "table.holder_levels",
    "table.language_profiles",
    "table.lexemes",
    "table.name_registry",
    "table.node_materials",
    "table.polity_members",
    "table.polity_profiles",
    "table.region_environment",
    "table.structure_designs",
    "table.structure_profiles",
    "table.trade_route_profiles",
    "table.unit_designs",
    "table.vehicle_group_sections",
    "table.vehicle_groups",
    "table.vessel_profiles",
    "table.workshops",
    "table.world_materials",
)
@writes(
    "table.applied_fixups",
    "table.community_stocks",
    "table.design_components",
    "table.design_mounts",
    "table.design_sections",
    "table.designs",
    "table.entities",
    "table.equipment_models",
    "table.goods_flows",
    "table.name_registry",
    "table.polity_profiles",
    "table.vehicle_group_sections",
    "table.vehicle_groups",
)
async def vehicle_works_phase(ctx: TickContext) -> None:
    ctx.count("made_entities_aligned", await align_made(ctx.session))
    for key, value in (await made_kinds_fixup(ctx)).items():
        ctx.count(f"made_kinds_fixup_{key}", value)
    count(ctx, "vehicle_works", await vehicle_works(ctx))


@reads("table.megastructure_states", "table.structure_profiles")
@writes("table.megastructure_states", "table.routes", "table.stars", "table.worlds")
async def megastructures(ctx: TickContext) -> None:
    count(ctx, "megastructures", await run_megastructures(ctx))


@reads(
    "table.armies",
    "table.army_profiles",
    "table.community_dishes",
    "table.community_stocks",
    "table.designs",
    "table.dishes",
    "table.epoch_year_cursors",
    "table.equipment_models",
    "table.holder_levels",
    "table.language_profiles",
    "table.lexemes",
    "table.name_registry",
    "table.structure_designs",
    "table.unit_designs",
)
@writes(
    "table.army_profiles",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_dishes",
    "table.dish_ingredients",
    "table.dishes",
    "table.entities",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.language_profiles",
    "table.name_registry",
)
async def kitchens(ctx: TickContext) -> None:
    count(ctx, "kitchens", await run_kitchens(ctx))


@reads("table.mortal_castes", "table.mortal_profiles", "table.people_reproduction")
@writes("table.entities", "table.mortal_profiles")
async def attraction(ctx: TickContext) -> None:
    count(ctx, "attraction", await assign_attraction(ctx))


@reads(
    "mortal.age",
    "mortal.agility",
    "mortal.charisma",
    "mortal.endurance",
    "mortal.hp",
    "mortal.intellect",
    "mortal.lifespan",
    "mortal.strength",
    "mortal.willpower",
    "table.assistive_aids",
    "table.bodies",
    "table.body_customs",
    "table.bonds",
    "table.conditions",
    "table.cult_tenets",
    "table.culture_values",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.genomes",
    "table.holder_levels",
    "table.injuries",
    "table.item_profiles",
    "table.memories",
    "table.minds",
    "table.mortal_equipment",
    "table.mortal_profiles",
    "table.nodes",
    "table.prostheses",
)
@writes(
    "table.bodies",
    "table.body_customs",
    "table.chronicle",
    "table.chronicle_entities",
    "table.conditions",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.memories",
)
async def cognitive_decline(ctx: TickContext) -> None:
    count(ctx, "cognitive_decline", await run_decline(ctx))


@reads("table.bodies", "table.injuries")
@writes("table.bodies", "table.world_materials")
async def being_wounds(ctx: TickContext) -> None:
    count(ctx, "being_wounds", await tend_beings(ctx))


PHASES = (
    Phase("equipment_forging", equipment_forging),
    Phase("unit_types", unit_types),
    Phase("vehicle_works", vehicle_works_phase),
    Phase("megastructures", megastructures),
    Phase("kitchens", kitchens),
    Phase("attraction", attraction),
    Phase("cognitive_decline", cognitive_decline),
    Phase("being_wounds", being_wounds),
)
