import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from functools import partial
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.session import Database
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.epochs import EpochRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.sons import SonPowerRow, SonRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.son import SonStatus
from aerona.jobs.context import JobContext
from aerona.rules.registry import Rules
from aerona.services.images.records import missing_prompt_targets
from aerona.services.lore_ports import LorePorts
from aerona.services.player.ports import ContentJob, ContentJobKind, RevelationRequest

logger = logging.getLogger(__name__)

FIRST_STAR_CONTENT = "The first light that hangs over the world and marks its first age."
CELESTIAL = EntityType.CELESTIAL.value


@dataclass(frozen=True)
class MissingWork:
    portrait: bool = False
    son_powers: list[int] = field(default_factory=list)
    sky_body: bool = False
    first_people: bool = False
    image_prompts: int = 0
    undeepened_gods: list[int] = field(default_factory=list)
    pending_names: int = 0
    past_narratives: list[int] = field(default_factory=list)

    @property
    def any(self) -> bool:
        return bool(
            self.portrait
            or self.son_powers
            or self.sky_body
            or self.first_people
            or self.image_prompts
            or self.undeepened_gods
            or self.pending_names
            or self.past_narratives
        )


@dataclass
class CompletionReport:
    completed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)


async def _exists(session: AsyncSession, entity_type: EntityType) -> bool:
    statement = select(EntityRow.id).where(EntityRow.entity_type == entity_type, EntityRow.status == EntityStatus.CANON).limit(1)
    return await session.scalar(statement) is not None


def god_needs_depth(god: ForeignGodRow) -> bool:
    return god.depth is None or not god.depth.history.strip()


async def missing_work(session: AsyncSession, rules: Rules) -> MissingWork:
    repository = CosmosRepository(session)
    cosmos = await repository.get()
    if cosmos is None:
        return MissingWork()
    creator = await repository.creator()
    powered = select(SonPowerRow.son_id)
    sons = list(await session.scalars(select(SonRow.id).where(SonRow.status != SonStatus.DEAD, SonRow.id.not_in(powered)).order_by(SonRow.id)))
    gods = [god.id for god in await session.scalars(select(ForeignGodRow).order_by(ForeignGodRow.id)) if god_needs_depth(god)]
    pending = int(
        await session.scalar(select(func.count()).select_from(EntityRow).where(EntityRow.pending_name.is_(True), EntityRow.status == EntityStatus.CANON)) or 0
    )
    narratives = list(
        await session.scalars(
            select(EpochRow.epoch).where(EpochRow.epoch < cosmos.epoch, or_(EpochRow.narrative.is_(None), EpochRow.narrative == "")).order_by(EpochRow.epoch)
        )
    )
    return MissingWork(
        portrait=creator is not None and not creator.image_prompt,
        son_powers=sons,
        sky_body=not await _exists(session, EntityType.CELESTIAL),
        first_people=not await _exists(session, EntityType.PEOPLE),
        image_prompts=len(await missing_prompt_targets(session, rules.content.image_prompt_batch)),
        undeepened_gods=gods,
        pending_names=pending,
        past_narratives=narratives,
    )


class StartupCompletion:
    def __init__(self, database: Database, rules: Callable[[], Rules], ports: LorePorts, *, read_only: Callable[[], bool] = lambda: False) -> None:
        self._database = database
        self._rules = rules
        self._ports = ports
        self._read_only = read_only

    def enabled(self) -> bool:
        return bool(self._rules().server.auto_complete) and not self._read_only()

    async def needed(self) -> MissingWork:
        async with self._database.read() as session:
            return await missing_work(session, self._rules())

    async def run(self, context: JobContext | None = None) -> dict[str, Any]:
        work = await self.needed()
        report = CompletionReport()
        steps = self._steps(work)
        for index, (name, step) in enumerate(steps, start=1):
            if context is not None:
                context.report(index / max(1, len(steps)), name)
            try:
                await step()
                report.completed.append(name)
            except Exception as error:
                logger.warning("startup completion step %s failed: %s", name, error)
                report.failed.append(name)
        return {"completed": report.completed, "failed": report.failed}

    def _steps(self, work: MissingWork) -> list[tuple[str, Callable[[], Awaitable[object]]]]:
        ports = self._ports
        steps: list[tuple[str, Callable[[], Awaitable[object]]]] = []
        if work.portrait and ports.writer is not None:
            writer = ports.writer
            steps.append(("portrait", lambda: writer.write(ContentJob(ContentJobKind.CREATOR_PORTRAIT, None))))
        if work.son_powers and ports.powers is not None:
            powers = ports.powers
            for son_id in work.son_powers:
                steps.append((f"powers:{son_id}", partial(powers.write_powers, son_id)))
        if work.first_people and ports.awakener is not None:
            awakener = ports.awakener
            steps.append(("peoples", lambda: self._awaken(awakener.awaken)))
        if work.image_prompts and ports.prompts is not None:
            steps.append(("image prompts", self._prompts))
        if work.undeepened_gods and ports.deepener is not None:
            deepener = ports.deepener
            for god_id in work.undeepened_gods:
                steps.append((f"foreign god:{god_id}", partial(deepener.deepen_foreign_god, god_id)))
        if work.pending_names and ports.namer is not None:
            steps.append(("naming", ports.namer.name_pending))
        if work.sky_body and ports.revelations is not None:
            steps.append(("first star", self._first_star))
        if work.past_narratives and ports.narrator is not None:
            narrator = ports.narrator
            for epoch in work.past_narratives:
                steps.append((f"narrative:{epoch}", partial(narrator.narrate, epoch)))
        return steps

    async def _awaken(self, awaken: Callable[[int, int | None], Awaitable[list[int]]]) -> list[int]:
        async with self._database.read() as session:
            cosmos = await CosmosRepository(session).require_cosmos()
            world_id = cosmos.primary_world_id
        return await awaken(self._rules().awakening.first_peoples, world_id)

    async def _prompts(self) -> int:
        writer = self._ports.prompts
        if writer is None:
            return 0
        async with self._database.read() as session:
            targets = await missing_prompt_targets(session, self._rules().content.image_prompt_batch)
        return await writer.write_batch([target.node_id for target in targets])

    async def _first_star(self) -> int | None:
        revelations = self._ports.revelations
        if revelations is None:
            return None
        async with self._database.read() as session:
            cosmos = await CosmosRepository(session).require_cosmos()
            world_id = cosmos.primary_world_id
        star_id = await revelations.reveal(RevelationRequest(FIRST_STAR_CONTENT, CELESTIAL, world_id, None))
        async with self._database.write() as session:
            world = await session.get(WorldRow, world_id) if world_id is not None else None
            entity = await session.get(EntityRow, star_id)
            if world is not None and entity is not None and entity.entity_type is EntityType.CELESTIAL:
                world.epoch_star_entity_id = entity.id
        return star_id
