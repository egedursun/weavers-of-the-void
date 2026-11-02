import asyncio
from dataclasses import dataclass, field

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.ask import ask
from aerona.agents.context.entity_detail import entity_detail
from aerona.agents.context.scope import Scope, load_scope
from aerona.agents.context.tired_images import tired_images
from aerona.agents.context.world_header import world_header
from aerona.agents.fate.name_check import dialect_letters, fresh_name, name_problems, renamed_item, type_named_subtype
from aerona.agents.roles import AgentRole
from aerona.agents.runtime import AgentRuntime
from aerona.agents.text import ENGINE_DESCRIPTION_PREFIXES, sanitize, without_engine_prefix
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.names import NameRepository
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.domain.enums.entity import EntityFlag, EntityOrigin
from aerona.domain.models.phonology import Phonology
from aerona.engine.primitives.motifs import plain, record_motifs
from aerona.engine.primitives.renames import rewrite_name
from aerona.language.alphabet import first_word
from aerona.prompts import PromptId
from aerona.prompts.contexts.common import TiredImages
from aerona.prompts.contexts.narrative import DialectWarning, NamingContext
from aerona.prompts.schemas.fate import NamingsOutput
from aerona.prompts.schemas.shared import NamingItemOutput

KEPT_NAME_FLAGS = (EntityFlag.NAME_FROM_LANGUAGE, EntityFlag.FIXED_NAME, EntityFlag.NAMELESS)


@dataclass
class NamingReport:
    named: int = 0
    left: int = 0
    warnings: dict[int, list[DialectWarning]] = field(default_factory=dict)


@dataclass(frozen=True)
class NamingBatch:
    world_id: int
    ids: list[int]


def single_words(images: TiredImages) -> set[str]:
    return {motif.key for motif in images.motifs if len(motif.key.split()) == 1}


async def pending_count(session: AsyncSession) -> int:
    return int(await session.scalar(select(func.count()).select_from(EntityRow).where(EntityRow.pending_name.is_(True))) or 0)


async def keeps_name(session: AsyncSession, entity_id: int) -> bool:
    found = await session.scalar(select(EntityFlagRow.entity_id).where(EntityFlagRow.entity_id == entity_id, EntityFlagRow.flag.in_(KEPT_NAME_FLAGS)).limit(1))
    return found is not None


async def requeue_engine_drafts(session: AsyncSession) -> int:
    prefixed = or_(*(EntityRow.description.startswith(prefix) for prefix in ENGINE_DESCRIPTION_PREFIXES))
    caught = await session.execute(update(EntityRow).where(EntityRow.pending_name.is_(False), prefixed).values(pending_name=True, naming_attempts=0))
    await session.execute(update(EntityRow).where(EntityRow.pending_name.is_(True), EntityRow.naming_attempts > 0).values(naming_attempts=0))
    return int(getattr(caught, "rowcount", 0) or 0)


async def apply_naming(session: AsyncSession, item: NamingItemOutput, epoch: int) -> tuple[str, str] | None:
    entity = await session.get(EntityRow, item.id)
    if entity is None or not entity.pending_name:
        return None
    old = entity.name
    repository = EntityRepository(session)
    if await keeps_name(session, entity.id) or not item.name.strip():
        name = old
    elif item.name.strip() != old and await NameRepository(session).is_taken(item.name, entity.id):
        name = await NameRepository(session).unique_name(item.name)
    else:
        name = item.name.strip()
    if entity.origin is not EntityOrigin.ENGINE or not entity.subtype:
        entity.subtype = type_named_subtype(item.subtype, entity.entity_type) or entity.subtype
    entity.description = sanitize(without_engine_prefix(item.description) or without_engine_prefix(entity.description)) or entity.description
    entity.image_prompt = item.image_prompt.strip() or entity.image_prompt
    entity.pending_name = False
    await record_motifs(session, entity, plain(item.motifs), epoch, replace=True)
    if name != old:
        name = await repository.rename(entity, name)
        await rewrite_name(session, entity.id, old, name)
    await session.flush()
    return old, name


async def next_batches(runtime: AgentRuntime, max_tries: int) -> list[NamingBatch]:
    async with runtime.database.read() as session:
        rules = await runtime.rules(session)
        rows = await session.execute(
            select(EntityRow.id, EntityRow.world_id)
            .where(EntityRow.pending_name.is_(True), EntityRow.naming_attempts < max_tries)
            .order_by(EntityRow.world_id, EntityRow.id)
        )
        batches: list[NamingBatch] = []
        for entity_id, world_id in rows:
            if not batches or batches[-1].world_id != world_id or len(batches[-1].ids) >= rules.naming.batch:
                if len(batches) >= rules.naming.parallel:
                    break
                batches.append(NamingBatch(world_id, []))
            batches[-1].ids.append(entity_id)
        return batches


async def naming_context(scope: Scope, batch: NamingBatch, warnings: list[DialectWarning]) -> NamingContext:
    entities = [entity for entity in [await scope.session.get(EntityRow, entity_id) for entity_id in batch.ids] if entity is not None]
    world = scope.worlds.get(batch.world_id)
    return NamingContext(
        lore_language=scope.cosmos.lore_language,
        world_name=scope.cosmos.name,
        target_world=world.name if world is not None and scope.multi_world else None,
        world_header=await world_header(scope, batch.world_id if scope.multi_world else None),
        records=[await entity_detail(scope, entity) for entity in entities],
        dialect_warnings=warnings,
        tired_images=await tired_images(scope, batch.world_id),
    )


async def run_batch(runtime: AgentRuntime, batch: NamingBatch, report: NamingReport, max_tries: int) -> None:
    async with runtime.database.read() as session:
        rules = await runtime.rules(session)
        scope = await load_scope(session, rules)
        warnings = [warning for entity_id in batch.ids for warning in report.warnings.get(entity_id, [])]
        context = await naming_context(scope, batch, warnings)
        world = scope.worlds.get(batch.world_id)
        phonology = world.phonology if world is not None else None
        if phonology is None and scope.primary_world is not None:
            phonology = scope.primary_world.phonology
        tired = single_words(context.tired_images)
    output = await ask(
        runtime.model, rules, label=AgentRole.NAMING, system=(PromptId.NAMING_SYSTEM, context), user=(PromptId.NAMING_USER, context), output=NamingsOutput
    )
    async with runtime.database.write() as session:
        epoch = (await load_scope(session, rules)).epoch
        for item in output.namings:
            if item.id not in batch.ids:
                continue
            entity = await session.get(EntityRow, item.id)
            if entity is None:
                continue
            check = rules.naming.dialect_check and not await keeps_name(session, entity.id)
            violation = await name_problems(session, rules, entity, item.name, phonology=phonology, tired=tired) if check else None
            if violation is not None and entity.naming_attempts < max_tries:
                report.warnings[item.id] = [violation]
                continue
            fresh = await fresh_name(session, rules, entity, phonology=phonology, tired=tired) if violation is not None else None
            chosen = renamed_item(item, fresh) if fresh else item
            if await apply_naming(session, chosen, epoch) is not None:
                report.named += 1
                report.warnings.pop(item.id, None)


async def name_pending_records(runtime: AgentRuntime) -> NamingReport:
    rules = await runtime.current_rules()
    max_tries = 1 + rules.naming.retries
    report = NamingReport()
    async with runtime.database.write() as session:
        caught = await requeue_engine_drafts(session)
    if caught:
        runtime.note(f"{caught} records still carrying the world engine's draft text were put back in line to be written.")
    while True:
        batches = await next_batches(runtime, max_tries)
        if not batches:
            break
        ids = [entity_id for batch in batches for entity_id in batch.ids]
        async with runtime.database.write() as session:
            await session.execute(update(EntityRow).where(EntityRow.id.in_(ids)).values(naming_attempts=EntityRow.naming_attempts + 1))
            remaining = await pending_count(session)
        runtime.note(f"{len(ids)} records born of the world's own course are being named in {len(batches)} batches ({remaining} remaining).")
        results = await asyncio.gather(*(run_batch(runtime, batch, report, max_tries) for batch in batches), return_exceptions=True)
        failures = [result for result in results if isinstance(result, BaseException)]
        if len(failures) == len(results):
            raise failures[0]
    async with runtime.database.read() as session:
        report.left = await pending_count(session)
    if report.named or report.left:
        tail = f"; {report.left} still carry draft text and are tried again at the next epoch end" if report.left else ""
        runtime.note(f"{report.named} records were named{tail}.")
    return report


def dialect_violation(entity_id: int, name: str, phonology: Phonology | None) -> DialectWarning | None:
    if phonology is None:
        return None
    root = first_word(name)
    letters = dialect_letters(root, phonology)
    return DialectWarning(id=entity_id, name=name, root=root, letters=letters) if letters else None
