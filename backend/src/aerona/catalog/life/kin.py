from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.cycles import KinshipDescent
from aerona.domain.enums.kin import KinRole

R = KinRole


@dataclass(frozen=True)
class KinRoleSpec:
    label: str
    close: bool = False
    extended: bool = False
    avenges: bool = False
    raises: int | None = None


KIN_ROLES: Mapping[KinRole, KinRoleSpec] = total(
    KinRole,
    {
        R.PARENT: KinRoleSpec("Parent", close=True, extended=True, avenges=True),
        R.CHILD: KinRoleSpec("Child", close=True, extended=True, avenges=True),
        R.SIBLING: KinRoleSpec("Sibling", close=True, extended=True, avenges=True, raises=3),
        R.GRANDPARENT: KinRoleSpec("Grandparent", extended=True, raises=0),
        R.GRANDCHILD: KinRoleSpec("Grandchild", extended=True),
        R.PARENT_SIBLING_FIRST_LINE: KinRoleSpec("Parent's sibling of the first line", extended=True, raises=1),
        R.PARENT_SIBLING_SECOND_LINE: KinRoleSpec("Parent's sibling of the second line", extended=True, raises=2),
        R.SIBLING_CHILD: KinRoleSpec("Sibling's child", extended=True),
        R.COUSIN_PARALLEL: KinRoleSpec("Parallel cousin", extended=True),
        R.COUSIN_CROSS: KinRoleSpec("Cross cousin", extended=True),
        R.PARENT_IN_LAW: KinRoleSpec("Parent by marriage"),
        R.CHILD_IN_LAW: KinRoleSpec("Child by marriage"),
        R.SIBLING_IN_LAW: KinRoleSpec("Sibling by marriage"),
        R.CO_SPOUSE: KinRoleSpec("Co-spouse"),
        R.CHOSEN_KIN: KinRoleSpec("Chosen kin", raises=5),
        R.GODPARENT: KinRoleSpec("Godparent", raises=4),
        R.SWORN_KIN: KinRoleSpec("Sworn kin", avenges=True, raises=6),
        R.FOSTER_KIN: KinRoleSpec("Foster kin", avenges=True, raises=7),
    },
)
RAISE_ORDER = tuple(
    role for role, spec in sorted(((role, spec) for role, spec in KIN_ROLES.items() if spec.raises is not None), key=lambda item: item[1].raises or 0)
)
AVENGING = tuple(role for role, spec in KIN_ROLES.items() if spec.avenges)
LINE_ROLES = {KinshipDescent.THROUGH_FIRST_LINE: R.PARENT_SIBLING_FIRST_LINE, KinshipDescent.THROUGH_SECOND_LINE: R.PARENT_SIBLING_SECOND_LINE}
