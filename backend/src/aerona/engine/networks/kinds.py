from collections.abc import Mapping

from aerona.core.total import total
from aerona.domain.enums.made import DataContent
from aerona.domain.enums.networks import NetworkAccess

ACCESS_REACH: Mapping[NetworkAccess, int] = total(
    NetworkAccess,
    {NetworkAccess.CLOSED: 50, NetworkAccess.MEMBERS: 100, NetworkAccess.LICENSED: 120, NetworkAccess.OPEN: 150},
)
ACCESS_GUARD: Mapping[NetworkAccess, int] = total(
    NetworkAccess,
    {NetworkAccess.CLOSED: 25, NetworkAccess.MEMBERS: 10, NetworkAccess.LICENSED: 5, NetworkAccess.OPEN: 0},
)
TAKEN_CONTENT = frozenset(DataContent)
