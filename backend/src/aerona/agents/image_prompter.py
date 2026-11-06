from collections.abc import Sequence

from sqlalchemy import select

from aerona.agents.ask import ask
from aerona.agents.context.scope import Scope, load_scope
from aerona.agents.roles import AgentRole
from aerona.agents.runtime import AgentRuntime
from aerona.catalog.entity_types import ENTITY_TYPES
from aerona.catalog.stars import STAR_TYPE_LABELS, STAR_TYPES
from aerona.catalog.worlds import WORLD_TYPES
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.entity import EntityFlag, EntityStatus
from aerona.domain.enums.world import WorldType
from aerona.prompts import PromptId
from aerona.prompts.contexts.imagery import CosmosImagePromptsContext, CosmosSubject, EntityImagePromptsContext, ImageSubject, WorldAmbience
from aerona.prompts.data.images import CosmosSubjectKind, fix_image_prompt
from aerona.prompts.schemas.narrative import CosmosImagePromptsOutput, EntityImagePromptsOutput

PROMPTABLE_STATUSES = (EntityStatus.CANON, EntityStatus.DEAD, EntityStatus.FULFILLED)


def star_description(star: StarRow) -> str:
    return " ".join(part for part in (STAR_TYPES[star.star_type].description, star.description) if part)


def ambience(world: WorldRow | None) -> WorldAmbience | None:
    if world is None or world.world_type is WorldType.ORDINARY:
        return None
    spec = WORLD_TYPES[world.world_type]
    return WorldAmbience(type_label=spec.label, biomes=list(spec.biomes))


async def entity_subjects(scope: Scope, limit: int, ids: Sequence[int] | None) -> list[tuple[EntityRow, ImageSubject]]:
    content = scope.rules.content
    statement = select(EntityRow).where(EntityRow.status.in_(PROMPTABLE_STATUSES))
    statement = statement.where(EntityRow.id.in_(list(ids))) if ids else statement.where(EntityRow.image_prompt.is_(None))
    rows = list(await scope.session.scalars(statement.order_by(EntityRow.pending_name, EntityRow.id).limit(limit)))
    repository = EntityRepository(scope.session)
    kinds = select(VesselProfileRow.entity_id, VesselProfileRow.kind).where(VesselProfileRow.entity_id.in_([row.id for row in rows]))
    vehicles = {entity_id: kind for entity_id, kind in await scope.session.execute(kinds)}
    return [
        (
            row,
            ImageSubject(
                id=row.id,
                entity_type=row.entity_type,
                type_label=ENTITY_TYPES[row.entity_type].label,
                subtype=row.subtype,
                name=row.name,
                description=row.description[: content.image_prompt_description_chars],
                megafauna=await repository.has_flag(row.id, EntityFlag.MEGAFAUNA),
                vehicle=vehicles.get(row.id),
                ambience=ambience(scope.worlds.get(row.world_id)),
            ),
        )
        for row in rows
    ]


async def missing_image_prompts(runtime: AgentRuntime, limit: int | None = None, ids: Sequence[int] | None = None) -> int:
    runtime.require_llm("image prompts")
    async with runtime.database.read() as session:
        rules = await runtime.rules(session)
        scope = await load_scope(session, rules)
        subjects = await entity_subjects(scope, limit or rules.content.image_prompt_batch, ids)
        if not subjects:
            return 0
        context = EntityImagePromptsContext(
            rules=rules, world_name=scope.cosmos.name, cosmology=scope.cosmos.cosmology, tone=scope.cosmos.tone, subjects=[item for _, item in subjects]
        )
    output = await ask(
        runtime.model,
        rules,
        label=AgentRole.ENTITY_IMAGE_PROMPTS,
        system=(PromptId.ENTITY_IMAGE_PROMPTS_SYSTEM, context),
        user=(PromptId.ENTITY_IMAGE_PROMPTS_USER, context),
        output=EntityImagePromptsOutput,
    )
    wanted = {subject.id: subject for _, subject in subjects}
    written = 0
    async with runtime.database.write() as session:
        for item in output.prompts:
            subject = wanted.get(item.id)
            text = item.prompt.strip()
            entity = await session.get(EntityRow, item.id)
            if subject is None or entity is None or len(text) < rules.content.image_prompt_min_chars:
                continue
            entity.image_prompt = fix_image_prompt(text, subject.entity_type, subject.megafauna, rules.content.cosmic_image_prompt_max_chars)
            written += 1
    if written:
        runtime.note(f"{written} entities got an image prompt.")
    return written


CosmicRow = WorldRow | StarRow | ForeignGodRow | SonRow | CreatorRow
COSMIC_TABLES: dict[CosmosSubjectKind, type[CosmicRow]] = {
    CosmosSubjectKind.WORLD: WorldRow,
    CosmosSubjectKind.STAR: StarRow,
    CosmosSubjectKind.FOREIGN_GOD: ForeignGodRow,
    CosmosSubjectKind.SON: SonRow,
    CosmosSubjectKind.CREATOR: CreatorRow,
}


def son_description(son: SonRow) -> str:
    return f"god of {son.domain_primary.value} and {son.domain_secondary.value}, {son.rarity.value}, {son.status.value}"


def creator_description(creator: CreatorRow) -> str:
    return " ".join(part for part in (creator.appearance, creator.temperament) if part) or "the god who made this cosmos"


async def cosmos_subjects(scope: Scope, ids: Sequence[int] | None = None) -> list[tuple[CosmosSubjectKind, int, CosmosSubject]]:
    content = scope.rules.content
    wanted = set(ids) if ids else None
    found: list[tuple[CosmosSubjectKind, int, CosmosSubject]] = []
    creator = await CosmosRepository(scope.session).creator()
    if creator is not None and creator.image_prompt is None and (wanted is None or creator.id in wanted):
        found.append(
            (
                CosmosSubjectKind.CREATOR,
                creator.id,
                CosmosSubject(
                    number=len(found) + 1,
                    kind=CosmosSubjectKind.CREATOR,
                    name=creator.name,
                    title=creator.title,
                    description=creator_description(creator)[: content.cosmic_prompt_other_chars],
                ),
            )
        )
    for son in await scope.session.scalars(select(SonRow).where(SonRow.image_prompt.is_(None)).order_by(SonRow.id)):
        if wanted is not None and son.id not in wanted:
            continue
        found.append(
            (
                CosmosSubjectKind.SON,
                son.id,
                CosmosSubject(
                    number=len(found) + 1,
                    kind=CosmosSubjectKind.SON,
                    name=son.name,
                    title=son.title,
                    description=son_description(son)[: content.cosmic_prompt_other_chars],
                ),
            )
        )
    for world in scope.worlds.values():
        if world.image_prompt is None and (wanted is None or world.id in wanted):
            subject = CosmosSubject(
                number=len(found) + 1,
                kind=CosmosSubjectKind.WORLD,
                type_label=WORLD_TYPES[world.world_type].label,
                name=world.name,
                description=(world.description or world.cosmology or "")[: content.cosmic_prompt_world_chars],
                ambience=ambience(world),
            )
            found.append((CosmosSubjectKind.WORLD, world.id, subject))
    for star in await scope.session.scalars(select(StarRow).where(StarRow.image_prompt.is_(None)).order_by(StarRow.id)):
        if wanted is not None and star.id not in wanted:
            continue
        found.append(
            (
                CosmosSubjectKind.STAR,
                star.id,
                CosmosSubject(
                    number=len(found) + 1,
                    kind=CosmosSubjectKind.STAR,
                    type_label=STAR_TYPE_LABELS[star.star_type],
                    name=star.name,
                    description=" ".join(part for part in (STAR_TYPES[star.star_type].description, star.description) if part)[
                        : content.cosmic_prompt_other_chars
                    ],
                ),
            )
        )
    for god in await scope.session.scalars(select(ForeignGodRow).where(ForeignGodRow.image_prompt.is_(None)).order_by(ForeignGodRow.id)):
        if wanted is not None and god.id not in wanted:
            continue
        found.append(
            (
                CosmosSubjectKind.FOREIGN_GOD,
                god.id,
                CosmosSubject(
                    number=len(found) + 1,
                    kind=CosmosSubjectKind.FOREIGN_GOD,
                    name=god.name,
                    title=god.title,
                    description=(god.description or "")[: content.cosmic_prompt_other_chars],
                ),
            )
        )
    return found[: content.cosmic_prompt_batch]


async def missing_cosmos_prompts(runtime: AgentRuntime, ids: Sequence[int] | None = None) -> int:
    runtime.require_llm("cosmos image prompts")
    async with runtime.database.read() as session:
        rules = await runtime.rules(session)
        scope = await load_scope(session, rules)
        subjects = await cosmos_subjects(scope, ids)
        if not subjects:
            return 0
        context = CosmosImagePromptsContext(
            rules=rules, world_name=scope.cosmos.name, cosmology=scope.cosmos.cosmology, tone=scope.cosmos.tone, subjects=[item for _, _, item in subjects]
        )
    output = await ask(
        runtime.model,
        rules,
        label=AgentRole.COSMOS_IMAGE_PROMPTS,
        system=(PromptId.COSMOS_IMAGE_PROMPTS_SYSTEM, context),
        user=(PromptId.COSMOS_IMAGE_PROMPTS_USER, context),
        output=CosmosImagePromptsOutput,
    )
    by_number = {subject.number: (kind, target) for kind, target, subject in subjects}
    limit = rules.content.cosmic_image_prompt_max_chars
    written = 0
    async with runtime.database.write() as session:
        for item in output.prompts:
            match = by_number.get(item.number)
            text = item.prompt.strip()[:limit]
            if match is None or len(text) < rules.content.image_prompt_min_chars:
                continue
            kind, target = match
            row: CosmicRow | None = await session.get(COSMIC_TABLES[kind], target)
            if row is not None and row.image_prompt is None:
                row.image_prompt = text
                written += 1
    if written:
        runtime.note(f"{written} cosmic bodies got an image prompt.")
    return written
