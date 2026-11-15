from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

V = RuleGroup.CIVILIZATION
E = RuleGroup.ECONOMY
W = RuleGroup.WAR_AND_DIPLOMACY


@dataclass(frozen=True)
class WritingMediaRules:
    rot_pct: int = rule(100, 0, 400, V, "Scale of the condition a written work loses each epoch to the damp of its land (%)")
    fire_loss: int = rule(40, 0, 100, V, "Condition a written work of a burning medium loses when fire strikes the town that keeps it")
    clay_baking: int = rule(10, 0, 100, V, "Condition a work on clay gains when fire strikes the town that keeps it")
    copy_gain: int = rule(1, 0, 100, V, "Copies a work on a medium that copies quickly gains each epoch")
    printing_pct: int = rule(300, 100, 1000, V, "Scale of the copies made where printing is known (%)")
    copy_shield_pct: int = rule(10, 0, 100, V, "Share of decay each further copy of a work spares it (%)")
    reading_pct: int = rule(100, 0, 100, V, "Share of what a work teaches that its condition decides (%)")


@dataclass(frozen=True)
class SecurityRules:
    seed_quality: int = rule(30, 0, 100, V, "Lock quality a treasury, archive or store first takes where its people work metal")
    metal_level: int = rule(2, 0, 10, V, "Metalworking a people needs before its holders lock their stores")
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
    most_devices: int = rule(8, 1, 100, E, "Most devices of one kind a town keeps")


@dataclass(frozen=True)
class NavigationRules:
    magnetism_from: int = rule(20, 0, 100, W, "Magnetism a world needs before a compass points true there")
    seed_quality: int = rule(30, 0, 100, W, "Quality an instrument first has when the pilots of a port take it up")
    refine_skill: int = rule(5, 0, 10, W, "Navigation a mortal of a port needs to refine its instruments")
    refine_gain: int = rule(3, 0, 100, W, "Quality a skilled navigator adds to each instrument of its port each epoch")
    aid_pct: int = rule(15, 0, 100, W, "Navigation accuracy each instrument of full quality adds (%)")
    skill_pct: int = rule(5, 0, 100, W, "Navigation accuracy each level of the best navigator of a port adds")
    danger_pct: int = rule(40, 0, 100, W, "Share of the danger of its sea roads a fully accurate port no longer suffers (%)")
    shore_hops: int = rule(3, 1, 100, W, "Lands a sea road crosses from which it leaves sight of shore")
    open_sea_from: int = rule(50, 0, 100, W, "Accuracy from which a port's ships cross the open sea safely")
    adrift_pct: int = rule(50, 0, 400, W, "Extra danger an open-sea road suffers when neither port reaches that accuracy (%)")


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
