from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.ask import ask
from aerona.agents.context.briefs import son_brief
from aerona.agents.context.cosmos_lines import cosmos_lines
from aerona.agents.context.scope import Scope, load_scope
from aerona.agents.context.world_header import world_header
from aerona.agents.roles import AgentRole
from aerona.agents.runtime import AgentRuntime
from aerona.catalog.domains import DOMAIN_LABELS
from aerona.catalog.worlds import STAR_TYPE_LABELS, WORLD_TYPES
from aerona.core.errors import ValidationFailedError
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.epochs import DeferredStepRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.routes import HorizonIntuitionRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.epoch import DeferredStepKind, DeferredStepStatus
from aerona.domain.enums.travel import HorizonStatus
from aerona.domain.enums.world import StarType, WorldType
from aerona.engine.cosmos.birth import BirthRequest, process_world_birth
from aerona.engine.phases.exploration import begin_intuition, intuition_inspiration, pending_intuitions, settle_intuition
from aerona.engine.primitives.manual import manual_context
from aerona.events.kinds import EventKind
from aerona.prompts import PromptId, render
from aerona.prompts.contexts.common import WorldItem
from aerona.prompts.contexts.cosmos import ForeignGodBrief, InspirationKind, NewWorldContext, PlacementKind, StarLine, WorldInspirationContext
from aerona.prompts.schemas.cosmos import NewWorldOutput

NAMED_TYPES = (EntityType.REGION, EntityType.PEOPLE, EntityType.LANGUAGE, EntityType.PLACE, EntityType.CELESTIAL)
PAYLOAD_TYPE = "world_type"
PAYLOAD_INSPIRATION = "inspiration"
PAYLOAD_STAR = "star_id"
PAYLOAD_PARENT = "parent_world_id"
PAYLOAD_NEW_STAR = "new_star"
PAYLOAD_SON = "son_id"
PAYLOAD_STAR_TYPE = "new_star_type"


@dataclass(frozen=True)
class BirthPlan:
    world_type: WorldType | None = None
    inspiration: str | None = None
    star_id: int | None = None
    parent_world_id: int | None = None
    new_star: bool = False
    son_id: int | None = None
    new_star_type: StarType | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "BirthPlan":
        raw_type = payload.get(PAYLOAD_TYPE)
        return cls(
            world_type=WorldType(raw_type) if isinstance(raw_type, str) and raw_type in WorldType.__members__.values() else None,
            inspiration=payload.get(PAYLOAD_INSPIRATION) if isinstance(payload.get(PAYLOAD_INSPIRATION), str) else None,
            star_id=payload.get(PAYLOAD_STAR) if isinstance(payload.get(PAYLOAD_STAR), int) else None,
            parent_world_id=payload.get(PAYLOAD_PARENT) if isinstance(payload.get(PAYLOAD_PARENT), int) else None,
            new_star=bool(payload.get(PAYLOAD_NEW_STAR)),
            son_id=payload.get(PAYLOAD_SON) if isinstance(payload.get(PAYLOAD_SON), int) else None,
            new_star_type=StarType(raw_star)
            if isinstance(raw_star := payload.get(PAYLOAD_STAR_TYPE), str) and raw_star in StarType.__members__.values()
            else None,
        )


def placement_of(plan: BirthPlan) -> PlacementKind:
    if plan.parent_world_id is not None:
        return PlacementKind.MOON
    if plan.star_id is not None:
        return PlacementKind.EXISTING_STAR
    return PlacementKind.NEW_STAR if plan.new_star or plan.new_star_type is not None else PlacementKind.FREE


async def banned_names(scope: Scope) -> list[str]:
    rules = scope.rules.world_birth
    names = list(
        await scope.session.scalars(
            select(EntityRow.name).where(EntityRow.entity_type.in_(NAMED_TYPES)).order_by(EntityRow.id.desc()).limit(rules.banned_names)
        )
    )
    cosmic = [
        *(world.name for world in scope.worlds.values()),
        *await scope.session.scalars(select(StarRow.name)),
        *await scope.session.scalars(select(ForeignGodRow.name)),
    ]
    return names + cosmic[: rules.banned_cosmic_names]


async def birth_context(scope: Scope, plan: BirthPlan) -> NewWorldContext:
    stars = list(await scope.session.scalars(select(StarRow).order_by(StarRow.id)))
    gods = list(await scope.session.scalars(select(ForeignGodRow).order_by(ForeignGodRow.id)))
    son = await scope.session.get(SonRow, plan.son_id) if plan.son_id is not None else None
    primary = scope.primary_world
    return NewWorldContext(
        lore_language=scope.cosmos.lore_language,
        rules=scope.rules,
        cosmos_name=scope.cosmos.name,
        world_header=await world_header(scope),
        cosmos_lines=await cosmos_lines(scope),
        main_world=WorldItem(id=primary.id if primary else 0, name=primary.name if primary else scope.cosmos.name),
        stars=[
            StarLine(
                id=star.id,
                name=star.name,
                type_label=STAR_TYPE_LABELS[star.star_type],
                description=star.description,
                planets=[WorldItem(id=world.id, name=world.name) for world in scope.worlds.values() if world.star_id == star.id],
            )
            for star in stars
        ],
        foreign_gods=[ForeignGodBrief(name=god.name, title=god.title, world_id=god.world_id, domains=DOMAIN_LABELS[god.domain_primary]) for god in gods],
        placement=placement_of(plan),
        star_id=plan.star_id,
        parent_world_id=plan.parent_world_id,
        creator_son=son_brief(son) if son is not None else None,
        god_name=scope.creator.name,
        world_type_label=WORLD_TYPES[plan.world_type].label if plan.world_type else None,
        world_type_key=plan.world_type.value if plan.world_type else None,
        inspiration=plan.inspiration,
        banned_names=await banned_names(scope),
        cosmic_resource=scope.cosmos.travel_resource.name if scope.cosmos.travel_resource is not None else None,
    )


async def birth_world(runtime: AgentRuntime, plan: BirthPlan) -> WorldRow:
    runtime.require_llm("world birth")
    async with runtime.database.read() as session:
        rules = await runtime.rules(session)
        scope = await load_scope(session, rules)
        context = await birth_context(scope, plan)
        son = await session.get(SonRow, plan.son_id) if plan.son_id is not None else None
        maker = son.name if son is not None else scope.creator.name
    label = f" ({WORLD_TYPES[plan.world_type].label})" if plan.world_type else ""
    runtime.step(f"{maker} is giving birth to a new world{label}…")
    output = await ask(
        runtime.model,
        rules,
        label=AgentRole.WORLD_BIRTH,
        system=(PromptId.NEW_WORLD_SYSTEM, context),
        user=(PromptId.NEW_WORLD_USER, context),
        output=NewWorldOutput,
    )
    if not output.regions:
        raise ValidationFailedError("A world cannot be born without regions.")
    request = BirthRequest(
        forced_type=plan.world_type,
        creator_son_id=plan.son_id,
        star_id=plan.star_id,
        parent_world_id=plan.parent_world_id,
        new_star=plan.new_star or plan.new_star_type is not None,
        new_star_type=plan.new_star_type,
    )
    async with runtime.database.write() as session:
        ctx = await manual_context(session, "world_birth", rules, runtime.publish)
        world = await process_world_birth(ctx, output, request)
        world_id, name = world.id, world.name
    runtime.publish(EventKind.WORLD_BORN, {"world_id": world_id, "name": name})
    async with runtime.database.read() as session:
        born = await session.get(WorldRow, world_id)
    if born is None:
        raise ValidationFailedError("The new world vanished.")
    return born


async def process_deferred_births(runtime: AgentRuntime) -> int:
    async with runtime.database.write() as session:
        steps = list(
            await session.scalars(
                select(DeferredStepRow)
                .where(DeferredStepRow.kind == DeferredStepKind.WORLD_BIRTH, DeferredStepRow.status == DeferredStepStatus.PENDING)
                .order_by(DeferredStepRow.id)
            )
        )
        for step in steps:
            step.status = DeferredStepStatus.RUNNING
            step.attempts += 1
        plans = [(step.id, BirthPlan.from_payload(step.payload)) for step in steps]
    born = 0
    for step_id, plan in plans:
        try:
            world = await birth_world(runtime, plan)
            status, error, result = DeferredStepStatus.DONE, None, world.id
            born += 1
        except Exception as failure:
            status, error, result = DeferredStepStatus.FAILED, str(failure), None
            runtime.error(f"The world could not be born: {failure}")
        async with runtime.database.write() as session:
            row = await session.get(DeferredStepRow, step_id)
            if row is not None:
                row.status, row.error, row.result_world_id = status, error, result
    return born


async def process_intuitions(runtime: AgentRuntime) -> int:
    async with runtime.database.read() as session:
        waiting = [intuition.id for intuition in await pending_intuitions(session)]
    born = 0
    for intuition_id in waiting:
        async with runtime.database.write() as session:
            intuition = await session.get(HorizonIntuitionRow, intuition_id)
            if intuition is None or intuition.status is not HorizonStatus.PENDING:
                continue
            seeker = await begin_intuition(session, intuition)
            inspiration = intuition_inspiration(seeker, intuition) if seeker is not None else None
        if inspiration is None:
            continue
        try:
            world = await birth_world(runtime, BirthPlan(inspiration=inspiration))
        except Exception as failure:
            async with runtime.database.write() as session:
                row = await session.get(HorizonIntuitionRow, intuition_id)
                if row is not None:
                    row.status = HorizonStatus.PENDING
            runtime.error(f"The sensed world could not be born: {failure}")
            break
        async with runtime.database.write() as session:
            rules = await runtime.rules(session)
            ctx = await manual_context(session, "sensed_world", rules, runtime.publish)
            row = await session.get(HorizonIntuitionRow, intuition_id)
            born_world = await session.get(WorldRow, world.id)
            if row is not None:
                text = await settle_intuition(ctx, row, born_world)
                if text:
                    runtime.note(text)
            await mark_sensed_step(session, intuition_id, world.id)
        born += 1
    return born


async def mark_sensed_step(session: AsyncSession, intuition_id: int, world_id: int) -> None:
    steps = await session.scalars(
        select(DeferredStepRow).where(DeferredStepRow.kind == DeferredStepKind.SENSED_WORLD, DeferredStepRow.status == DeferredStepStatus.PENDING)
    )
    for step in steps:
        if step.payload.get("intuition_id") == intuition_id:
            step.status = DeferredStepStatus.DONE
            step.result_world_id = world_id


def inspiration_text(kind: InspirationKind, mortal_name: str = "", method: str = "", world_number: int = 0) -> str:
    return render(PromptId.WORLD_INSPIRATION, WorldInspirationContext(kind=kind, mortal_name=mortal_name, method=method, world_number=world_number))
