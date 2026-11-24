from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule

V = RuleGroup.CIVILIZATION
E = RuleGroup.ECONOMY
W = RuleGroup.WAR_AND_DIPLOMACY


@dataclass(frozen=True)
class WritingMediaRules(Spanned):
    rot_pct: int = rule(100, 0, 400, V, "Scale of the condition a written work loses each epoch to the damp of its land (%)")
    fire_loss: int = rule(40, 0, 100, V, "Condition a written work of a burning medium loses when fire strikes the town that keeps it")
    clay_baking: int = rule(10, 0, 100, V, "Condition a work on clay gains when fire strikes the town that keeps it")
    copy_gain: int = rule(1, 0, 100, V, "Copies a work on a medium that copies quickly gains each year")
    printing_pct: int = rule(3000, 100, 100000, V, "Scale of the copies made where printing is known (%)")
    copy_shield_pct: int = rule(
        10, 0, 1000, V, "How much each further copy of a work slows its decay (%): the decay is divided by one plus this share for every further copy"
    )
    reading_pct: int = rule(100, 0, 100, V, "Share of what a work teaches that its condition decides (%)")
    clay_tablet_durability: int = rule(90, 0, 100, V, "How well writings on clay tablets hold against damp and time (%)")
    wax_tablet_durability: int = rule(40, 0, 100, V, "How well writings on wax tablets hold against damp and time (%)")
    bark_durability: int = rule(50, 0, 100, V, "How well writings on bark hold against damp and time (%)")
    palm_leaf_durability: int = rule(40, 0, 100, V, "How well writings on palm leaves hold against damp and time (%)")
    papyrus_durability: int = rule(20, 0, 100, V, "How well writings on papyrus hold against damp and time (%)")
    parchment_durability: int = rule(80, 0, 100, V, "How well writings on parchment hold against damp and time (%)")
    paper_durability: int = rule(60, 0, 100, V, "How well writings on paper hold against damp and time (%)")
    metal_plate_durability: int = rule(100, 0, 100, V, "How well writings on metal plates hold against damp and time (%)")
    stone_durability: int = rule(100, 0, 100, V, "How well writings on stone hold against damp and time (%)")
    knotted_cord_durability: int = rule(50, 0, 100, V, "How well writings on knotted cords hold against damp and time (%)")
    calcified_tissue_durability: int = rule(90, 0, 100, V, "How well writings on bone and shell hold against damp and time (%)")
    silk_durability: int = rule(60, 0, 100, V, "How well writings on silk hold against damp and time (%)")
    wood_slips_durability: int = rule(50, 0, 100, V, "How well writings on slips of wood or cane hold against damp and time (%)")
    electronic_durability: int = rule(70, 0, 100, V, "How well writings on electronic records hold against damp and time (%)")
    outage_loss: int = rule(30, 0, 100, V, "Condition an electronic record loses each epoch its place has no working network")
    intrusion_alter_pct: int = rule(20, 0, 100, V, "Chance an intrusion into a network alters each electronic record kept there (%)")
    cloth_durability: int = rule(45, 0, 100, V, "How well writings on cloth hold against damp and time (%)")
    potsherd_durability: int = rule(85, 0, 100, V, "How well writings scratched on broken pottery hold against damp and time (%)")


@dataclass(frozen=True)
class SecurityRules:
    seed_quality: int = rule(30, 0, 100, V, "Lock quality a treasury, archive or store first takes where its people work metal")
    metal_level: int = rule(2, 0, 10, V, "Metalworking a people needs before its holders lock their stores")
    seed_guards: int = rule(
        2, 0, 10000, V, "Guards a treasury, archive or store keeps from the epoch it is first secured, before its town's people are counted"
    )
    guards_per_ten_thousand: int = rule(1, 0, 10000, V, "More guards a treasury, archive or store first keeps for every 10000 people of its town")
    smith_gain: int = rule(2, 0, 100, V, "Lock quality a master smith of the town adds each epoch")
    smith_skill: int = rule(5, 0, 10, V, "Smithing a mortal needs to improve the locks of its town")
    lock_pct: int = rule(60, 0, 100, V, "Share by which a lock of full quality thwarts a theft (%)")
    seal_pct: int = rule(30, 0, 100, V, "Chance a seal betrays a theft so that the thief is known (%)")
    guard_pct: int = rule(5, 0, 100, V, "Share of a theft each guard thwarts (%)")
    thief_pct: int = rule(8, 0, 100, V, "Share of a lock's hold each level of a thief's intrigue or deception undoes (%)")
    trap_harm: int = rule(15, 0, 100, V, "Harm a trap deals a thief who sets it off")


@dataclass(frozen=True)
class WaterLiftingRules:
    dry_below: int = rule(40, 0, 100, E, "Rainfall of a land below which its farming needs water lifted to it")
    irrigation_pct: int = rule(5, 0, 100, E, "Harvest each lifting device adds to a dry land's farms, scaled by its capacity (%)")
    irrigation_cap: int = rule(40, 0, 200, E, "Most harvest lifting devices can add to a land (%)")
    deep_from: int = rule(60, 0, 100, E, "Difficulty of a deposit from which its mine floods without pumps")
    flooded_pct: int = rule(50, 0, 100, E, "Share of its yield a deep mine without pumps loses to the water (%)")
    sanitation_gain: int = rule(2, 0, 100, E, "Sanitation each device adds to its town")
    build_chance: int = rule(20, 0, 100, E, "Chance each epoch that a town that needs water lifted builds a device it knows (%)")
    most_devices: int = rule(8, 1, 100000, E, "Most devices of one kind a town keeps, before its people are counted")
    devices_per_thousand: int = rule(1, 0, 10000, E, "More devices of one kind a town keeps for every 1000 of its people")


@dataclass(frozen=True)
class NavigationRules:
    magnetism_from: int = rule(20, 0, 100, W, "Magnetism a world needs before a compass points true there")
    seed_quality: int = rule(30, 0, 100, W, "Quality an instrument first has when the pilots of a port take it up")
    refine_skill: int = rule(5, 0, 10, W, "Navigation a mortal of a port needs to refine its instruments")
    refine_gain: int = rule(3, 0, 100, W, "Quality a skilled navigator adds to each instrument of its port each epoch")
    skill_pct: int = rule(5, 0, 100, W, "Navigation accuracy each level of the best navigator of a port adds")
    danger_pct: int = rule(40, 0, 100, W, "Share of the danger of its sea roads a fully accurate port no longer suffers (%)")
    shore_hops: int = rule(3, 1, 100, W, "Lands a sea road crosses from which it leaves sight of shore")
    open_sea_from: int = rule(50, 0, 100, W, "Accuracy from which a port's ships cross the open sea safely")
    adrift_pct: int = rule(50, 0, 400, W, "Extra danger an open-sea road suffers when neither port reaches that accuracy (%)")
    compass_loss_cut_pct: int = rule(15, 0, 100, W, "Navigation accuracy a compass of full quality adds (%)")
    astrolabe_loss_cut_pct: int = rule(15, 0, 100, W, "Navigation accuracy an astrolabe of full quality adds (%)")
    log_line_loss_cut_pct: int = rule(15, 0, 100, W, "Navigation accuracy a log-line of full quality adds (%)")
    charts_loss_cut_pct: int = rule(15, 0, 100, W, "Navigation accuracy charts of full quality adds (%)")
    sounding_line_loss_cut_pct: int = rule(10, 0, 100, W, "Navigation accuracy a sounding line of full quality adds (%)")
    wayfinding_loss_cut_pct: int = rule(15, 0, 100, W, "Navigation accuracy wayfinding lore of full quality adds (%)")
    beacons_loss_cut_pct: int = rule(15, 0, 100, W, "Navigation accuracy beacons on the shore of full quality adds (%)")
    positioning_loss_cut_pct: int = rule(30, 0, 100, W, "Navigation accuracy positioning by network of full quality adds (%)")
    beacon_works: int = rule(1, 0, 10, W, "Lighthouses or beacons a port needs on its shore to keep beacons")
    pilots_loss_cut_pct: int = rule(40, 0, 100, V, "Share of losses near a harbour that local pilots taking vessels in prevent (%)")
    buoys_loss_cut_pct: int = rule(20, 0, 100, V, "Share of losses on marked waters that buoys prevent (%)")


@dataclass(frozen=True)
class BuildingMaterialRules:
    weathering_pct: int = rule(
        100, 0, 400, V, "Scale of the decay a structure takes each epoch from the damp of its land where its material does not resist water (%)"
    )
    fire_harm: int = rule(20, 0, 100, V, "Condition a town fire takes from a structure whose material burns at the lowest heat")
    siege_pct: int = rule(40, 0, 100, V, "Share of siege harm a material of the greatest hardness turns aside (%)")


@dataclass(frozen=True)
class ContainerRules:
    made_per_skill: int = rule(2, 0, 100, E, "Containers each skilled potter or cooper of a town makes each epoch for each level of skill")
    skill_floor: int = rule(3, 0, 10, E, "Skill a potter or cooper needs to make containers")
    per_capacity: int = rule(10, 0, 1000, E, "Capacity of a trade road each container carries")
    shortage_pct: int = rule(50, 0, 100, E, "Share of its capacity a road keeps when its town lacks the containers to fill it (%)")
    breakage_pct: int = rule(5, 0, 100, E, "Share of a town's containers that break each epoch (%)")
    sealed_pct: int = rule(30, 0, 100, E, "Share of the spoilage of its stores a town with enough jars and barrels is spared (%)")
    amphora_capacity: int = rule(2, 0, 1000, E, "Goods one amphora holds, against the capacity of a trade road")
    barrel_capacity: int = rule(3, 0, 1000, E, "Goods one barrel holds, against the capacity of a trade road")
    sack_capacity: int = rule(2, 0, 1000, E, "Goods one sack holds, against the capacity of a trade road")
    crate_capacity: int = rule(3, 0, 1000, E, "Goods one crate holds, against the capacity of a trade road")
    jar_capacity: int = rule(1, 0, 1000, E, "Goods one jar holds, against the capacity of a trade road")
    chest_capacity: int = rule(2, 0, 1000, E, "Goods one chest holds, against the capacity of a trade road")
    bale_capacity: int = rule(4, 0, 1000, E, "Goods one bale holds, against the capacity of a trade road")
    basket_capacity: int = rule(2, 0, 1000, E, "Goods one basket holds, against the capacity of a trade road")
    skin_capacity: int = rule(1, 0, 1000, E, "Goods one skin holds, against the capacity of a trade road")
    tank_capacity: int = rule(10, 0, 1000, E, "Goods one tank holds, against the capacity of a trade road")
    fit_spoil_pct: int = rule(50, 0, 100, E, "Share of the loss of goods on a road spared when they travel in containers suited to them (%)")
    cage_capacity: int = rule(2, 0, 1000, E, "Goods one cage holds, against the capacity of a trade road")
    net_bag_capacity: int = rule(3, 0, 1000, E, "Goods one net bag holds, against the capacity of a trade road")
