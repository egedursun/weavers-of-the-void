from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.ask import ask
from aerona.agents.chronicle import record_line
from aerona.agents.context.scope import Scope, load_scope
from aerona.agents.context.world_line import world_line
from aerona.agents.context.world_summary import world_summary
from aerona.agents.roles import AgentRole
from aerona.agents.runtime import AgentRuntime
from aerona.agents.stats import stats_from
from aerona.agents.text import sanitize
from aerona.catalog.entity_types import ENTITY_TYPES, can_contain
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityDraft, EntityRepository
from aerona.db.repositories.names import NameRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityOrigin, EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.society import NaturalLaw
from aerona.engine.economy.resources import set_resource_yield
from aerona.engine.primitives.mechanics import assign_mechanics
from aerona.engine.structures.backfill import FALLBACK
from aerona.engine.structures.profiles import ensure_profile as ensure_structure_profile
from aerona.events.kinds import EventKind
from aerona.prompts import PromptId
from aerona.prompts.contexts.common import WorldItem
from aerona.prompts.contexts.genesis import RevelationContext, RevelationType
from aerona.prompts.schemas.genesis import RevelationOutput
from aerona.rules.registry import Rules

REVELATION_TAG = "revelation"
LAW_TAG_PREFIX = "law:"
SON_TARGET = "son"
LOCATED_STATUSES = (EntityStatus.CANON, EntityStatus.DEAD)
UNLINKABLE = (EntityStatus.REJECTED, EntityStatus.DESTROYED)


def revelation_types(entity_type: EntityType | None) -> list[RevelationType]:
    kinds = [entity_type] if entity_type is not None else [kind for kind, spec in ENTITY_TYPES.items() if spec.creation_tool]
    return [
        RevelationType(
            type_label=ENTITY_TYPES[kind].label,
            stats=[field.key for field in ENTITY_TYPES[kind].stats],
            locations=[ENTITY_TYPES[item].label for item in ENTITY_TYPES[kind].containers],
        )
        for kind in kinds
    ]


async def valid_location(scope: Scope, entity_type: EntityType, location_id: int, world_id: int) -> EntityRow | None:
    location = await scope.session.get(EntityRow, location_id) if location_id else None
    if location is None or location.status not in LOCATED_STATUSES or location.world_id != world_id or not can_contain(location.entity_type, entity_type):
        return None
    return location


async def first_region(scope: Scope, world_id: int) -> EntityRow | None:
    return await scope.session.scalar(
        select(EntityRow)
        .where(EntityRow.world_id == world_id, EntityRow.entity_type == EntityType.REGION, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
        .limit(1)
    )


async def link_revelation(scope: Scope, entity: EntityRow, output: RevelationOutput) -> None:
    bonds = BondRepository(scope.session)
    for link in output.links:
        if link.target_kind.strip().casefold() == SON_TARGET:
            target_id = link.target_id if await scope.session.get(SonRow, link.target_id) is not None else None
        else:
            target = await scope.session.get(EntityRow, link.target_id)
            ok = (
                target is not None
                and target.id != entity.id
                and target.status not in UNLINKABLE
                and (not scope.multi_world or target.world_id == entity.world_id)
            )
            target_id = link.target_id if ok else None
        if target_id is None or (link.kind is BondKind.INSIDE and target_id == entity.location_id):
            continue
        await bonds.connect(BondDraft(entity.id, target_id, link.kind, scope.epoch, sanitize(link.description) or None))


async def type_revealed(session: AsyncSession, rules: Rules, epoch: int, entity: EntityRow, output: RevelationOutput) -> None:
    if entity.entity_type is EntityType.RESOURCE:
        await set_resource_yield(session, rules, entity.id, output.commodity or CommodityKind.ORE, output.material)
    elif entity.entity_type is EntityType.STRUCTURE:
        await ensure_structure_profile(session, rules, epoch, entity, output.structure_kind or FALLBACK, material=output.material)


def revelation_tags(output: RevelationOutput, entity_type: EntityType, mechanic: NaturalLaw | None) -> list[str]:
    tags = [tag for tag in (output.tags or [REVELATION_TAG]) if not tag.startswith(LAW_TAG_PREFIX)]
    law = mechanic or output.mechanic
    if entity_type is EntityType.NATURAL_LAW and law is not None:
        tags.append(f"{LAW_TAG_PREFIX}{law.value}")
    return tags


async def reveal(
    runtime: AgentRuntime, text: str, entity_type: EntityType | None = None, world_id: int | None = None, mechanic: NaturalLaw | None = None
) -> EntityRow:
    runtime.require_llm("revelation")
    if not text.strip():
        raise ValidationFailedError("A revelation needs content.")
    async with runtime.database.read() as session:
        rules = await runtime.rules(session)
        scope = await load_scope(session, rules)
        target = world_id if world_id is not None else scope.primary_world_id
        if target not in scope.worlds:
            raise NotFoundError("No such world.")
        context = RevelationContext(
            lore_language=scope.cosmos.lore_language,
            god_name=scope.creator.name,
            world_name=scope.cosmos.name,
            target_world=WorldItem(id=target, name=scope.world_name(target)) if scope.multi_world else None,
            target_world_line=await world_line(scope, target) or None if scope.multi_world else None,
            world_summary=await world_summary(scope),
            entity_types=revelation_types(entity_type),
            first_star=entity_type is EntityType.CELESTIAL,
            revelation_text=text.strip(),
        )
    runtime.step(f"{scope.creator.name} is revealing…")
    output = await ask(
        runtime.model,
        rules,
        label=AgentRole.REVELATION,
        system=(PromptId.REVELATION_SYSTEM, context),
        user=(PromptId.REVELATION_USER, context),
        output=RevelationOutput,
    )
    chosen = entity_type or output.type
    async with runtime.database.write() as session:
        scope = await load_scope(session, rules)
        location = await valid_location(scope, chosen, output.location_id, target)
        if location is None and ENTITY_TYPES[chosen].location_required:
            location = await first_region(scope, target)
        entity = await EntityRepository(session).create(
            EntityDraft(
                name=await NameRepository(session).unique_name(output.name),
                entity_type=chosen,
                description=sanitize(output.description),
                stats=stats_from(chosen, output.stats, rules),
                power_level=max(1, min(rules.content.revelation_max_power, output.power_level)),
                origin=EntityOrigin.CREATOR,
                birth_epoch=scope.epoch,
                world_id=None if location is not None else target,
                location_id=location.id if location is not None else None,
                subtype=output.subtype.strip() or None,
                domain=output.domain,
                natural_law=(mechanic or output.mechanic) if chosen is EntityType.NATURAL_LAW else None,
                image_prompt=output.image_prompt.strip() or None,
                tags=revelation_tags(output, chosen, mechanic),
                split_title=False,
            )
        )
        await link_revelation(scope, entity, output)
        await type_revealed(session, rules, scope.epoch, entity, output)
        await assign_mechanics(session, rules, entity, resource_choice=output.resource_mechanics)
        await record_line(
            session,
            rules,
            "creator.revelation",
            roles={IncidentRole.ACTOR: scope.creator.id, IncidentRole.PRODUCT: entity.id},
            facts={"type_label": ENTITY_TYPES[chosen].label},
            kind=ChronicleKind.CREATOR_HAND,
        )
        entity_id = entity.id
    runtime.publish(EventKind.REVELATION, {"entity_id": entity_id, "name": entity.name})
    async with runtime.database.read() as session:
        created = await session.get(EntityRow, entity_id)
    if created is None:
        raise NotFoundError("The revealed record vanished.")
    return created
