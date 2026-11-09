from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class RarityGatesRules:
    create_region: int = rule(
        3, 0, 5, RuleGroup.RARITY_TIERS, "Lowest son rarity that can create a Region (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
    create_place: int = rule(
        0, 0, 5, RuleGroup.RARITY_TIERS, "Lowest son rarity that can create a Place (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
    create_resource: int = rule(
        0, 0, 5, RuleGroup.RARITY_TIERS, "Lowest son rarity that can create a Resource (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
    create_settlement: int = rule(
        0, 0, 5, RuleGroup.RARITY_TIERS, "Lowest son rarity that can create a Settlement (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
    create_species: int = rule(
        0, 0, 5, RuleGroup.RARITY_TIERS, "Lowest son rarity that can create a Species (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
    create_people: int = rule(
        0, 0, 5, RuleGroup.RARITY_TIERS, "Lowest son rarity that can create a People (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
    create_mortal: int = rule(
        0, 0, 5, RuleGroup.RARITY_TIERS, "Lowest son rarity that can create a Mortal (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
    create_item: int = rule(
        1, 0, 5, RuleGroup.RARITY_TIERS, "Lowest son rarity that can create an Item (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
    create_structure: int = rule(
        1, 0, 5, RuleGroup.RARITY_TIERS, "Lowest son rarity that can create a Structure (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
    create_language: int = rule(
        1, 0, 5, RuleGroup.RARITY_TIERS, "Lowest son rarity that can create a Language (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
    create_legend: int = rule(
        0, 0, 5, RuleGroup.RARITY_TIERS, "Lowest son rarity that can create a Legend (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
    create_tradition: int = rule(
        0, 0, 5, RuleGroup.RARITY_TIERS, "Lowest son rarity that can create a Tradition (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
    create_cult: int = rule(
        1, 0, 5, RuleGroup.RARITY_TIERS, "Lowest son rarity that can create a Cult (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
    create_faction: int = rule(
        1, 0, 5, RuleGroup.RARITY_TIERS, "Lowest son rarity that can create a Faction (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
    create_celestial: int = rule(
        2, 0, 5, RuleGroup.RARITY_TIERS, "Lowest son rarity that can create a Celestial Body (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
    create_artwork: int = rule(
        0, 0, 5, RuleGroup.RARITY_TIERS, "Lowest son rarity that can create an Artwork (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
    create_law: int = rule(
        1, 0, 5, RuleGroup.RARITY_TIERS, "Lowest son rarity that can create a Law (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
    create_spirit: int = rule(
        1, 0, 5, RuleGroup.RARITY_TIERS, "Lowest son rarity that can create a Spirit (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
    create_knowledge: int = rule(
        2, 0, 5, RuleGroup.RARITY_TIERS, "Lowest son rarity that can create Knowledge (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
    create_prophecy: int = rule(
        3, 0, 5, RuleGroup.RARITY_TIERS, "Lowest son rarity that can create a Prophecy (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
    create_event: int = rule(
        3, 0, 5, RuleGroup.RARITY_TIERS, "Lowest son rarity that can create an Event (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
    create_vessel: int = rule(
        2, 0, 5, RuleGroup.RARITY_TIERS, "Lowest son rarity that can create a Vessel (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
    create_outer_being: int = rule(
        5, 0, 5, RuleGroup.RARITY_TIERS, "Lowest son rarity that can create an Outer Being (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
    create_army: int = rule(
        3, 0, 5, RuleGroup.RARITY_TIERS, "Lowest son rarity that can create an Army (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
    create_trade_route: int = rule(
        5, 0, 5, RuleGroup.RARITY_TIERS, "Lowest son rarity that can create a Trade route (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
    create_disease: int = rule(
        2, 0, 5, RuleGroup.RARITY_TIERS, "Lowest son rarity that can loose a Disease (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
    create_polity: int = rule(
        3, 0, 5, RuleGroup.RARITY_TIERS, "Lowest son rarity that can found a Polity (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
    create_house: int = rule(
        1, 0, 5, RuleGroup.RARITY_TIERS, "Lowest son rarity that can found a House (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
    create_treaty: int = rule(
        1, 0, 5, RuleGroup.RARITY_TIERS, "Lowest son rarity that can broker a Treaty (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
    create_title: int = rule(
        2, 0, 5, RuleGroup.RARITY_TIERS, "Lowest son rarity that can create a Title (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
    create_ideology: int = rule(
        1, 0, 5, RuleGroup.RARITY_TIERS, "Lowest son rarity that can found an Ideology (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
    create_beast: int = rule(
        2, 0, 5, RuleGroup.RARITY_TIERS, "Lowest son rarity that can loose a named Beast (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
    create_rite: int = rule(
        1, 0, 5, RuleGroup.RARITY_TIERS, "Lowest son rarity that can reveal a Rite (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
    create_theory: int = rule(
        1, 0, 5, RuleGroup.RARITY_TIERS, "Lowest son rarity that can reveal a Theory (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
    create_art_form: int = rule(
        1, 0, 5, RuleGroup.RARITY_TIERS, "Lowest son rarity that can inspire an Art form (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
    create_phenomenon: int = rule(
        2, 0, 5, RuleGroup.RARITY_TIERS, "Lowest son rarity that can raise a Phenomenon (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
    create_cosmic_being: int = rule(
        3, 0, 5, RuleGroup.RARITY_TIERS, "Lowest son rarity that can call a Cosmic Being (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
    create_natural_law: int = rule(
        4, 0, 5, RuleGroup.RARITY_TIERS, "Lowest son rarity that can create a Natural Law (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
    influence_tools: int = rule(
        1,
        0,
        5,
        RuleGroup.RARITY_TIERS,
        "Tools to influence an entity, mark a chosen one and curse: lowest son rarity (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)",
    )
    miracle_tool: int = rule(
        1, 0, 5, RuleGroup.RARITY_TIERS, "The son's miracle tool: lowest son rarity (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
    rare_tools: int = rule(
        2,
        0,
        5,
        RuleGroup.RARITY_TIERS,
        "Send-dream, disaster, give-knowledge and incite-war tools: lowest son rarity (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)",
    )
    legendary_tools: int = rule(
        4,
        0,
        5,
        RuleGroup.RARITY_TIERS,
        "Transform, destroy and bear-child tools: lowest son rarity (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)",
    )
    holy_world: int = rule(
        2, 0, 5, RuleGroup.RARITY_TIERS, "Declaring a holy world: lowest son rarity (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
    seal_gate: int = rule(3, 0, 5, RuleGroup.RARITY_TIERS, "Sealing a gate: lowest son rarity (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)")
    rekindle_star: int = rule(
        3, 0, 5, RuleGroup.RARITY_TIERS, "Rekindling a dead star: lowest son rarity (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
    spirit_cloak: int = rule(
        1, 0, 5, RuleGroup.RARITY_TIERS, "Spirit cloaking: lowest son rarity (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
    hang_extinguish_star: int = rule(
        5, 0, 5, RuleGroup.RARITY_TIERS, "Hanging and extinguishing stars: lowest son rarity (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
    interworld_treaty: int = rule(
        2, 0, 5, RuleGroup.RARITY_TIERS, "Inter-world treaty: lowest son rarity (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
    seal_leak: int = rule(3, 0, 5, RuleGroup.RARITY_TIERS, "Sealing a leak: lowest son rarity (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)")
    open_cosmic_bed: int = rule(
        4, 0, 5, RuleGroup.RARITY_TIERS, "Opening a cosmic bed (channel): lowest son rarity (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
    foreign_god_war: int = rule(
        2,
        0,
        5,
        RuleGroup.RARITY_TIERS,
        "War with a foreign god (tool and spontaneous war): lowest son rarity (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)",
    )
    birth_world: int = rule(
        4, 0, 5, RuleGroup.RARITY_TIERS, "Birthing a world: lowest son rarity (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
    take_life: int = rule(
        2, 0, 5, RuleGroup.RARITY_TIERS, "Taking a mortal's life (can_al): lowest son rarity (0 Common, 1 Uncommon, 2 Rare, 3 Epic, 4 Legendary, 5 Mythic)"
    )
