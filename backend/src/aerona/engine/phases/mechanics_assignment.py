from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.knowledge import NATURAL_LAWS, RESOURCE_MECHANICS
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.society import NaturalLaw
from aerona.engine.context import TickContext
from aerona.engine.gods.economy import mechanics_of
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.mechanics import assign_mechanics, resource_weighed
from aerona.rules.registry import Rules

WEIGHED_TYPES = (EntityType.RESOURCE, EntityType.NATURAL_LAW)
SKIPPED_STATUSES = (EntityStatus.REJECTED,)


async def unweighed(session: AsyncSession, statuses: tuple[EntityStatus, ...] | None = (EntityStatus.CANON,)) -> list[EntityRow]:
    statement = select(EntityRow).where(EntityRow.entity_type.in_(WEIGHED_TYPES))
    if statuses is not None:
        statement = statement.where(EntityRow.status.in_(list(statuses)))
    else:
        statement = statement.where(EntityRow.status.not_in(list(SKIPPED_STATUSES)))
    found: list[EntityRow] = []
    for entity in await session.scalars(statement.order_by(EntityRow.id)):
        if (entity.entity_type is EntityType.NATURAL_LAW and entity.natural_law is None) or (
            entity.entity_type is EntityType.RESOURCE and not await resource_weighed(session, entity)
        ):
            found.append(entity)
    return found


async def _announce(ctx: TickContext, entity: EntityRow) -> None:
    if entity.entity_type is EntityType.RESOURCE:
        mechanics = sorted(await mechanics_of(ctx.session, entity))
        if mechanics:
            rules_text = " ".join(RESOURCE_MECHANICS[item].effect for item in mechanics)
            await note(ctx, f"{entity.name} carries a strange rule: {rules_text}", key="mechanics.resource", ids=[entity.id], kind=ChronicleKind.RESOURCE)
        return
    if entity.natural_law is not None and entity.natural_law is not NaturalLaw.NONE:
        await note(
            ctx,
            f"{entity.name} wove itself into the workings of the world: {NATURAL_LAWS[entity.natural_law].effect}",
            key="mechanics.law",
            ids=[entity.id],
            kind=ChronicleKind.COSMIC_LAW,
        )


async def weigh(ctx: TickContext, entities: list[EntityRow], announce: bool) -> int:
    weighed = 0
    for entity in entities:
        if held(entity.id) or not await assign_mechanics(ctx.session, ctx.rules, entity):
            continue
        weighed += 1
        if announce and entity.status is EntityStatus.CANON:
            await _announce(ctx, entity)
    return weighed


@reads("table.bonds", "table.entity_flags", "table.epoch_year_cursors", "table.nodes", "table.resource_mechanics")
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
)
async def mechanics_assignment(ctx: TickContext) -> None:
    ctx.count("weighed", await weigh(ctx, await unweighed(ctx.session), announce=True))


async def weigh_everything(session: AsyncSession, rules: Rules) -> int:
    ctx = await manual_context(session, "mechanics_assignment", rules)
    return await weigh(ctx, await unweighed(session, None), announce=False)


PHASES = (Phase("mechanics_assignment", mechanics_assignment),)
