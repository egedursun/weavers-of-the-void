from types import MappingProxyType

from aerona.domain.enums.economy import WorkshopKind
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.industry import OwnerClass

W = WorkshopKind
OC = OwnerClass

OWNER_CLASS: MappingProxyType[WorkshopKind, OwnerClass] = MappingProxyType(
    {
        W.MARKET: OC.MERCHANTS,
        W.WAREHOUSE: OC.MERCHANTS,
        W.BREWERY: OC.MERCHANTS,
        W.SHIPYARD: OC.MERCHANTS,
        W.GRANARY: OC.HOUSE,
        W.MILL: OC.HOUSE,
        W.STABLE: OC.HOUSE,
        W.MINE: OC.HOUSE,
        W.LUMBER_CAMP: OC.HOUSE,
        W.FISHERY: OC.COMMUNITY,
        W.CHARCOAL_KILN: OC.GUILD,
        W.FORGE: OC.GUILD,
        W.TANNERY: OC.GUILD,
        W.WEAVERY: OC.GUILD,
        W.MASON_YARD: OC.GUILD,
        W.ALCHEMIST: OC.GUILD,
        W.SHRINE_WORKSHOP: OC.CULT,
        W.SIEGE_YARD: OC.REALM,
        W.MINT: OC.REALM,
    }
)
OWNER_LABELS: MappingProxyType[OwnerClass, str] = MappingProxyType(
    {
        OC.GUILD: "A craft guild",
        OC.MERCHANTS: "A merchant guild",
        OC.CULT: "A cult",
        OC.REALM: "The realm",
        OC.HOUSE: "A landed house",
        OC.COMMUNITY: "The community itself",
        OC.COMPANY: "A company",
        OC.INDIVIDUAL: "One owner",
        OC.COOPERATIVE: "Its own workers",
        OC.MADE_MIND: "A made mind",
        OC.FOREIGN_POWER: "A foreign power",
        OC.GOD: "A god",
    }
)
GUILD_KINDS: MappingProxyType[OwnerClass, tuple[FactionKind, ...]] = MappingProxyType(
    {OC.GUILD: (FactionKind.CRAFT_GUILD,), OC.MERCHANTS: (FactionKind.MERCHANT_GUILD, FactionKind.WANDERING_MARKET)}
)
