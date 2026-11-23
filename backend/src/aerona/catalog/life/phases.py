from collections.abc import Mapping
from types import MappingProxyType

from aerona.catalog.grief import OPEN_GRIEF_STAGES
from aerona.catalog.war_w52 import PEACE_OPERATIONS as PEACE_SET
from aerona.catalog.war_w52 import WAR_OPERATIONS as WAR_SET
from aerona.core.total import total
from aerona.domain.enums.civilization import TierCapability
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.military import CasualtyFate, DuelEnd, SackChoice
from aerona.domain.enums.mind import MemoryKind, SkillKind
from aerona.domain.enums.polity import TreatyKind
from aerona.domain.enums.travel import JourneyIntent, RouteState
from aerona.domain.enums.war import CaptiveStatus, WarEnding

WAR_OPERATIONS = WAR_SET


PEACE_OPERATIONS = PEACE_SET


VENGEFUL_MEMORIES = (MemoryKind.KILLED_KIN, MemoryKind.MAIMED_ME)


EXPLORER_SKILLS = (SkillKind.TRACKING, SkillKind.NAVIGATION, SkillKind.MOUNTAINEERING)


SEER_SKILLS = (SkillKind.PROPHECY, SkillKind.SPIRIT_SPEAKING, SkillKind.LORE)


LOST_REASONS: dict[RouteState, str] = {
    RouteState.FORGOTTEN: "the world at the end of the route was forgotten",
    RouteState.COLLAPSED: "the divine bridge collapsed",
    RouteState.SEALED: "the route was sealed",
    RouteState.SNAPPED: "the light sail snapped",
    RouteState.SEVERED: "the route was severed for good",
    RouteState.WORN: "the route wore away",
    RouteState.SCORCHED: "a flare scorched the route shut for good",
}


GRIEF = (MemoryKind.KILLED_KIN, MemoryKind.MAIMED_ME)


INSULTS = (MemoryKind.HUMILIATED_ME, MemoryKind.HARMED_ME, MemoryKind.BETRAYED_ME, MemoryKind.MAIMED_ME, MemoryKind.KILLED_KIN)


DUEL_FATES: Mapping[DuelEnd, CasualtyFate] = total(
    DuelEnd,
    {
        DuelEnd.YIELD: CasualtyFate.WOUNDED,
        DuelEnd.DISARM: CasualtyFate.WOUNDED,
        DuelEnd.CRIPPLED: CasualtyFate.MAIMED,
        DuelEnd.DEATH: CasualtyFate.KILLED,
        DuelEnd.EXHAUSTION: CasualtyFate.WOUNDED,
        DuelEnd.UNCONSCIOUS: CasualtyFate.WOUNDED,
        DuelEnd.FIRST_WOUND: CasualtyFate.WOUNDED,
        DuelEnd.RING_OUT: CasualtyFate.WOUNDED,
    },
)


DUEL_ENDINGS: Mapping[DuelEnd, str] = total(
    DuelEnd,
    {
        DuelEnd.YIELD: "{loser} yielded",
        DuelEnd.DISARM: "{loser} lost the weapon and yielded",
        DuelEnd.CRIPPLED: "{loser} was crippled",
        DuelEnd.DEATH: "{loser} died",
        DuelEnd.EXHAUSTION: "both were spent and {winner} stood the steadier",
        DuelEnd.UNCONSCIOUS: "{loser} lost consciousness",
        DuelEnd.FIRST_WOUND: "{loser} took the first wound and the duel ended there",
        DuelEnd.RING_OUT: "{loser} was driven beyond the marked bounds",
    },
)

BASE_STATS_FACTION_KINDS = frozenset({FactionKind.MERCHANT_GUILD, FactionKind.CRAFT_GUILD, FactionKind.WANDERING_MARKET})
BASE_STATS_FACTION_KINDS_2 = frozenset(
    {FactionKind.PRIESTHOOD, FactionKind.SCHOLARS_ACADEMY, FactionKind.SECRET_SOCIETY, FactionKind.NOBLE_COUNCIL, FactionKind.SOCIAL_CIRCLE}
)
MIND_GRIEF_GRIEF_STAGES = OPEN_GRIEF_STAGES
PRISONERS_CAPTIVE_STATUSS = (CaptiveStatus.HELD, CaptiveStatus.WARD)
SEND_SPONTANEOUSLY_JOURNEY_INTENTS = (JourneyIntent.COLONY, JourneyIntent.CONQUEST, JourneyIntent.EXILE, JourneyIntent.FLIGHT)
ARRIVE_JOURNEY_INTENTS = (JourneyIntent.EXPLORATION, JourneyIntent.PILGRIMAGE)
ARRIVE_JOURNEY_INTENTS_2 = (JourneyIntent.COLONY, JourneyIntent.CONQUEST, JourneyIntent.EXILE, JourneyIntent.FLIGHT)
TRIBUTE_TREATY_KINDS = (TreatyKind.TRIBUTE, TreatyKind.VASSALAGE)
SACKED_SACK_CHOICES = frozenset({SackChoice.SACK, SackChoice.RAZE})
END_WAR_BY_DECREE_WAR_ENDINGS = (WarEnding.VICTORY, WarEnding.CONQUEST, WarEnding.TRIBUTE)

INTENT_CAPABILITY = MappingProxyType({JourneyIntent.COLONY: TierCapability.COLONY, JourneyIntent.CONQUEST: TierCapability.CONQUEST})
