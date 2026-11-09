from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class TravelMethodsRules:
    ancient_gate_duration: int = rule(1, 1, 20, RuleGroup.COSMOS_AND_TRAVEL, "Ancient gate: journey duration (epochs)")
    ancient_gate_danger: int = rule(25, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Ancient gate: danger")
    space_fold_duration: int = rule(1, 1, 20, RuleGroup.COSMOS_AND_TRAVEL, "Space folding: journey duration (epochs)")
    space_fold_danger: int = rule(30, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Space folding: danger")
    light_sail_duration: int = rule(3, 1, 20, RuleGroup.COSMOS_AND_TRAVEL, "Light sail: journey duration (epochs)")
    light_sail_danger: int = rule(20, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Light sail: danger")
    cosmic_mount_duration: int = rule(2, 1, 20, RuleGroup.COSMOS_AND_TRAVEL, "Cosmic mount: journey duration (epochs)")
    cosmic_mount_danger: int = rule(35, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Cosmic mount: danger")
    dream_journey_duration: int = rule(1, 1, 20, RuleGroup.COSMOS_AND_TRAVEL, "Dream journey: journey duration (epochs)")
    dream_journey_danger: int = rule(45, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Dream journey: danger")
    river_of_dead_duration: int = rule(1, 1, 20, RuleGroup.COSMOS_AND_TRAVEL, "River of the dead: journey duration (epochs)")
    river_of_dead_danger: int = rule(40, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "River of the dead: danger")
    divine_bridge_duration: int = rule(1, 1, 20, RuleGroup.COSMOS_AND_TRAVEL, "Divine bridge: journey duration (epochs)")
    divine_bridge_danger: int = rule(10, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Divine bridge: danger")
    slingshot_orbit_duration: int = rule(2, 1, 20, RuleGroup.COSMOS_AND_TRAVEL, "Slingshot orbit: journey duration (epochs)")
    slingshot_orbit_danger: int = rule(25, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Slingshot orbit: danger")
    swallowed_duration: int = rule(2, 1, 20, RuleGroup.COSMOS_AND_TRAVEL, "Being swallowed: journey duration (epochs)")
    swallowed_danger: int = rule(60, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Being swallowed: danger")
    wormhole_duration: int = rule(1, 1, 20, RuleGroup.COSMOS_AND_TRAVEL, "Wormhole: journey duration (epochs)")
    wormhole_danger: int = rule(40, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Wormhole: danger")
    void_ark_duration: int = rule(6, 1, 100, RuleGroup.COSMOS_AND_TRAVEL, "Void ark: journey duration before its reach (epochs)")
    void_ark_danger: int = rule(25, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Void ark: danger")
    galactic_gate_duration: int = rule(1, 1, 20, RuleGroup.COSMOS_AND_TRAVEL, "Galactic gate: journey duration (epochs)")
    galactic_gate_danger: int = rule(15, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Galactic gate: danger")
    filament_lane_duration: int = rule(3, 1, 50, RuleGroup.COSMOS_AND_TRAVEL, "Filament lane: journey duration before its reach (epochs)")
    filament_lane_danger: int = rule(20, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Filament lane: danger")
    dimensional_rift_duration: int = rule(1, 1, 20, RuleGroup.COSMOS_AND_TRAVEL, "Dimensional rift: journey duration (epochs)")
    dimensional_rift_danger: int = rule(45, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Dimensional rift: danger")
    planar_door_duration: int = rule(1, 1, 20, RuleGroup.COSMOS_AND_TRAVEL, "Planar door: journey duration (epochs)")
    planar_door_danger: int = rule(20, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Planar door: danger")
    wormhole_open_pct: int = rule(60, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Wormhole: chance its throat is open in a given epoch (%)")
    bridge_collapse_loss_pct: int = rule(
        70, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Chance an expedition on a collapsing divine bridge falls into the void (%; the rest turn back)"
    )
    gate_sacrifice_pct: int = rule(
        3, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Ancient gate: share of travellers sacrificed to open the gate when nobody in the party knows its true name (%)"
    )
    gate_sacrifice_hp: int = rule(15, 0, 1000, RuleGroup.COSMOS_AND_TRAVEL, "Ancient gate: HP a lone traveller pays to open the gate without its true name")
    sail_snap_loss_pct: int = rule(
        50,
        0,
        100,
        RuleGroup.COSMOS_AND_TRAVEL,
        "Light sail: chance a journey on a sail route is lost when the star lighting the route dies (%; otherwise it is stranded)",
    )
    dream_no_return_pct: int = rule(20, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Dream journey: chance that some of the travellers never wake on arrival (%)")
    dream_no_return_share_pct: int = rule(30, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Dream journey: share of travellers whose souls never return (%)")
    dream_lone_no_return_pct: int = rule(
        10, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Dream journey: chance a lone traveller's soul never returns and the body dies (%)"
    )
    river_memory_loss_pct: int = rule(60, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "River of the dead: chance the living lose their memories on the way (%)")
    river_knowledge_loss_pct: int = rule(
        50, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "River of the dead: share of knowledge forgotten by travellers who lost their memories (%)"
    )
