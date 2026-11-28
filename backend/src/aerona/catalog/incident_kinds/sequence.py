from collections.abc import Iterable
from types import MappingProxyType

from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS

WAR_COURSE = (
    "rumour.alarm",
    "history.anniversary",
    "war.battle.",
    "war.ended_",
    "war.weary_peace",
    "war.separate_peace",
    "war.siege.",
    "war.surrendered_by_talk",
    "war.mutiny.",
    "war.sack.",
    "war.terror",
    "war.remnant_harm",
)
AFTER_A_DEATH = (
    "death_work.",
    "death.funeral",
    "death.named",
    "gathering.wake",
    "gathering.funeral",
    "gathering.mourning",
    "mortal.mourning",
    "lifecycle.affairs_closed",
)
RITE_YEARS = 1
RUIN = ("deepened.town_ruined", "disasters.", "settlement.district_", "war.sack.", "event.sack", "refugees.ruin", "structures.ruined")
FOLLOWS: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("affairs.mandate_failed",), ("mandate.issued", "tools.mortal.mandate")),
    (("enactment.", "polity.law_enacted"), ("polity.law_proposed", "polity.law_proposed_by_need", "tools.mortal.law_proposed")),
    (("settlement.rebuilt", "settlement.left_after_ruin", "tools.mortal.rebuild", "city.planned_rebuild"), RUIN),
    (WAR_COURSE, ("war.outbreak",)),
    (("war.ended_", "war.weary_peace", "war.separate_peace", "war.surrendered_by_talk"), ("war.battle.", "war.siege.season")),
    (("speech.moved_crowd", "speech.moved_vote", "speech.offence_taken"), ("speech.given", "tools.mortal.set_speech")),
    (("faction.riot", "faction.acted", "faction.goal_met", "faction.strike", "faction.exposed"), ("faction.founded", "tools.mortal.founded_faction")),
    (
        ("expedition.delve", "expedition.discovery", "expedition.returned", "expedition.lost", "expedition.resolve"),
        ("expedition.set_out", "tools.mortal.expedition", "tools.mortal.lead_expedition", "tools.son.send_expedition"),
    ),
    (("expedition.returned", "expedition.resolve"), ("expedition.delve", "expedition.discovery")),
    (("indenture.released", "manumission."), ("indenture.bound", "indenture.contracted")),
    (
        ("travel.arrival", "travel.cargo_delivered", "travel.road.", "travel.journey_recalled", "travel.journey_vanished", "travel.sick_arrival"),
        ("travel.expedition_sent", "travel.journey", "travel.expedition_ordered"),
    ),
    (("treaty.broken",), ("treaty.misread_breach",)),
    (("war.siege.surrender", "war.surrendered_by_talk", "war.siege.relieved", "siege.", "war.battle.siege_"), ("war.siege.season",)),
    (("duel.bout", "duel.fought"), ("duel.honour", "tools.mortal.challenge_to_duel")),
    (
        ("witchcraft.hunt", "witchcraft.hunt_over"),
        ("witchcraft.accused", "witchcraft.accused_by_diviners", "witchcraft.accused_by_rumour", "tools.mortal.accuse_of_witchcraft", "hunt.accusation"),
    ),
    (
        ("art.forgery_exposed", "intrigue.exposed_forgery", "trust.forgery_found", "tools.son.expose_forgery"),
        ("arts.forged", "tools.mortal.forge_work", "tools.mortal.forge_record", "intrigue.scheme_done_forge_work", "intrigue.scheme_done_forge_letter"),
    ),
    (("condition.gained.possession", "affliction.possession"), ("afterlife.possession", "transform.possession")),
    (("oaths.wrath", "oaths.wrath_cursed", "intrigue.exposed_broken_oath"), ("oaths.broken", "oath.broken")),
    (("city.service_failed",), ("city.service_founded",)),
    (("tradition.kept_untimely",), ("tradition.slot_closed",)),
    (("death.funeral", "death.funeral_unpaid"), ("death_work.remains_treated", "death_work.exception")),
    (("daily.help_taken",), ("daily.servant_hired",)),
    (("divine.battle_hand", "divine.battle_contest"), ("war.battle.",)),
    (("divine.wound_healed",), ("divine.wound_",)),
    (("sons.rebel_theft",), ("gods.power.rebellion_declared",)),
    (("sons.covenant_lapsed",), ("divine.battle_contest", "religion.conversion")),
)


def matching(patterns: Iterable[str], keys: Iterable[str]) -> frozenset[str]:
    found = set()
    for key in keys:
        if any(key == pattern or (pattern.endswith((".", "_")) and key.startswith(pattern)) for pattern in patterns):
            found.add(key)
    return frozenset(found)


def built(keys: frozenset[str]) -> MappingProxyType[str, frozenset[str]]:
    table: dict[str, set[str]] = {}
    for effects, causes in FOLLOWS:
        before = matching(causes, keys)
        for effect in matching(effects, keys):
            table.setdefault(effect, set()).update(before - {effect})
    return MappingProxyType({key: frozenset(value) for key, value in table.items() if value})


AFTER_KINDS = built(frozenset(INCIDENT_KINDS))
SOON_AFTER_DEATH = matching(AFTER_A_DEATH, frozenset(INCIDENT_KINDS))
