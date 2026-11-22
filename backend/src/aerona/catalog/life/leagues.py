from aerona.domain.enums.leagues import LeagueAim
from aerona.domain.enums.polity import TreatyKind

BINDING_TREATIES = (TreatyKind.COALITION, TreatyKind.INTERWORLD, TreatyKind.ALLIANCE_DEFENSIVE, TreatyKind.TRADE_PACT)


TREATY_AIMS = {
    TreatyKind.COALITION: [LeagueAim.DEFENCE],
    TreatyKind.INTERWORLD: [LeagueAim.TRADE, LeagueAim.PEACE],
    TreatyKind.ALLIANCE_DEFENSIVE: [LeagueAim.DEFENCE],
    TreatyKind.TRADE_PACT: [LeagueAim.TRADE],
}

APPLY_LEGACY_TREATY_KINDS = (TreatyKind.COALITION, TreatyKind.INTERWORLD)
