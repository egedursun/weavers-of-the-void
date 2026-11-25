from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

from aerona.db.session import Database
from aerona.db.tables.divine_will import DivineWillCycleRow, DivineWillSessionRow
from aerona.domain.enums.divine_will import CycleStatus, DivineWillMode
from aerona.domain.enums.world import LoreLanguage
from aerona.events.bus import EventBus
from aerona.jobs.manager import JobManager
from aerona.prompts.tools.divine_will_ids import DivineWillToolId
from aerona.rules.registry import Rules
from aerona.services.container import Services
from aerona.services.discovery import DiscoveryService
from aerona.services.divine_will.player import CatalogPlayer
from aerona.services.ledger import Ledger
from aerona.services.player.runtime import PlayerRuntime
from aerona.services.rules import RulesService
from aerona.settings import Settings
from aerona.tools.divine_will.catalogue import tool_by_name
from aerona.tools.divine_will.framework import WillCall, WillResult, invoke
from tests.tools.divine_will_case import HOST_PARTS, WillCase, WillWorld
from tests.tools.divine_will_cases_library import LIBRARY_CASES
from tests.tools.divine_will_cases_read import READ_CASES
from tests.tools.divine_will_cases_retrieval import RETRIEVAL_CASES
from tests.tools.factories import EPOCH, seed_realm

WILL_CASES: dict[DivineWillToolId, WillCase] = {**READ_CASES, **RETRIEVAL_CASES, **LIBRARY_CASES}


@dataclass
class HarnessApplication:
    ledger: Ledger
    discovery: DiscoveryService


@dataclass
class HarnessServices:
    database: Database
    jobs: JobManager
    rules: RulesService
    application: HarnessApplication
    player: PlayerRuntime


def harness_player(database: Database, folder: Path, jobs: JobManager | None = None) -> CatalogPlayer:
    bus = EventBus()
    jobs = jobs or JobManager(database, bus)
    settings = Settings(data_dir=folder, llm_enabled=False, image_worker_url="")
    application = HarnessApplication(Ledger(bus), DiscoveryService(settings))
    host = HarnessServices(database, jobs, RulesService(database), application, PlayerRuntime(database, jobs, bus))
    return CatalogPlayer(cast(Services, host))


async def will_world(database: Database, mode: DivineWillMode = DivineWillMode.COMMAND) -> WillWorld:
    realm = await seed_realm(database)
    async with database.write() as session:
        opened = DivineWillSessionRow(opened_epoch=EPOCH, title="")
        session.add(opened)
        await session.flush()
        cycle = DivineWillCycleRow(session_id=opened.id, ordinal=1, mode=mode, epoch=EPOCH, status=CycleStatus.RUNNING, player_text="")
        session.add(cycle)
        await session.flush()
        return WillWorld(realm, opened.id, cycle.id)


def will_call(
    database: Database, world: WillWorld, mode: DivineWillMode, folder: Path, *, rules: Rules | None = None, player: CatalogPlayer | None = None
) -> WillCall:
    host = SimpleNamespace(**{name: part(database) for name, part in HOST_PARTS.items()})
    return WillCall(
        database,
        rules or Rules(),
        cycle_id=world.cycle_id,
        session_id=world.session_id,
        epoch=EPOCH,
        mode=mode,
        lore_language=LoreLanguage.ENGLISH.value,
        player=player or harness_player(database, folder),
        services=host,
    )


async def call_tool(call: WillCall, tool: DivineWillToolId, arguments: dict[str, Any]) -> WillResult:
    found = tool_by_name(tool.value)
    assert found is not None, f"{tool} is not registered"
    return await invoke(call, found, arguments)


async def run_will_case(database: Database, tool: DivineWillToolId, case: WillCase, folder: Path) -> WillResult:
    world = await will_world(database, case.mode)
    async with database.write() as session:
        world.ids.update(await case.setup(session, world))
    call = will_call(database, world, case.mode, folder)
    for step in case.prelude:
        before = await call_tool(call, step.tool, step.arguments(world))
        assert not before.is_error, f"prelude {step.tool}: {before.text}"
        world.handles.append(before.handle)
    return await call_tool(call, tool, case.arguments(world))
