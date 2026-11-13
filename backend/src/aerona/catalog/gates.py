from collections.abc import Callable
from enum import StrEnum

from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.rarity import Rarity
from aerona.rules.registry import Rules


class Gate(StrEnum):
    INFLUENCE_TOOLS = "influence_tools"
    MIRACLE_TOOL = "miracle_tool"
    SPIRIT_CLOAK = "spirit_cloak"
    RARE_TOOLS = "rare_tools"
    HOLY_WORLD = "holy_world"
    INTERWORLD_TREATY = "interworld_treaty"
    FOREIGN_GOD_WAR = "foreign_god_war"
    TAKE_LIFE = "take_life"
    SEAL_GATE = "seal_gate"
    REKINDLE_STAR = "rekindle_star"
    SEAL_LEAK = "seal_leak"
    LEGENDARY_TOOLS = "legendary_tools"
    OPEN_COSMIC_BED = "open_cosmic_bed"
    BIRTH_WORLD = "birth_world"
    HANG_EXTINGUISH_STAR = "hang_extinguish_star"
    GALAXY_CREATION = "galaxy_creation"
    CLUSTER_CREATION = "cluster_creation"
    DIMENSION_CREATION = "dimension_creation"
    GALACTIC_WORKS = "galactic_works"
    DIMENSIONAL_WORKS = "dimensional_works"
    COSMIC_WORKS = "cosmic_works"
    POWER_SITES = "power_sites"
    ROAD_OPENING = "road_opening"


GATE_RULES: dict[Gate, Callable[[Rules], int]] = {
    Gate.INFLUENCE_TOOLS: lambda rules: rules.rarity_gates.influence_tools,
    Gate.MIRACLE_TOOL: lambda rules: rules.rarity_gates.miracle_tool,
    Gate.SPIRIT_CLOAK: lambda rules: rules.rarity_gates.spirit_cloak,
    Gate.RARE_TOOLS: lambda rules: rules.rarity_gates.rare_tools,
    Gate.HOLY_WORLD: lambda rules: rules.rarity_gates.holy_world,
    Gate.INTERWORLD_TREATY: lambda rules: rules.rarity_gates.interworld_treaty,
    Gate.FOREIGN_GOD_WAR: lambda rules: rules.rarity_gates.foreign_god_war,
    Gate.TAKE_LIFE: lambda rules: rules.rarity_gates.take_life,
    Gate.SEAL_GATE: lambda rules: rules.rarity_gates.seal_gate,
    Gate.REKINDLE_STAR: lambda rules: rules.rarity_gates.rekindle_star,
    Gate.SEAL_LEAK: lambda rules: rules.rarity_gates.seal_leak,
    Gate.LEGENDARY_TOOLS: lambda rules: rules.rarity_gates.legendary_tools,
    Gate.OPEN_COSMIC_BED: lambda rules: rules.rarity_gates.open_cosmic_bed,
    Gate.BIRTH_WORLD: lambda rules: rules.rarity_gates.birth_world,
    Gate.HANG_EXTINGUISH_STAR: lambda rules: rules.rarity_gates.hang_extinguish_star,
    Gate.GALAXY_CREATION: lambda rules: rules.rarity_gates.galaxy_creation,
    Gate.CLUSTER_CREATION: lambda rules: rules.rarity_gates.cluster_creation,
    Gate.DIMENSION_CREATION: lambda rules: rules.rarity_gates.dimension_creation,
    Gate.GALACTIC_WORKS: lambda rules: rules.rarity_gates.galactic_works,
    Gate.DIMENSIONAL_WORKS: lambda rules: rules.rarity_gates.dimensional_works,
    Gate.COSMIC_WORKS: lambda rules: rules.rarity_gates.cosmic_works,
    Gate.POWER_SITES: lambda rules: rules.rarity_gates.power_sites,
    Gate.ROAD_OPENING: lambda rules: rules.rarity_gates.road_opening,
}

CREATION_GATE_RULES: dict[EntityType, Callable[[Rules], int]] = {
    EntityType.REGION: lambda rules: rules.rarity_gates.create_region,
    EntityType.PLACE: lambda rules: rules.rarity_gates.create_place,
    EntityType.RESOURCE: lambda rules: rules.rarity_gates.create_resource,
    EntityType.SETTLEMENT: lambda rules: rules.rarity_gates.create_settlement,
    EntityType.SPECIES: lambda rules: rules.rarity_gates.create_species,
    EntityType.PEOPLE: lambda rules: rules.rarity_gates.create_people,
    EntityType.MORTAL: lambda rules: rules.rarity_gates.create_mortal,
    EntityType.ITEM: lambda rules: rules.rarity_gates.create_item,
    EntityType.STRUCTURE: lambda rules: rules.rarity_gates.create_structure,
    EntityType.LANGUAGE: lambda rules: rules.rarity_gates.create_language,
    EntityType.LEGEND: lambda rules: rules.rarity_gates.create_legend,
    EntityType.TRADITION: lambda rules: rules.rarity_gates.create_tradition,
    EntityType.CULT: lambda rules: rules.rarity_gates.create_cult,
    EntityType.FACTION: lambda rules: rules.rarity_gates.create_faction,
    EntityType.CELESTIAL: lambda rules: rules.rarity_gates.create_celestial,
    EntityType.ARTWORK: lambda rules: rules.rarity_gates.create_artwork,
    EntityType.LAW: lambda rules: rules.rarity_gates.create_law,
    EntityType.SPIRIT: lambda rules: rules.rarity_gates.create_spirit,
    EntityType.KNOWLEDGE: lambda rules: rules.rarity_gates.create_knowledge,
    EntityType.PROPHECY: lambda rules: rules.rarity_gates.create_prophecy,
    EntityType.EVENT: lambda rules: rules.rarity_gates.create_event,
    EntityType.VESSEL: lambda rules: rules.rarity_gates.create_vessel,
    EntityType.OUTER_BEING: lambda rules: rules.rarity_gates.create_outer_being,
    EntityType.ARMY: lambda rules: rules.rarity_gates.create_army,
    EntityType.NATURAL_LAW: lambda rules: rules.rarity_gates.create_natural_law,
    EntityType.TRADE_ROUTE: lambda rules: rules.rarity_gates.create_trade_route,
    EntityType.DISEASE: lambda rules: rules.rarity_gates.create_disease,
    EntityType.POLITY: lambda rules: rules.rarity_gates.create_polity,
    EntityType.HOUSE: lambda rules: rules.rarity_gates.create_house,
    EntityType.TREATY: lambda rules: rules.rarity_gates.create_treaty,
    EntityType.TITLE: lambda rules: rules.rarity_gates.create_title,
    EntityType.IDEOLOGY: lambda rules: rules.rarity_gates.create_ideology,
    EntityType.BEAST: lambda rules: rules.rarity_gates.create_beast,
    EntityType.RITE: lambda rules: rules.rarity_gates.create_rite,
    EntityType.THEORY: lambda rules: rules.rarity_gates.create_theory,
    EntityType.ART_FORM: lambda rules: rules.rarity_gates.create_art_form,
    EntityType.PHENOMENON: lambda rules: rules.rarity_gates.create_phenomenon,
    EntityType.COSMIC_BEING: lambda rules: rules.rarity_gates.create_cosmic_being,
    EntityType.VEHICLE_TYPE: lambda rules: rules.rarity_gates.create_vehicle_type,
    EntityType.UNIT_TYPE: lambda rules: rules.rarity_gates.create_unit_type,
    EntityType.EQUIPMENT_MODEL: lambda rules: rules.rarity_gates.create_equipment_model,
    EntityType.DISH: lambda rules: rules.rarity_gates.create_dish,
    EntityType.BUILDING_TYPE: lambda rules: rules.rarity_gates.create_building_type,
}


def gate_rarity(rules: Rules, gate: Gate) -> Rarity:
    return Rarity.from_rank(GATE_RULES[gate](rules))


def creation_gate_rarity(rules: Rules, entity_type: EntityType) -> Rarity:
    return Rarity.from_rank(CREATION_GATE_RULES[entity_type](rules))


def passes_gate(rules: Rules, rarity: Rarity, gate: Gate) -> bool:
    return rarity.at_least(gate_rarity(rules, gate))


def may_create(rules: Rules, rarity: Rarity, entity_type: EntityType) -> bool:
    return rarity.at_least(creation_gate_rarity(rules, entity_type))
