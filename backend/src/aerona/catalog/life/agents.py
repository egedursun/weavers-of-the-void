from aerona.domain.enums.constructs import ContractStatus
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.polity import OathKind, OfficeKind

OPEN = (ContractStatus.POSTED, ContractStatus.TAKEN)


WAR_OFFICES = (OfficeKind.RULER, OfficeKind.MARSHAL, OfficeKind.ADMIRAL)

MORTAL_INTIMACY_LINES_OATH_KINDS = (OathKind.CELIBACY, OathKind.FIDELITY)
ESTATE_LINES_FACTION_KINDS = (FactionKind.CRAFT_GUILD, FactionKind.MERCHANT_GUILD)
