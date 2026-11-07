from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

W = RuleGroup.WAR_AND_DIPLOMACY


@dataclass(frozen=True)
class ArmyDepthRules:
    supply_floor: int = rule(300, 0, 100000, W, "Soldiers any region feeds from what grows wild and what can be taken")
    road_supply_pct: int = rule(130, 100, 300, W, "Supply a region with roads gives, as roads bring food from further away (%)")
    oversupply_scar: int = rule(10, 0, 100, W, "Plunder scar each season of an army above the supply limit leaves on the land")
    oversupply_resentment: int = rule(6, 0, 100, W, "Friendship the region's communities lose with the army's owner each season it eats them out")
    earthworks_at: int = rule(60, 0, 100, W, "Earthworks an army must have dug for them to stay on the land when it leaves")
    earthworks_charge_pct: int = rule(40, 0, 100, W, "Charge strength lost against a defender behind full earthworks (%)")
    earthworks_decay: int = rule(3, 0, 100, W, "Earthworks left on the land that wear away each epoch")
    earthworks_fertility_pct: int = rule(10, 0, 100, W, "Harvest lost under full earthworks (%)")
    sapper_dig_pct: int = rule(60, 0, 300, W, "Faster an entrenching army digs with enough sappers (%)")
    sapper_road_gain: int = rule(10, 0, 100, W, "Road an army's sappers lay in its region each season")
    road_at: int = rule(30, 0, 100, W, "Military road a region needs before armies march and supply along it as on a built road")
    road_decay: int = rule(1, 0, 100, W, "Military road that falls into disrepair each epoch")
    road_fertility_pct: int = rule(5, 0, 100, W, "Harvest lost under a full military road (%)")
    sappers_needed: int = rule(30, 0, 100000, W, "Sappers an army needs to bridge rivers, lay roads or blow bridges")
    bridge_down_decay: int = rule(50, 0, 100, W, "Share of a blown bridge rebuilt each epoch")
    bridge_down_fertility_pct: int = rule(0, 0, 100, W, "Harvest lost while a bridge lies blown (%)")
    sparring_injury_pct: int = rule(3, 0, 100, W, "Chance each epoch an officer of a drilling army takes a sparring injury (%)")
    sparring_hp: int = rule(6, 0, 100, W, "Harm a sparring injury deals")
    drill_discipline: int = rule(3, 0, 100, W, "Discipline a drilling stack gains each epoch, up to the drill of its army")
    patrol_pct: int = rule(40, 0, 100, W, "Share of bandit danger a garrison or entrenched army removes from the routes through its region (%)")
    standard_shock: int = rule(15, 0, 100, W, "Morale shock a side suffers when its standard is captured")
    standard_score: int = rule(1, 0, 20, W, "War score the captor of a standard gains")
    standard_renown: int = rule(5, 0, 100, W, "Renown a captured standard gains as a trophy")
    standard_capture_pct: int = rule(60, 0, 100, W, "Chance a routed or massacred side loses its standard (%)")
    template_share: int = rule(70, 0, 100, W, "Share of a raised army filled from its realm's template, the rest from its doctrine (%)")
    command_area_pct: int = rule(20, 0, 100, W, "Strength a commander lends the arm they lead best, at full skill in that area (%)")
    logistics_food_pct: int = rule(30, 0, 100, W, "Share of an army's food a commander gifted at logistics saves at full skill (%)")
