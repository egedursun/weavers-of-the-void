from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.session import Database
from aerona.domain.enums.divine_will import DivineWillMode
from aerona.prompts.tools.divine_will_ids import DivineWillToolId
from aerona.services.divine_will_reads import ActionDesk, LoreReads
from tests.tools.divine_will_library_host import harness_library
from tests.tools.divine_will_media import harness_index, harness_media
from tests.tools.divine_will_rules import harness_rule_desk
from tests.tools.factories import Realm


@dataclass
class WillWorld:
    realm: Realm
    session_id: int
    cycle_id: int
    ids: dict[str, int] = field(default_factory=dict)
    handles: list[str] = field(default_factory=list)


WillSetup = Callable[[AsyncSession, WillWorld], Awaitable[dict[str, int]]]
WillArguments = Callable[[WillWorld], dict[str, Any]]
HostPart = Callable[[Database], Any]


async def no_setup(_session: AsyncSession, _world: WillWorld) -> dict[str, int]:
    return {}


def no_arguments(_world: WillWorld) -> dict[str, Any]:
    return {}


@dataclass(frozen=True)
class WillStep:
    tool: DivineWillToolId
    arguments: WillArguments = no_arguments


@dataclass(frozen=True)
class WillCase:
    arguments: WillArguments = no_arguments
    setup: WillSetup = no_setup
    mode: DivineWillMode = DivineWillMode.COMMAND
    prelude: tuple[WillStep, ...] = ()
    expect: tuple[str, ...] = ()
    pause: bool = False


HOST_PARTS: dict[str, HostPart] = {
    "lore_reads": lambda _database: LoreReads(),
    "action_desk": lambda _database: ActionDesk(),
    "lore_index": harness_index,
    "attachment_store": harness_media,
    "library": harness_library,
    "rule_desk": harness_rule_desk,
}
