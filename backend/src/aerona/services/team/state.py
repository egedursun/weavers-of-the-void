import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from aerona.services.accounts.guard import GrantedAccess
from aerona.services.team.presence import Roster

GrantResolver = Callable[[int], Awaitable[GrantedAccess | None]]


@dataclass
class TeamState:
    roster: Roster = field(default_factory=Roster)
    applying: asyncio.Lock = field(default_factory=asyncio.Lock)
    grant_of: GrantResolver | None = None
