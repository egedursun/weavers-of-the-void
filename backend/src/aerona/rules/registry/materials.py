from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

G = RuleGroup.MATERIALS


@dataclass(frozen=True)
class MaterialsRules:
    damage_hardness_pct: int = rule(45, 0, 100, G, "Share of a weapon's hardness that becomes damage (%)")
    forge_heat_base: int = rule(45, 0, 100, G, "Heat a forge reaches with no metallurgy, on the scale of melting points")
    forge_heat_per_level: int = rule(10, 0, 50, G, "Heat each level of metallurgy adds to a forge, on the scale of melting points")
    bow_draw_pct: int = rule(60, 0, 300, G, "Extra harm a bow or crossbow does at full elasticity of its material (%)")
    damage_edge_pct: int = rule(40, 0, 100, G, "Share of a weapon's edge that becomes damage (%)")
    damage_quality_pct: int = rule(15, 0, 100, G, "Share of a weapon's quality that becomes damage (%)")
    protection_hardness_pct: int = rule(40, 0, 100, G, "Share of an armour's hardness that becomes protection (%)")
    protection_toughness_pct: int = rule(45, 0, 100, G, "Share of an armour's toughness that becomes protection (%)")
    protection_quality_pct: int = rule(15, 0, 100, G, "Share of an armour's quality that becomes protection (%)")
    enchant_floor: int = rule(15, 0, 100, G, "Might any material can hold, however dull")
    enchant_conductivity_pct: int = rule(85, 0, 200, G, "Extra might a material holds per point of conductivity (%)")
    curse_corruption_pct: int = rule(30, 0, 200, G, "Curse chance added per point of a material's corruption (% of the corruption)")
    corruption_lure_pct: int = rule(10, 0, 200, G, "Outer-being interest drawn per point of corrupt material held in a world (% of the corruption)")
    sanctity_splendour_pct: int = rule(8, 0, 100, G, "Temple splendour gained per epoch per point of its material's sanctity (% of the sanctity)")
    sanctity_ward_pct: int = rule(12, 0, 100, G, "Spirit unrest warded off per point of sanctity of the holy goods a community holds (% of the sanctity)")
    decay_per_epoch_pct: int = rule(20, 0, 100, G, "Share of a material's decay an item loses from its damage, protection and might each epoch (%)")
    warm_temperature: int = rule(65, 0, 100, G, "Temperature from which a region counts as warm for decay and heat")
    warm_decay_pct: int = rule(180, 100, 500, G, "Decay of organic and soft materials in warm regions (% of normal)")
    march_weight_pct: int = rule(10, 0, 100, G, "Campaign seasons slowed per point of armour weight (% of the weight)")
    heat_weight_pct: int = rule(6, 0, 100, G, "Soldiers lost to heat per point of armour weight in warm regions (per mille of the army per point)")
    skysteel_magic_density: int = rule(70, 0, 100, G, "Magic density a region needs before its smiths can work skysteel")
    world_material_god_chance: int = rule(80, 0, 100, G, "A dead god's remains become a substance of their own (%)")
    world_material_star_chance: int = rule(70, 0, 100, G, "A dead star's core falls as a substance of its own (%)")
    world_material_beast_chance: int = rule(35, 0, 100, G, "A slain great beast leaves scales or bone of a substance of its own (%)")
    world_material_leak_chance: int = rule(25, 0, 100, G, "A leak wound crystallises into a substance of its own (%)")
    world_material_research_chance: int = rule(10, 0, 100, G, "Smiths at the height of metallurgy discover an alloy of their own (% per epoch)")
    world_material_research_level: int = rule(6, 1, 10, G, "Metallurgy level at which smiths can discover an alloy")
    world_material_spread: int = rule(20, 0, 100, G, "How far a new substance's properties stray from its source (+/- points)")
    soldiers_per_kit: int = rule(10, 1, 10000, G, "Soldiers one unit of weapons or armour from the stores equips")
    kit_equipment_pct: int = rule(40, 0, 200, G, "Army equipment gained from fully issued weapons and armour (% of their damage and protection)")
    soldiers_per_engine: int = rule(200, 1, 100000, G, "Soldiers one unit of siege materiel serves at a siege")
    engine_breach_pct: int = rule(25, 0, 100, G, "Breach chance added by a full train of siege engines (%)")
    march_campaign_pct: int = rule(2, 0, 100, G, "Battle power an army loses per point of armour weight it drags along (%)")
    hull_guard_pct: int = rule(60, 0, 100, G, "Road danger a vessel's hull turns aside at full toughness and hardness (% of the risk)")
    hull_wear_pct: int = rule(70, 0, 100, G, "Armour a tough hull keeps when a storm or raider strikes it (% of the usual loss at full toughness)")
    fabric_light_weight: int = rule(25, 0, 100, G, "Sail or harness weight at or below which a vessel runs a stage faster")
    fabric_wind_pct: int = rule(50, 0, 100, G, "Wind risk a tough sail or harness turns aside at full toughness (% of the wind risk)")
    sanctity_undead_pct: int = rule(80, 0, 300, G, "Extra harm a weapon does to the undead per point of its material's sanctity (% of the sanctity)")
    sanctity_cursed_pct: int = rule(40, 0, 300, G, "Extra harm a weapon does to the cursed per point of its material's sanctity (% of the sanctity)")
    sanctity_void_pct: int = rule(50, 0, 300, G, "Extra harm a weapon does to beings of the void per point of its material's sanctity (% of the sanctity)")
    corruption_void_pct: int = rule(
        30, 0, 300, G, "Harm a corrupt weapon loses against beings of the void that feed on it, per point of corruption (% of the corruption)"
    )
    rust_wet_moisture: int = rule(60, 0, 100, G, "Moisture of a land from which items rust or rot by their material's decay each epoch")
    rust_decay_pct: int = rule(100, 0, 500, G, "Wear an item takes in a wet land for each step of its material's decay (% of the item-wear rule)")
    rust_decay_step: int = rule(10, 1, 100, G, "Points of a material's decay that make one step of wet-land wear")
    battle_toughness_pct: int = rule(50, 0, 100, G, "Battle wear a weapon or armour of full toughness shrugs off (%)")
    item_worth_pct: int = rule(60, 0, 300, G, "How strongly a material's rarity and base value raise the worth of an item made from it (%)")
