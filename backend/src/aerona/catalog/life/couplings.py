from types import MappingProxyType

from aerona.domain.enums.couplings import SociolectKind
from aerona.domain.enums.faction import FactionKind

FACTION_SPEECH = MappingProxyType(
    {
        FactionKind.MERCHANT_GUILD: SociolectKind.GUILD,
        FactionKind.CRAFT_GUILD: SociolectKind.GUILD,
        FactionKind.BANDITS: SociolectKind.CANT,
        FactionKind.PIRATES: SociolectKind.CANT,
        FactionKind.ASSASSINS: SociolectKind.CANT,
        FactionKind.CRIME_FAMILY: SociolectKind.CANT,
        FactionKind.THIEVES_GUILD: SociolectKind.CANT,
        FactionKind.ROUTE_RAIDERS: SociolectKind.CANT,
    }
)
