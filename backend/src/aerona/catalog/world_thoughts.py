from types import MappingProxyType

from aerona.domain.enums.mind import ThoughtKind

T = ThoughtKind

WORLD_THOUGHTS: MappingProxyType[str, ThoughtKind] = MappingProxyType(
    {
        "monsoons.failed": T.SEASON_FAILED,
        "year.hunger": T.SEASON_FAILED,
        "event.storm": T.STORM_SURVIVED,
        "seafaring.storm": T.STORM_SURVIVED,
        "settlement.district_storm": T.STORM_SURVIVED,
        "event.earthquake": T.QUAKE_SURVIVED,
        "disasters.earthquake": T.QUAKE_SURVIVED,
        "settlement.district_earthquake": T.QUAKE_SURVIVED,
        "event.flood": T.HOME_LOST_TO_FLOOD,
        "disasters.flood": T.HOME_LOST_TO_FLOOD,
        "settlement.district_flood": T.HOME_LOST_TO_FLOOD,
        "beasts.raid": T.BEAST_PASSED,
        "beasts.risen": T.BEAST_PASSED,
        "event.plague": T.FLED_PLAGUE,
        "disease.plague_response.expel_sick": T.FLED_PLAGUE,
        "tradition.slot_closed": T.GATHERING_CLOSED,
        "dominion.throne_passed": T.SAW_ACCESSION,
        "succession.advanced": T.SAW_ACCESSION,
        "war.ended_peace": T.YEAR_OF_PEACE,
        "diplomacy.peace": T.YEAR_OF_PEACE,
        "tools.mortal.make_charm": T.CHARM_FOUND,
        "tools.son.bless_charm": T.CHARM_FOUND,
    }
)
