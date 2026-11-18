from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.language import EPOCH_WORD_SEED_PREFIX
from aerona.core.grammar import several
from aerona.db.repositories.lexicon import add_lexeme
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.lore import LexemeRow
from aerona.domain.enums.entity import EntityFlag, EntityStatus
from aerona.domain.enums.epoch import EngineStage, EpochPhase, EpochStepKind, EpochStepStatus
from aerona.domain.enums.node import ActorKind
from aerona.engine.cosmos.foreign_gods import birth_local_gods
from aerona.engine.phase import Phase
from aerona.engine.pipeline import POST_TRANSITION_ORDER, TOLERANT_TRANSITION_STEPS, TRANSITION_ORDER, after_transition, current_environment, disabled_by_rules
from aerona.engine.primitives.local_language import local_language_of
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.naming import Namer
from aerona.epoch.context import EpochContext
from aerona.epoch.phases.engine_tick import run_engine_stage
from aerona.epoch.state import mark_step, step_settled
from aerona.language.epoch_words import EPOCH_WORD_TYPES, EpochWordSource, plan_epoch_words
from aerona.language.generator import NameKind
from aerona.rules.registry import Rules

WORD_STATUSES = (EntityStatus.CANON, EntityStatus.DEAD)
LOCAL_GODS_PHASE = "local_gods"


async def add_epoch_words(session: AsyncSession, rules: Rules, epoch: int) -> int:
    records = list(
        await session.scalars(
            select(EntityRow)
            .where(
                EntityRow.birth_epoch == epoch,
                EntityRow.entity_type.in_(EPOCH_WORD_TYPES),
                EntityRow.status.in_(WORD_STATUSES),
                EntityRow.pending_name.is_(False),
            )
            .order_by(EntityRow.power_level.desc(), EntityRow.id)
        )
    )
    named = set(await session.scalars(select(EntityFlagRow.entity_id).where(EntityFlagRow.flag == EntityFlag.NAME_FROM_LANGUAGE)))
    recorded = set(await session.scalars(select(LexemeRow.added_by_node_id).where(LexemeRow.added_by_kind == ActorKind.ENGINE)))
    by_id: dict[int, EntityRow] = {}
    sources: list[EpochWordSource] = []
    for record in records:
        language = await local_language_of(session, rules, record)
        if language is not None:
            by_id[language.id] = language
        sources.append(
            EpochWordSource(
                entity_id=record.id,
                entity_type=record.entity_type,
                name=record.name,
                subtype=record.subtype,
                language_id=language.id if language is not None else None,
                named_from_language=record.id in named,
                already_recorded=record.id in recorded,
            )
        )
    namer = Namer(session, rules)
    words: dict[tuple[int, str], str | None] = {}
    for source in sources:
        if source.language_id is not None and not source.already_recorded:
            seed = f"{EPOCH_WORD_SEED_PREFIX}:{source.entity_id}"
            words[(source.language_id, seed)] = await namer.from_language(by_id[source.language_id], seed, NameKind.GENERAL)
    known: dict[int, set[str]] = defaultdict(set)
    for language_id, word in await session.execute(select(LexemeRow.language_entity_id, LexemeRow.word).where(LexemeRow.language_entity_id.in_(list(by_id)))):
        known[language_id].add(word)
    planned = plan_epoch_words(sources, epoch, lambda language_id, seed: words.get((language_id, seed)), known, rules)
    for item in planned:
        await add_lexeme(
            session,
            LexemeRow(
                language_entity_id=item.language_id,
                word=item.entry.word,
                meaning=item.entry.meaning,
                part_of_speech=item.entry.part_of_speech,
                etymology=item.entry.origin or None,
                added_by_kind=ActorKind.ENGINE,
                added_by_node_id=item.entity_id,
                epoch=epoch,
            ),
        )
    await session.flush()
    return len(planned)


def transition_order() -> tuple[Phase, ...]:
    return TRANSITION_ORDER


def post_transition_order() -> tuple[Phase, ...]:
    return POST_TRANSITION_ORDER


async def transition(ec: EpochContext) -> None:
    await ec.enter_phase(EpochPhase.TRANSITION)
    async with ec.database.read() as session:
        words_done = await step_settled(session, ec.epoch, EpochStepKind.EPOCH_WORDS)
        gods_done = await step_settled(session, ec.epoch, EpochStepKind.LOCAL_GODS)
    if not words_done:
        try:
            async with ec.database.write() as session:
                count = await add_epoch_words(session, await ec.runtime.rules(session), ec.epoch)
                await mark_step(session, ec.epoch, EpochStepKind.EPOCH_WORDS, EpochStepStatus.DONE)
            if count:
                ec.runtime.note(f"{several(count, 'new word', 'new words')} entered the languages.")
        except Exception as error:
            ec.runtime.error(f"Epoch words: {error}")
    if not gods_done:
        try:
            async with ec.database.write() as session:
                rules = await ec.runtime.rules(session)
                if LOCAL_GODS_PHASE in disabled_by_rules(rules):
                    born: list[ForeignGodRow] = []
                    await mark_step(session, ec.epoch, EpochStepKind.LOCAL_GODS, EpochStepStatus.SKIPPED)
                else:
                    ctx = await manual_context(session, LOCAL_GODS_PHASE, rules, ec.runtime.publish)
                    born = await birth_local_gods(ctx)
                    await mark_step(session, ec.epoch, EpochStepKind.LOCAL_GODS, EpochStepStatus.DONE)
            for god in born:
                ec.runtime.note(f"A sleeping local god was born: {god.name}.")
        except Exception as error:
            ec.runtime.error(f"Local god: {error}")
    environment = await current_environment(ec.database, ec.runtime.publish, phase=EpochPhase.TRANSITION)
    if environment.epoch == ec.epoch:
        await run_engine_stage(ec, EngineStage.TRANSITION, transition_order(), environment, TOLERANT_TRANSITION_STEPS)
    advanced = await current_environment(ec.database, ec.runtime.publish, phase=EpochPhase.NOT_STARTED)
    post_environment = after_transition(advanced) if advanced.epoch == ec.epoch else advanced
    await run_engine_stage(ec, EngineStage.AFTER_TRANSITION, post_transition_order(), post_environment, TOLERANT_TRANSITION_STEPS)
    async with ec.database.write() as session:
        await mark_step(session, ec.epoch, EpochStepKind.TRANSITION, EpochStepStatus.DONE)
    await ec.complete_phase(EpochPhase.TRANSITION)
