import argparse
import asyncio
import logging
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import traceback
from collections import Counter
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select, update

from aerona.agents.mortal import mortal_prompts, start_mortal_turn
from aerona.agents.runtime import AgentRuntime
from aerona.agents.son import prepare_prompts, son_toolkit, start_turn
from aerona.agents.tool_ports import attach_toolkits
from aerona.constants.paths import DATABASE_FILENAME
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.migrations import upgrade_to_head_sync
from aerona.db.session import Database
from aerona.db.tables.celestial import StarRow
from aerona.db.tables.cosmography import GalaxyRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mythic import CosmicOfficeRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.son import SonStatus
from aerona.engine.pipeline import simulate
from aerona.engine.primitives.manual import manual_context
from aerona.main import create_app
from aerona.settings import Settings
from aerona.tools.toolkit import Toolkits, TurnToolkit
from tests.agents.fakes import FakeModel
from tests.api.test_every_endpoint import FIXED, GET_PATHS, NAMED_TABLES, PARAM, SECOND
from tests.services.player.every_lever import kind_of, payload_for, pick
from tests.tools import factories
from tests.tools import test_every_tool as proof
from tests.tools.every_mortal_tool import MORTAL_CASES
from tests.tools.every_son_tool import SON_CASES

PROMPT_ROUNDS = 1
TOOL_VARIANTS = 3
TOOL_POINTS = 999
ENDPOINT_SAMPLES = 6


class Crashes(logging.Handler):
    def __init__(self, message: str | None) -> None:
        super().__init__()
        self.message = message
        self.found: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        if record.exc_info and (self.message is None or record.getMessage() == self.message):
            self.found.append("".join(traceback.format_exception(*record.exc_info)[-6:]))


def watch(message: str | None = None) -> Crashes:
    crashes = Crashes(message)
    logging.getLogger("aerona").addHandler(crashes)
    return crashes


def snapshot(source: Path, folder: Path) -> Path:
    target = folder / "world.db"
    with sqlite3.connect(f"file:{source}?mode=ro", uri=True) as reader, sqlite3.connect(target) as writer:
        reader.backup(writer)
    upgrade_to_head_sync(f"sqlite+aiosqlite:///{target}")
    return target


def clone(source: Path, target: Path) -> Path:
    subprocess.run(["cp", "-c", str(source), str(target)], check=True)
    return target


def toolkits_of(runtime: AgentRuntime) -> Toolkits:
    assert isinstance(runtime.toolkits, Toolkits)
    return runtime.toolkits


def opened(path: Path) -> Database:
    return Database(f"sqlite+aiosqlite:///{path}")


async def open_turns(path: Path) -> None:
    database = opened(path)
    async with database.write() as session:
        await session.execute(update(SonRow).values(last_acted_epoch=0))
        await session.execute(update(EntityRow).values(last_acted_epoch=0))
    await database.dispose()


async def prompts(path: Path) -> int:
    database = opened(path)
    runtime = attach_toolkits(AgentRuntime(database=database, model=FakeModel(), publish=lambda *_: None))
    async with database.read() as session:
        sons = list(await session.scalars(select(SonRow.id).where(SonRow.status == SonStatus.ACTIVE, SonRow.chained.is_(False)).order_by(SonRow.id)))
        mortals = list(
            await session.scalars(
                select(EntityRow.id).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
            )
        )
    failures: list[str] = []
    for son_id in sons:
        try:
            started = await start_turn(runtime, son_id)
            prepared = await prepare_prompts(runtime, started, (await son_toolkit(runtime, started)).catalogue)
            assert prepared.system_prompt and prepared.prompt
        except Exception:
            failures.append(f"son {son_id}: {traceback.format_exc(limit=8)}")
    for entity_id in mortals:
        try:
            mortal_turn = await start_mortal_turn(runtime, entity_id)
            toolkit = await toolkits_of(runtime).mortal_toolkit(entity_id, mortal_turn.epoch, mortal_turn.action_points)
            system, prompt = await mortal_prompts(runtime, mortal_turn, toolkit.catalogue)
            assert system and prompt
        except Exception:
            failures.append(f"mortal {entity_id}: {traceback.format_exc(limit=8)}")
    await database.dispose()
    print(f"prompts: {len(sons)} sons, {len(mortals)} mortals, {len(failures)} failures")
    for item in failures:
        print(item)
    return 1 if failures else 0


async def engine(path: Path, epochs: int) -> int:
    database = opened(path)
    started = time.monotonic()
    try:
        runs = await simulate(database, epochs)
        print(f"engine: lived {len(runs)} epochs in {time.monotonic() - started:.0f}s")
        return 0
    except Exception:
        print(f"engine: failed after {time.monotonic() - started:.0f}s\n{traceback.format_exc()}")
        return 1
    finally:
        await database.dispose()


async def endpoints(path: Path, folder: Path) -> int:

    data = folder / "data"
    data.mkdir(parents=True, exist_ok=True)
    clone(path, data / DATABASE_FILENAME)
    app = create_app(Settings(data_dir=data, llm_enabled=False, image_worker_url=""))
    broken: list[str] = []
    checked = 0

    async def filled(services: Any, route: str, skip: int) -> str | None:
        values: dict[str, Any] = {}
        async with services.database.read() as session:
            for name in PARAM.findall(route):
                if name in FIXED:
                    values[name] = FIXED[name]
                    continue
                found = await pick(session, kind_of("mortal_id" if name in SECOND else NAMED_TABLES.get(name, name)), skip + (1 if name in SECOND else 0))
                if found is None:
                    return None
                values[name] = found
        return PARAM.sub(lambda match: str(values[match.group(1)]), route)

    async with (
        LifespanManager(app, startup_timeout=300, shutdown_timeout=120) as manager,
        AsyncClient(transport=ASGITransport(app=manager.app), base_url="http://localhost", timeout=300) as http,
    ):
        for route in GET_PATHS:
            urls = {await filled(app.state.services, route, skip) for skip in range(ENDPOINT_SAMPLES if PARAM.search(route) else 1)}
            for url in sorted(url for url in urls if url is not None):
                checked += 1
                response = await http.get(url)
                if response.status_code >= 500:
                    broken.append(f"{url}: {response.status_code} {response.text[:400]}")
    print(f"endpoints: {checked} reads over {len(GET_PATHS)} routes, {len(broken)} broken")
    for item in broken:
        print(item)
    return 1 if broken else 0


async def tools(path: Path) -> int:
    crashes = watch("tool call failed")
    database = opened(path)
    runtime = attach_toolkits(AgentRuntime(database=database, model=FakeModel(), publish=lambda *_: None))
    async with database.read() as session:
        epoch = (await manual_context(session, "lived_world")).epoch
        sons = list(await session.scalars(select(SonRow.id).where(SonRow.status == SonStatus.ACTIVE).order_by(SonRow.id)))
        mortals = list(
            await session.scalars(
                select(EntityRow.id).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
            )
        )
    tally: Counter[str] = Counter()
    offered: set[str] = set()
    won: set[str] = set()
    broken: list[str] = []
    kits = toolkits_of(runtime)
    actors: list[tuple[str, Callable[[int, int, int], Awaitable[TurnToolkit]], int]] = [(f"son {son_id}", kits.son_toolkit, son_id) for son_id in sons]
    actors += [(f"mortal {entity_id}", kits.mortal_toolkit, entity_id) for entity_id in mortals]
    for actor, make, node_id in actors:
        toolkit = await make(node_id, epoch, TOOL_POINTS)
        for spec in list(toolkit.runtime.specs):
            offered.add(spec.name)
            for variant in range(TOOL_VARIANTS):
                async with database.read() as session:
                    try:
                        arguments = await payload_for(session, spec.input_model, {}, variant)
                    except Exception:
                        tally["unfillable"] += 1
                        continue
                before = len(crashes.found)
                try:
                    outcome = await toolkit.runtime.call(spec.name, arguments)
                except Exception:
                    broken.append(f"{actor} {spec.name} raised out of the runtime: {traceback.format_exc(limit=6)}")
                    tally["raised"] += 1
                    continue
                if len(crashes.found) > before:
                    broken.append(f"{actor} {spec.name} {arguments}: {crashes.found[-1]}")
                    tally["crashed"] += 1
                elif outcome.is_error:
                    tally["refused"] += 1
                else:
                    tally["succeeded"] += 1
                    won.add(spec.name)
    await database.dispose()
    print(f"tools: {len(sons)} sons, {len(mortals)} mortals, {dict(tally)}, {len(won)} of {len(offered)} offered tools succeeded at least once")
    print("never succeeded:", " ".join(sorted(offered - won)))
    for item in broken:
        print(item)
    return 1 if broken else 0


async def case(path: Path, kind: str, name: str) -> int:
    async def lived_cosmos(session: Any) -> Any:
        taken = set(await session.scalars(select(NodeRow.name)))
        name = next(candidate for candidate in ("Orvael", *(f"Orvael {number}" for number in range(2, len(taken) + 3))) if candidate not in taken)
        world = await factories.add_world(session, name)
        galaxy = await session.scalar(select(GalaxyRow.id).order_by(GalaxyRow.id).limit(1))
        star = await session.get(StarRow, world.star_id) if world.star_id is not None else None
        if star is not None and galaxy is not None:
            star.galaxy_id = galaxy
        await session.execute(delete(CosmicOfficeRow))
        repository = CosmosRepository(session)
        cosmos = await repository.require_cosmos()
        cosmos.epoch = factories.EPOCH
        creator = await repository.creator()
        region = await factories.make_entity(session, "Vale of Mist", EntityType.REGION, world_id=world.id)
        place = await factories.make_entity(session, "Ember Hollow", EntityType.PLACE, world_id=world.id, location_id=region.id)
        await session.flush()
        return factories.Cosmos(world.id, region.id, place.id, creator.id if creator is not None else 0)

    factories.seed_cosmos = lived_cosmos
    crashes = watch()
    database = opened(path)
    problem: str | None = None
    try:
        await (proof.test_son_tool_runs if kind == "son" else proof.test_mortal_tool_runs)(database, name)
    except AssertionError as error:
        problem = f"refused: {error}\n{traceback.format_exc()}"
    except Exception:
        problem = f"raised: {traceback.format_exc()}"
    finally:
        await database.dispose()
    if crashes.found:
        problem = f"crashed: {crashes.found[-1]}\n{problem or ''}"
    print(f"case {kind} {name}: {'PASS' if problem is None else problem}")
    return 0 if problem is None else 1


def cases(path: Path, folder: Path, only: list[str]) -> int:
    wanted = [("son", name) for name in sorted(SON_CASES)] + [("mortal", name) for name in sorted(MORTAL_CASES)]
    wanted = [item for item in wanted if not only or item[1] in only]
    failed = 0
    for kind, name in wanted:
        copy = clone(path, folder / f"{kind}-{name}.db")
        run = subprocess.run([sys.executable, __file__, "case", str(copy), kind, name], capture_output=True, text=True, check=False)
        verdict = next((line for line in run.stdout.splitlines() if line.startswith("case ")), f"case {kind} {name}: no verdict\n{run.stderr[-2000:]}")
        if not verdict.endswith("PASS"):
            failed += 1
            print(run.stdout[run.stdout.find("case ") :] if "case " in run.stdout else verdict)
        for leftover in folder.glob(f"{kind}-{name}.db*"):
            leftover.unlink()
    print(f"cases: {len(wanted)} run, {len(wanted) - failed} passed, {failed} failed")
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Check a copy of a lived world: prompts, engine epochs, read endpoints and every tool")
    parser.add_argument("check", choices=("prompts", "engine", "endpoints", "tools", "cases", "all", "case"))
    parser.add_argument("database", type=Path)
    parser.add_argument("extra", nargs="*")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--only", nargs="*", default=[])
    arguments = parser.parse_args()
    if arguments.check == "case":
        return asyncio.run(case(arguments.database, arguments.extra[0], arguments.extra[1]))
    folder = Path(tempfile.mkdtemp(prefix="lived_world_"))
    try:
        world = snapshot(arguments.database, folder)
        asyncio.run(open_turns(world))
        checks = ("prompts", "engine", "endpoints", "tools", "cases") if arguments.check == "all" else (arguments.check,)
        failed = 0
        for check in checks:
            copy = clone(world, folder / f"{check}.db")
            if check == "prompts":
                failed += asyncio.run(prompts(copy))
            elif check == "engine":
                failed += asyncio.run(engine(copy, arguments.epochs))
            elif check == "endpoints":
                failed += asyncio.run(endpoints(copy, folder / "endpoints"))
            elif check == "tools":
                failed += asyncio.run(tools(copy))
            else:
                failed += cases(world, folder, arguments.only)
        return 1 if failed else 0
    finally:
        shutil.rmtree(folder, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
