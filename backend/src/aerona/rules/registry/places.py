from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

G = RuleGroup.EXPLORATION


@dataclass(frozen=True)
class PlacesRules:
    sacred_holy_base: int = rule(60, 0, 100, G, "Sacredness a holy kind of place (shrine site, nexus, place where a god died, burial ground) tends toward")
    sacred_notable_base: int = rule(25, 0, 100, G, "Sacredness a notable kind of place (spring, grove, peak, well, volcano) tends toward")
    sacred_profane_base: int = rule(0, 0, 100, G, "Sacredness an ordinary kind of place tends toward")
    sacred_per_temple: int = rule(15, 0, 100, G, "Sacredness each standing temple at a place adds")
    sacred_per_relic: int = rule(10, 0, 100, G, "Sacredness each saint's relic enshrined at a place adds")
    sacred_pilgrimage_site: int = rule(20, 0, 100, G, "Sacredness a declared pilgrimage site adds")
    sacred_nexus: int = rule(15, 0, 100, G, "Sacredness a ley nexus adds")
    sacred_drift: int = rule(5, 0, 100, G, "How far a place's sacredness moves toward what its kind, temples and relics make it each epoch")
    holy_site_threshold: int = rule(50, 0, 100, G, "Sacredness at which a place counts as a holy site for pilgrims and pilgrimage duties")
    pilgrimage_threshold: int = rule(40, 0, 100, G, "Sacredness at which a place draws pilgrims from its region each epoch")
    pilgrim_share_permille: int = rule(20, 0, 1000, G, "Pilgrims a sacred place draws per thousand people of its region at full sacredness")
    pilgrim_piety: int = rule(2, 0, 100, G, "Piety a community gains each epoch it sends pilgrims to a sacred place")
    pilgrim_prosperity: int = rule(2, 0, 100, G, "Prosperity a community standing at a sacred place gains from pilgrims each epoch")
    secret_chance_pct: int = rule(40, 0, 100, G, "Chance at full mystery that a place hides a secret when it is first surveyed (%)")
    woken_stability: int = rule(15, 0, 100, G, "Stability a sleeping mind gains when it is found and woken")
    secret_strength_min: int = rule(20, 0, 100, G, "Least strength of a secret the land hides")
    secret_strength_die: int = rule(60, 1, 100, G, "Strength swing of a secret the land hides")
    discover_base_pct: int = rule(2, 0, 100, G, "Base chance per epoch that a searcher finds a place's secret (%)")
    discover_skill_pct: int = rule(20, 0, 100, G, "Chance a master searcher adds to finding a secret (% at skill 100)")
    discover_mystery_pct: int = rule(10, 0, 100, G, "Chance a place of full mystery adds to finding its secret (%)")
    discover_strength_pct: int = rule(15, 0, 100, G, "Chance a secret of full strength takes away from finding it (%)")
    discover_role_pct: int = rule(10, 0, 100, G, "Chance an explorer or seer adds by calling alone (%)")
    discover_cap_pct: int = rule(40, 0, 100, G, "Highest chance per epoch that one searcher finds a secret (%)")
    miner_mined_min: int = rule(20, 0, 100, G, "Mined share of a region from which its miners dig into the secrets of its deep places")
    miner_pct: int = rule(30, 0, 100, G, "Chance per epoch at a fully mined region that miners strike a deep place's secret (%)")
    release_pct: int = rule(25, 0, 100, G, "Chance per epoch at a fully mined region that miners breach a known sealed thing (%)")
    released_unrest: int = rule(70, 0, 100, G, "Unrest of a spirit released from its seal")
    haunted_depth: int = rule(30, 0, 100, G, "Depth of the haunting a released spirit or opened way below leaves on its region")
    entrance_danger: int = rule(15, 0, 100, G, "Danger an opened way to the underworld adds to its place")
    relic_curse_pct: int = rule(30, 0, 100, G, "Chance a buried relic carries a curse (%)")
    relic_power: int = rule(3, 1, 12, G, "Power level of a relic dug from a place")
    knowledge_level: int = rule(2, 1, 10, G, "Level of lost knowledge found in a place")
    knowledge_power: int = rule(2, 1, 12, G, "Power level of lost knowledge found in a place")
    resource_power: int = rule(2, 1, 12, G, "Power level of a resource found in a place")
    spirit_power: int = rule(3, 1, 12, G, "Power level of a spirit released from a place")
    chokepoint_battle_pct: int = rule(35, 0, 100, G, "Chance a campaign season's battle is drawn to a chokepoint or pass of the defender's region (%)")
    battlefield_battles: int = rule(3, 1, 100, G, "Recorded battles that turn a valley or crossroads into a battlefield")
    wreck_site_wrecks: int = rule(
        2, 1, 100, G, "Wrecks lying in a land that turn its waterside place into a wreck site, or its open ground into a debris field in the void"
    )
    cover_missile_light_pct: int = rule(85, 0, 100, G, "Share of missile harm that reaches troops in light cover (%)")
    cover_missile_heavy_pct: int = rule(65, 0, 100, G, "Share of missile harm that reaches troops in heavy cover such as forests and ruins (%)")
    cover_defender_light_pct: int = rule(3, 0, 100, G, "Defence bonus of holding ground with light cover (%)")
    cover_defender_heavy_pct: int = rule(8, 0, 100, G, "Defence bonus of holding ground with heavy cover such as forests and ruins (%)")
    hide_secret_essence: int = rule(15, 0, 1000, G, "Essence a son spends to hide a secret in a place")
    sanctify_essence: int = rule(10, 0, 1000, G, "Essence a son spends to sanctify a place")
    sanctify_amount: int = rule(30, 0, 100, G, "Sacredness a son's sanctification adds to a place")
    raise_nexus_essence: int = rule(25, 0, 1000, G, "Essence a son spends to raise a ley nexus at a place")
