from collections.abc import Mapping
from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.arts import ArtMarketRole, ClubKind
from aerona.domain.enums.kind_crafts import GameCategory

ROLE_WEIGHT: Mapping[ArtMarketRole, int] = total(
    ArtMarketRole,
    {
        ArtMarketRole.COLLECTOR: 1,
        ArtMarketRole.DEALER: 2,
        ArtMarketRole.PATRON: 2,
        ArtMarketRole.CONNOISSEUR: 3,
        ArtMarketRole.CURATOR: 3,
        ArtMarketRole.CRITIC: 2,
        ArtMarketRole.FORGER: 0,
        ArtMarketRole.RESTORER: 2,
        ArtMarketRole.AUCTIONEER: 2,
    },
)


FIELD_GAMES = MappingProxyType(
    {
        GameCategory.BALL: ClubKind.TEAM_GAME,
        GameCategory.TEAM: ClubKind.TEAM_GAME,
        GameCategory.RACING: ClubKind.RACING,
        GameCategory.COMBAT_SPORT: ClubKind.COMBAT,
        GameCategory.ATHLETIC: ClubKind.ATHLETICS,
        GameCategory.BOARD: ClubKind.MIND_GAMES,
        GameCategory.WIT: ClubKind.MIND_GAMES,
    }
)
