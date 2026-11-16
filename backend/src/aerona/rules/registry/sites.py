from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

H = RuleGroup.HEROES_AND_MORTALS


@dataclass(frozen=True)
class SiteRules:
    challenge_pct: int = rule(55, 0, 100, H, "Chance a room of a site holds a challenge (%)")
    relic_piety: int = rule(5, 0, 100, H, "Piety a delver gains for carrying a relic out of the depths")
    difficulty_base: int = rule(25, 0, 100, H, "Difficulty of the first room of a site")
    difficulty_step: int = rule(10, 0, 100, H, "Difficulty each room deeper into a site adds")
    trap_strength: int = rule(40, 0, 100, H, "Strength of a trap laid in a room")
    room_item_pct: int = rule(35, 0, 100, H, "Chance a vault, store, armoury, library, crypt or heart holds a thing of the site (%)")
    raid_company: int = rule(4, 0, 100, H, "Raiders who walk a site beside the one who leads a feud raid on it")
    delve_skill_pct: int = rule(60, 0, 200, H, "Weight of a delver's strength and wits against a room's difficulty (%)")
    delve_company_pct: int = rule(10, 0, 100, H, "Chance each companion adds to clearing a room (%)")
    delve_hp: int = rule(20, 0, 200, H, "Harm a failed room deals the one who walks it")
    delve_renown: int = rule(4, 0, 100, H, "Renown for each room cleared")
    guardian_hp: int = rule(30, 0, 200, H, "Harm a guardian or a beast of the room deals when it wins")
    beast_wound: int = rule(30, 0, 200, H, "Harm a delver deals the beast of a room it beats")
    spirit_rest_pct: int = rule(50, 0, 100, H, "Chance a delver who clears a room lays its spirit to rest (%)")
    holder_shift: int = rule(1, 0, 1, H, "Record a new holder of a site when the one who holds it changes (1) or not (0)")


@dataclass(frozen=True)
class ExcavationRules:
    start_pct: int = rule(12, 0, 100, H, "Chance each epoch scholars nearby begin to dig an old site (%)")
    start_lore: int = rule(30, 0, 100, H, "Lore a scholar needs to lead a dig")
    open_max: int = rule(6, 0, 1000, H, "Digs open on one world at once")
    progress_base: int = rule(30, 0, 100, H, "Progress a dig makes each epoch with a leader of full skill")
    stalled_pct: int = rule(25, 0, 100, H, "Share of progress a dig still makes while it lacks the technique a stage needs (%)")
    difficulty_base: int = rule(20, 0, 100, H, "Difficulty of the first stage of a dig")
    difficulty_step: int = rule(12, 0, 100, H, "Difficulty each stage deeper adds")
    risk_pct: int = rule(30, 0, 100, H, "Chance a stage hides a risk (%)")
    find_pct: int = rule(55, 0, 100, H, "Chance a stage yields a find (%)")
    collapse_hp: int = rule(50, 0, 200, H, "Harm a collapse deals the leader of the dig")
    collapse_end_pct: int = rule(40, 0, 100, H, "Chance a collapse ends the dig for good (%)")
    abandon_after: int = rule(4, 1, 100, H, "Epochs a dig without a leader waits before it is abandoned")
    find_power: int = rule(30, 1, 100, H, "Power of a thing found in a dig")
    battlefield_dead: int = rule(500, 0, 10000000, H, "Dead a battle must leave on a battlefield to dig a mass grave there")
    grave_haunt_pct: int = rule(15, 0, 100, H, "Chance each epoch a mass grave stirs up a spirit (%)")
    salvage_take_pct: int = rule(20, 0, 100, H, "Share of a field of salvage the nearest community gleans each epoch (%)")
    feature_decay: int = rule(8, 0, 100, H, "Strength a battlefield feature loses each epoch")
