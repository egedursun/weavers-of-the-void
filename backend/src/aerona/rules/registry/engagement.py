from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

W = RuleGroup.WAR_AND_DIPLOMACY


@dataclass(frozen=True)
class EngagementRules:
    position_hits_pct: int = rule(150, 100, 500, W, "Hits a vessel lands in a round in which it holds the better position (%)")
    position_seamanship_pct: int = rule(50, 0, 200, W, "Weight of the crew's handling in the position a vessel takes (%)")
    sound_share_floor_pct: int = rule(20, 0, 100, W, "Share of its position a vessel keeps when every section it moves by is destroyed (%)")
    shield_absorb_pct: int = rule(60, 0, 100, W, "Share of energy and power hits a raised shield turns aside (%)")
    venting_crew_pct: int = rule(20, 0, 100, W, "Share of each station's crew lost when life support or an airlock vents (%)")
    breach_crew_pct: int = rule(10, 0, 100, W, "Share of each station's crew lost when a hull is breached outside water (%)")
    flooding_leak: int = rule(20, 0, 100, W, "Water a destroyed hull or keel lets in at once")
    fall_lost_pct: int = rule(60, 0, 100, W, "Chance a vessel whose lift is destroyed in the air is lost when it falls (%)")
    jettison_leak: int = rule(60, 0, 100, W, "Water at which a crew throws cargo over the side to keep its vessel afloat")
    jettison_relief: int = rule(15, 0, 100, W, "Water a jettisoned load lets the vessel shed")
    craft_hits_pct: int = rule(30, 0, 200, W, "Hits a vessel's launched craft add for each bay it fills (%)")
    ram_hits: int = rule(3, 0, 20, W, "Hull hits a ram lands when it strikes home")
    ram_recoil: int = rule(1, 0, 20, W, "Hits the ramming vessel takes on its own bow")
    board_marines_pct: int = rule(150, 100, 500, W, "Marines a vessel needs against the enemy's whole crew before it boards (%)")
    board_rounds: int = rule(3, 1, 10, W, "Rounds of close fighting a boarding lasts at most")
    board_loss_pct: int = rule(25, 0, 100, W, "Share of the weaker party lost in each round of a boarding (%)")
    officer_wound: int = rule(25, 0, 100, W, "Harm an officer takes when struck in a boarding")
    escape_position_pct: int = rule(120, 100, 500, W, "Position over its foe at which the weaker vessel breaks off at the end of a fight (%)")
    adrift_aground_pct: int = rule(20, 0, 100, W, "Chance a vessel adrift on water near a coast runs aground (%)")
