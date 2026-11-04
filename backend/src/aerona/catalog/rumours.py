from types import MappingProxyType

from aerona.domain.enums.culture import LegendArchetype

A = LegendArchetype
ATROCITY_KINDS = frozenset(
    {
        "captives.fates",
        "life_cycles.siege_razed",
        "life_cycles.razed_by_hand",
        "monsters.raid",
        "monsters.herd_raid",
        "war.battle.siege_breached",
        "war.battle.siege_starvation",
        "lore.infanticide",
        "lore.guest_killing",
        "lore.taboo_broken",
        "magic.dark_rite",
        "item.regalia_seized",
    }
)
ALARM_PREFIXES = ("war.outbreak", "war.battle.", "war.partisans", "war.sea_battle")
QUIET_PREFIXES = ("rumour.", "speech", "message", "system", "prayer", "engine_raw", "tools.son.message", "player.")
LEGEND_PREFIXES: MappingProxyType[str, LegendArchetype] = MappingProxyType(
    {
        "war.battle.great_victory": A.HERO_QUEST,
        "war.battle.field_victory": A.HERO_QUEST,
        "war.battle.siege_breached": A.BETRAYAL,
        "war.battle.siege_starvation": A.CURSED_LINE,
        "war.outbreak": A.BETRAYAL,
        "war.": A.HERO_QUEST,
        "monsters.": A.MONSTER,
        "life_cycles.siege_razed": A.LOST_PARADISE,
        "captives.fates": A.CURSED_LINE,
        "lore.infanticide": A.CHOSEN_ONE,
        "lore.prophecy": A.CHOSEN_ONE,
        "miracle": A.CREATION,
        "tools.son.miracle": A.CREATION,
        "disasters.flood": A.FLOOD,
        "disasters.": A.FLOOD,
        "mortal.death": A.HAUNTED_PLACE,
        "spirits.": A.HAUNTED_PLACE,
        "realm.usurp": A.RETURN_OF_THE_KING,
        "realm.succession": A.RETURN_OF_THE_KING,
        "trickster": A.TRICKSTER,
    }
)


def legend_archetype(kind: str) -> LegendArchetype:
    matches = [prefix for prefix in LEGEND_PREFIXES if kind.startswith(prefix)]
    return LEGEND_PREFIXES[max(matches, key=len)] if matches else A.HERO_QUEST


def is_atrocity(kind: str) -> bool:
    return kind in ATROCITY_KINDS


def is_alarm(kind: str) -> bool:
    return kind.startswith(ALARM_PREFIXES)


def is_quiet(kind: str) -> bool:
    return kind.startswith(QUIET_PREFIXES)
