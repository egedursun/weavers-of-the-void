import asyncio
from dataclasses import dataclass, field

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.ask import ask
from aerona.agents.context.entity_detail import entity_detail
from aerona.agents.context.kept_names import keeps_name
from aerona.agents.context.scope import Scope, load_scope
from aerona.agents.context.world_header import world_header
from aerona.agents.fate.name_check import dialect_letters, fresh_name, name_problems, renamed_item, type_named_subtype
from aerona.agents.roles import AgentRole
from aerona.agents.runtime import AgentRuntime
from aerona.agents.text import ENGINE_DESCRIPTION_PREFIXES, sanitize, without_engine_prefix
from aerona.core.grammar import several
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.names import NameRepository
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityOrigin
from aerona.domain.models.phonology import Phonology
from aerona.engine.primitives.motifs import record_motifs
from aerona.engine.primitives.renames import name_in_text, rewrite_name
from aerona.language.alphabet import first_word
from aerona.prompts import PromptId
from aerona.prompts.contexts.narrative import DialectWarning, NamingContext
from aerona.prompts.schemas.fate import NamingsOutput
from aerona.prompts.schemas.shared import NamingItemOutput


@dataclass
class NamingReport:
    named: int = 0
    left: int = 0
    warnings: dict[int, list[DialectWarning]] = field(default_factory=dict)


@dataclass(frozen=True)
class NamingBatch:
    world_id: int
    ids: list[int]


async def pending_count(session: AsyncSession) -> int:
    return int(await session.scalar(select(func.count()).select_from(EntityRow).where(EntityRow.pending_name.is_(True))) or 0)


async def requeue_engine_drafts(session: AsyncSession) -> int:
    prefixed = or_(*(EntityRow.description.startswith(prefix) for prefix in ENGINE_DESCRIPTION_PREFIXES))
    caught = await session.execute(update(EntityRow).where(EntityRow.pending_name.is_(False), prefixed).values(pending_name=True, naming_attempts=0))
    await session.execute(update(EntityRow).where(EntityRow.pending_name.is_(True), EntityRow.naming_attempts > 0).values(naming_attempts=0))
    return int(getattr(caught, "rowcount", 0) or 0)


def called(text: str, others: tuple[str, ...], name: str) -> str:
    for other in others:
        text = name_in_text(text, other, name)
    return text


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
    if name != old:
        name = await repository.rename(entity, name)
        await rewrite_name(session, entity.id, old, name)
    proposed = item.name.strip()
    description = sanitize(without_engine_prefix(item.description) or without_engine_prefix(entity.description)) or entity.description
    entity.description = called(description, (proposed, old), name)
    entity.image_prompt = called(item.image_prompt.strip(), (proposed, old), name) or entity.image_prompt
    entity.pending_name = False
    await record_motifs(session, entity, item.motifs, epoch, replace=True)
    await session.flush()
    return old, name


async def next_batch(runtime: AgentRuntime, max_tries: int, busy: set[int]) -> NamingBatch | None:
    async with runtime.database.read() as session:
        rules = await runtime.rules(session)
        rows = await session.execute(
            select(EntityRow.id, EntityRow.world_id)
            .where(EntityRow.pending_name.is_(True), EntityRow.naming_attempts < max_tries, EntityRow.id.not_in(busy))
            .order_by(EntityRow.world_id, EntityRow.id)
            .limit(rules.naming.batch)
        )
        batch: NamingBatch | None = None
        for entity_id, world_id in rows:
            if batch is None:
                batch = NamingBatch(world_id, [])
            elif batch.world_id != world_id:
                break
            batch.ids.append(entity_id)
        return batch


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
            violation = await name_problems(session, rules, entity, item.name, phonology=phonology) if check else None
            if violation is not None and entity.naming_attempts < max_tries:
                report.warnings[item.id] = [violation]
                continue
            fresh = await fresh_name(session, rules, entity, phonology=phonology) if violation is not None else None
            chosen = renamed_item(item, fresh) if fresh else item
            if await apply_naming(session, chosen, epoch) is not None:
                report.named += 1
                report.warnings.pop(item.id, None)


@dataclass
class NamingPool:
    runtime: AgentRuntime
    report: NamingReport
    max_tries: int
    busy: set[int] = field(default_factory=set)
    claim: asyncio.Lock = field(default_factory=asyncio.Lock)
    failures: list[BaseException] = field(default_factory=list)
    succeeded: int = 0
    streak: int = 0

    async def claimed(self) -> NamingBatch | None:
        async with self.claim:
            batch = await next_batch(self.runtime, self.max_tries, self.busy)
            if batch is None:
                return None
            self.busy.update(batch.ids)
            async with self.runtime.database.write() as session:
                await session.execute(update(EntityRow).where(EntityRow.id.in_(batch.ids)).values(naming_attempts=EntityRow.naming_attempts + 1))
                remaining = await pending_count(session)
        self.runtime.note(f"{several(len(batch.ids), 'record', 'records')} born of the world's own course are being named ({remaining} remaining).")
        return batch

    async def work(self) -> None:
        parallel = (await self.runtime.current_rules()).naming.parallel
        while self.streak < parallel:
            batch = await self.claimed()
            if batch is None:
                return
            try:
                await run_batch(self.runtime, batch, self.report, self.max_tries)
            except Exception as error:
                self.failures.append(error)
                self.streak += 1
            else:
                self.succeeded += 1
                self.streak = 0
            finally:
                self.busy.difference_update(batch.ids)


async def name_pending_records(runtime: AgentRuntime) -> NamingReport:
    rules = await runtime.current_rules()
    max_tries = 1 + rules.naming.retries
    report = NamingReport()
    async with runtime.database.write() as session:
        caught = await requeue_engine_drafts(session)
    if caught:
        runtime.note(f"{several(caught, 'record', 'records')} still carrying the world engine's draft text were put back in line to be written.")
    pool = NamingPool(runtime, report, max_tries)
    await asyncio.gather(*(pool.work() for _ in range(rules.naming.parallel)))
    if pool.failures and (pool.succeeded == 0 or pool.streak >= rules.naming.parallel):
        raise pool.failures[-max(pool.streak, 1)]
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
