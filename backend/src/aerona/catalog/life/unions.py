from collections.abc import Mapping

from aerona.core.total import total
from aerona.domain.enums.cycles import KinshipDescent
from aerona.domain.enums.unions import UnionDescent

DESCENT_OF: Mapping[KinshipDescent, UnionDescent] = total(
    KinshipDescent,
    {
        KinshipDescent.THROUGH_FIRST_LINE: UnionDescent.THROUGH_FIRST,
        KinshipDescent.THROUGH_SECOND_LINE: UnionDescent.THROUGH_SECOND,
        KinshipDescent.BILATERAL: UnionDescent.THROUGH_BOTH,
        KinshipDescent.DOUBLE: UnionDescent.THROUGH_BOTH,
        KinshipDescent.AMBILINEAL: UnionDescent.CHOSEN,
    },
)
