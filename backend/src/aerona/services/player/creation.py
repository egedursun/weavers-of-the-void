import math
from typing import Any

from pydantic import Field

from aerona.constants.tool_inputs import IMAGE_PROMPT_MAX
from aerona.core.errors import BusyError, ValidationFailedError
from aerona.db.tables.prehistory import EPOCHS_MAX
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.job import JobKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.world import StarType, WorldType
from aerona.engine.cosmos.foreign_gods import NewForeignGod, add_foreign_god
from aerona.engine.prehistory.control import configure
from aerona.engine.prehistory.run import run_prehistory
from aerona.engine.recording.record import record
from aerona.events.kinds import EventKind
from aerona.jobs.context import JobContext
from aerona.rules.registry import Rules
from aerona.services.player import guards, pantheon
from aerona.services.player.ports import ContentJob, ContentJobKind, WorldCreationRequest
from aerona.services.player.runtime import CostedJob, FreeJob, PlayerRuntime, submit_costed, submit_free, unavailable
from aerona.services.player.scope import ActionOutcome, Command, Effect, PlayerScope, player_action

MIN_PEOPLES = 1


class SummonSon(Command):
    world_id: int | None = None


class BirthChild(Command):
    son_id: int
    inspiration: str = ""
    co_parent_id: int | None = None


class MortalTarget(Command):
    entity_id: int


class CreateWorld(Command):
    world_type: WorldType | None = None
    inspiration: str = ""
    star_id: int | None = None
    parent_world_id: int | None = None
    new_star: bool = False
    new_star_type: StarType | None = None
    prehistory_epochs: int | None = Field(default=None, ge=0, le=EPOCHS_MAX)


class AwakenPeoples(Command):
    count: int = 2
    world_id: int | None = None


class ForeignGodTarget(Command):
    god_id: int


class PlaceForeignGod(Command):
    world_id: int
    name: str
    title: str | None = None
    description: str | None = None
    domain_primary: Domain = Domain.EARTH
    domain_secondary: Domain | None = None
    stance: int = 0
    power: int | None = None
    image_prompt: str | None = None


async def _validated_world(runtime: PlayerRuntime, world_id: int | None) -> None:
    async with runtime.database.read() as session:
        await guards.target_world(session, world_id)


async def summon_son(runtime: PlayerRuntime, rules: Rules, command: SummonSon) -> ActionOutcome:
    summoner = runtime.ports.summoner
    if summoner is None:
        raise unavailable("Summoning a son")
    await _validated_world(runtime, command.world_id)

    async def work(context: JobContext) -> dict[str, Any] | None:
        context.report(0.0, "summon")
        son_id = await summoner.summon(command.world_id)
        runtime.bus.publish(EventKind.NEW_SON, {"son_id": son_id})
        return {"son_id": son_id}

    job = CostedJob("summon_son", ActionKind.SUMMON_SON, JobKind.SUMMON, "summon", rules.costs.summon_son, "costs.summon_son")
    return await submit_costed(runtime, rules, job, command, work)


async def birth_child(runtime: PlayerRuntime, rules: Rules, command: BirthChild) -> ActionOutcome:
    summoner = runtime.ports.summoner
    if summoner is None:
        raise unavailable("A son's child")
    async with runtime.database.read() as session:
        parent = await guards.son(session, command.son_id)
        if not parent.alive:
            raise ValidationFailedError(f"{parent.name} is dead and cannot bear a child.")
        if command.co_parent_id is not None:
            partner = await guards.son(session, command.co_parent_id)
            if partner.id == parent.id or not partner.alive:
                raise ValidationFailedError("The other parent must be another living son.")
    inspiration = command.inspiration.strip()[: rules.god_actions.inspiration_max_chars]

    async def work(context: JobContext) -> dict[str, Any] | None:
        context.report(0.0, "birth")
        son_id = await summoner.birth(command.son_id, inspiration, command.co_parent_id)
        runtime.bus.publish(EventKind.NEW_SON, {"son_id": son_id})
        return {"son_id": son_id}

    return await submit_free(runtime, FreeJob("son:birth_child", JobKind.SUMMON, f"son:{command.son_id}:birth"), command, work)


async def mortal_act(runtime: PlayerRuntime, rules: Rules, command: MortalTarget) -> ActionOutcome:
    del rules
    actor = runtime.ports.mortals
    if actor is None:
        raise unavailable("A mortal's turn")
    async with runtime.database.read() as session:
        mortal = await guards.canon_entity(session, command.entity_id, "The mortal")

    async def work(context: JobContext) -> dict[str, Any] | None:
        context.report(0.0, "mortal turn")
        word = await actor.act(mortal.id)
        return {"entity_id": mortal.id, "word": word}

    return await submit_free(runtime, FreeJob("mortal:act", JobKind.SON_TURN, f"mortal:{mortal.id}:turn"), command, work)


async def create_world(runtime: PlayerRuntime, rules: Rules, command: CreateWorld) -> ActionOutcome:
    maker = runtime.ports.worlds
    if maker is None:
        raise unavailable("Creating a world")
    async with runtime.database.read() as session:
        if command.star_id is not None:
            await guards.star(session, command.star_id)
        if command.parent_world_id is not None:
            await guards.open_world(session, command.parent_world_id)
    if command.star_id is not None and command.parent_world_id is not None:
        raise ValidationFailedError("A new world circles either a star or another world, not both.")
    request = WorldCreationRequest(
        world_type=command.world_type,
        inspiration=command.inspiration.strip()[: rules.god_actions.inspiration_max_chars],
        star_id=command.star_id,
        parent_world_id=command.parent_world_id,
        new_star=command.new_star,
        new_star_type=command.new_star_type,
    )

    async def work(context: JobContext) -> dict[str, Any] | None:
        context.report(0.0, "world")
        world_id = await maker.create(request)
        runtime.bus.publish(EventKind.WORLD_BORN, {"world_id": world_id})
        epochs = rules.prehistory.epochs if command.prehistory_epochs is None else command.prehistory_epochs
        if epochs:
            context.report(0.5, "prehistory")
            async with runtime.database.write() as session:
                await configure(await runtime.scope(session, rules).context("create_world_prehistory"), world_id, epochs, rules.prehistory.resolution)
            await run_prehistory(runtime.database, world_id, rules=rules, publish=runtime.publish)
        return {"world_id": world_id}

    job = CostedJob("create_world", ActionKind.CREATE_WORLD, JobKind.WORLD_CREATION, "world", rules.balance.create_world, "balance.create_world")
    return await submit_costed(runtime, rules, job, command, work)


def awakening_cost(rules: Rules, count: int) -> int:
    return rules.balance.awaken_peoples * math.ceil(count / rules.awakening.batch_cap)


async def awaken_peoples(runtime: PlayerRuntime, rules: Rules, command: AwakenPeoples) -> ActionOutcome:
    awakener = runtime.ports.awakener
    if awakener is None:
        raise unavailable("Awakening peoples")
    if command.count < MIN_PEOPLES:
        raise ValidationFailedError("At least one people must awaken.")
    await _validated_world(runtime, command.world_id)
    batch = rules.awakening.batch_cap

    async def work(context: JobContext) -> dict[str, Any] | None:
        created: list[int] = []
        remaining = command.count
        while remaining > 0:
            size = min(batch, remaining)
            created += await awakener.awaken(size, command.world_id)
            remaining -= size
            context.report(1 - remaining / command.count, "awaken")
        runtime.bus.publish(EventKind.SYSTEM_NOTE, {"text": f"Awakened peoples: {len(created)}.", "entity_ids": created})
        return {"entity_ids": created}

    job = CostedJob("awaken_peoples", ActionKind.AWAKEN_PEOPLES, JobKind.AWAKENING, "awaken", awakening_cost(rules, command.count), "balance.awaken_peoples")
    return await submit_costed(runtime, rules, job, command, work)


async def deepen_foreign_god(runtime: PlayerRuntime, rules: Rules, command: ForeignGodTarget) -> ActionOutcome:
    writer = runtime.ports.writer
    if writer is None:
        raise unavailable("Deepening a foreign god")
    async with runtime.database.read() as session:
        god = await guards.foreign_god(session, command.god_id)
        name = god.name

    async def work(context: JobContext) -> dict[str, Any] | None:
        context.report(0.0, "deepen")
        summary = await writer.write(ContentJob(ContentJobKind.FOREIGN_GOD_DEEPEN, command.god_id))
        runtime.bus.publish(EventKind.FOREIGN_GOD_DEEPENED, {"id": command.god_id, "name": name})
        return {"summary": summary}

    return await submit_free(runtime, FreeJob("foreign_god:deepen", JobKind.DEEPEN, f"foreign_god:{command.god_id}:deepen"), command, work)


async def wake_foreign_god(runtime: PlayerRuntime, rules: Rules, command: pantheon.ForeignGodTarget) -> ActionOutcome:
    async with runtime.database.write() as session:
        outcome = await pantheon.wake(runtime.scope(session, rules), command)
        name = (await guards.foreign_god(session, command.god_id)).name
    writer = runtime.ports.writer
    if writer is None:
        return outcome

    async def work(context: JobContext) -> dict[str, Any] | None:
        context.report(0.0, "rewrite")
        summary = await writer.write(ContentJob(ContentJobKind.FOREIGN_GOD_AWAKENED, command.god_id))
        runtime.bus.publish(EventKind.FOREIGN_GOD_DEEPENED, {"id": command.god_id, "name": name})
        return {"summary": summary}

    try:
        queued = await submit_free(runtime, FreeJob("foreign_god:wake", JobKind.DEEPEN, f"foreign_god:{command.god_id}:deepen"), command, work)
    except BusyError:
        return outcome
    return outcome.model_copy(update={"values": {**outcome.values, **queued.values}})


@player_action("foreign_god:place", ActionKind.OTHER)
async def place_foreign_god(scope: PlayerScope, command: PlaceForeignGod) -> Effect:
    world = await guards.world(scope.session, command.world_id)
    if not command.name.strip():
        raise ValidationFailedError("It must have a name.")
    ctx = await scope.context("place_foreign_god")
    secondary = command.domain_secondary if command.domain_secondary is not command.domain_primary else None
    god = await add_foreign_god(
        scope.session,
        scope.rules,
        ctx.rng("place_foreign_god"),
        ctx.epoch,
        NewForeignGod(
            name=command.name.strip(),
            world_id=world.id,
            domains=(command.domain_primary, secondary),
            title=(command.title or "").strip() or None,
            description=(command.description or "").strip() or None,
            stance=command.stance,
            power=command.power,
            image_prompt=(command.image_prompt or "").strip()[:IMAGE_PROMPT_MAX] or None,
        ),
    )
    creator = await scope.creator()
    message = (
        await record(
            ctx,
            "player.foreign_god.placed",
            roles={IncidentRole.SUBJECT: god.id, IncidentRole.AUTHORITY: creator.id},
            facts={"world": str(world.name)},
            kind=ChronicleKind.FOREIGN_GOD,
            world_id=world.id,
        )
    ).text
    return Effect(message, god.id, created_ids=(god.id,), values={"god_id": god.id})


async def place_and_deepen(runtime: PlayerRuntime, rules: Rules, command: PlaceForeignGod) -> ActionOutcome:
    async with runtime.database.write() as session:
        outcome = await place_foreign_god(runtime.scope(session, rules), command)
    god_id = outcome.values.get("god_id")
    if runtime.llm_enabled and runtime.ports.writer is not None and isinstance(god_id, int):
        deepening = await deepen_foreign_god(runtime, rules, ForeignGodTarget(god_id=god_id))
        return outcome.model_copy(update={"values": {**outcome.values, "job_id": deepening.values.get("job_id")}})
    return outcome
