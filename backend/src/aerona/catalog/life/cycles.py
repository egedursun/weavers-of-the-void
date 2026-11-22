from aerona.domain.enums.cycles import KinshipDescent, ResidenceRule
from aerona.domain.enums.faction import FactionKind

RESIDENCES = {KinshipDescent.THROUGH_FIRST_LINE: ResidenceRule.WITH_FIRST_FAMILY, KinshipDescent.THROUGH_SECOND_LINE: ResidenceRule.WITH_SECOND_FAMILY}

EMPLOYER_IN_FACTION_KINDS = (FactionKind.MERCHANT_GUILD, FactionKind.CRAFT_GUILD)
LINE_FOR_KINSHIP_DESCENTS = (KinshipDescent.THROUGH_FIRST_LINE, KinshipDescent.THROUGH_SECOND_LINE)
COUSINS_FOR_KINSHIP_DESCENTS = (KinshipDescent.THROUGH_FIRST_LINE, KinshipDescent.THROUGH_SECOND_LINE)
