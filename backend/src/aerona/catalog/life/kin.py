from aerona.domain.enums.cycles import KinshipDescent
from aerona.domain.enums.kin import KinRole

RAISE_ORDER = (
    KinRole.GRANDPARENT,
    KinRole.PARENT_SIBLING_FIRST_LINE,
    KinRole.PARENT_SIBLING_SECOND_LINE,
    KinRole.SIBLING,
    KinRole.GODPARENT,
    KinRole.CHOSEN_KIN,
    KinRole.SWORN_KIN,
)


LINE_ROLES = {KinshipDescent.THROUGH_FIRST_LINE: KinRole.PARENT_SIBLING_FIRST_LINE, KinshipDescent.THROUGH_SECOND_LINE: KinRole.PARENT_SIBLING_SECOND_LINE}


AVENGING = (KinRole.PARENT, KinRole.CHILD, KinRole.SIBLING, KinRole.SWORN_KIN)
