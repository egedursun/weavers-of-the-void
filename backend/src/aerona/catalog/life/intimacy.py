from aerona.catalog.life.kin import KIN_ROLES
from aerona.domain.enums.intimacy import BirthComplication, RelationContext
from aerona.domain.enums.mind import ActKind, ValueAxis

SINGLE_COMPLICATIONS = (BirthComplication.POSITION, BirthComplication.BLEEDING, BirthComplication.FEVER, BirthComplication.EARLY, BirthComplication.LATE)


CLOSE_KIN = tuple(role for role, spec in KIN_ROLES.items() if spec.close)


STRICT_AXES = (ValueAxis.TRADITION, ValueAxis.PIETY, ValueAxis.HONOUR)


ACT_CONTEXTS = {ActKind.ADULTERY: RelationContext.OUTSIDE_UNION, ActKind.INCEST: RelationContext.WITH_KIN}

EXTENDED_KIN = tuple(role for role, spec in KIN_ROLES.items() if spec.extended)
