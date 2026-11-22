from aerona.domain.enums.intimacy import BirthComplication, RelationContext
from aerona.domain.enums.kin import KinRole
from aerona.domain.enums.mind import ActKind, ValueAxis

SINGLE_COMPLICATIONS = (BirthComplication.POSITION, BirthComplication.BLEEDING, BirthComplication.FEVER, BirthComplication.EARLY, BirthComplication.LATE)


CLOSE_KIN = (KinRole.PARENT, KinRole.CHILD, KinRole.SIBLING)


STRICT_AXES = (ValueAxis.TRADITION, ValueAxis.PIETY, ValueAxis.HONOUR)


ACT_CONTEXTS = {ActKind.ADULTERY: RelationContext.OUTSIDE_UNION, ActKind.INCEST: RelationContext.WITH_KIN}

EXTENDED_KIN = (
    *CLOSE_KIN,
    KinRole.GRANDPARENT,
    KinRole.GRANDCHILD,
    KinRole.PARENT_SIBLING_FIRST_LINE,
    KinRole.PARENT_SIBLING_SECOND_LINE,
    KinRole.SIBLING_CHILD,
    KinRole.COUSIN_PARALLEL,
    KinRole.COUSIN_CROSS,
)
