from dataclasses import dataclass
from math import ceil

from aerona.rules.groups import RuleGroup
from aerona.rules.model import FULL_PROGRESS, Spanned, rule, span

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
    records_strength: int = rule(30, 0, 100, H, "Weight of the records a library, shrine or laboratory of a site holds")
    flooding_pct: int = rule(10, 0, 100, H, "Chance a stage of a dig in porous rock floods (%)")
    gas_pct: int = rule(8, 0, 100, H, "Chance a stage of a dig in coal, shale or above a reservoir meets bad air (%)")
    disease_pct: int = rule(8, 0, 100, H, "Chance a stage of a dig where a sickness lies sealed or the dead lie in a mass grave lets it loose (%)")
    ordnance_harm: int = rule(10, 0, 100, H, "Dead a field of remnant arms at full strength takes each epoch from the community that crosses it")
    memorial_dead: int = rule(2000, 0, 10000000, H, "Dead a battle must leave for a memorial to be raised on its field")
    memorial_piety: int = rule(3, 0, 100, H, "Piety a memorial at full strength gives the community whose pilgrims visit it each epoch")
    remains_piety: int = rule(4, 0, 100, H, "Piety a community gains when remains found in a dig are given its funeral rites")
    holder_shift: int = rule(1, 0, 1, H, "Record a new holder of a site when the one who holds it changes (1) or not (0)")


@dataclass(frozen=True)
class ExcavationRules(Spanned):
    start_pct: int = rule(12, 0, 100, H, "Chance each epoch scholars nearby begin to dig an old site (%)")
    start_lore: int = rule(30, 0, 100, H, "Lore a scholar needs to lead a dig")
    open_max: int = rule(6, 0, 100000, H, "Base of the digs open on one world at once, grown by the number of old sites on that world")
    open_site_divisor: int = rule(3, 0, 100000, H, "Old sites on a world per extra dig open there at once (0: the cap stays at its base)")
    dig_years: int = span(5, 1, 2000, H, "Years a dig takes with a leader of full skill")
    stalled_pct: int = rule(25, 0, 100, H, "Share of progress a dig still makes while it lacks the technique a stage needs (%)")
    difficulty_base: int = rule(20, 0, 100, H, "Difficulty of the first stage of a dig")
    difficulty_step: int = rule(12, 0, 100, H, "Difficulty each stage deeper adds")
    risk_pct: int = rule(30, 0, 100, H, "Chance a stage hides a risk (%)")
    find_pct: int = rule(55, 0, 100, H, "Chance a stage yields a find (%)")
    collapse_hp: int = rule(50, 0, 200, H, "Harm a collapse deals the leader of the dig")
    collapse_end_pct: int = rule(40, 0, 100, H, "Chance a collapse ends the dig for good (%)")
    abandon_after_years: int = span(5, 1, 2500, H, "Years a dig without a leader waits before it is abandoned")
    find_power: int = rule(30, 1, 100, H, "Power of a thing found in a dig")
    battlefield_dead: int = rule(500, 0, 10000000, H, "Dead a battle must leave on a battlefield to dig a mass grave there")
    grave_haunt_pct: int = rule(15, 0, 100, H, "Chance each epoch a mass grave stirs up a spirit (%)")
    salvage_take_pct: int = rule(20, 0, 100, H, "Share of a field of salvage the nearest community gleans each epoch (%)")
    feature_decay: int = rule(8, 0, 100, H, "Strength a battlefield feature loses each epoch")

    @property
    def abandon_after(self) -> int:
        return self.epochs(self.abandon_after_years)

    @property
    def progress_base(self) -> int:
        return ceil(FULL_PROGRESS / max(1, self.epochs(self.dig_years)))
