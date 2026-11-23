from aerona.core.total import total
from aerona.domain.enums.faction import MovementCause
from aerona.domain.enums.referendums import ReferendumSubject

PETITIONS = total(
    MovementCause,
    {
        MovementCause.ABOLITION: None,
        MovementCause.INDEPENDENCE: ReferendumSubject.INDEPENDENCE,
        MovementCause.REVIVAL: ReferendumSubject.FAITH,
        MovementCause.LAND_REFORM: None,
        MovementCause.FRANCHISE: ReferendumSubject.CONSTITUTION,
        MovementCause.PEACE: ReferendumSubject.WAR,
        MovementCause.CONSERVATION: None,
        MovementCause.LABOUR: ReferendumSubject.LAW,
        MovementCause.FAITH_REFORM: ReferendumSubject.FAITH,
        MovementCause.TEMPERANCE: ReferendumSubject.LAW,
        MovementCause.MIND_RIGHTS: ReferendumSubject.LAW,
        MovementCause.EQUAL_STANDING: ReferendumSubject.CONSTITUTION,
    },
)
