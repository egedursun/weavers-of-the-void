from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.chronicle import record_line
from aerona.agents.fate.facts import entities_in_text, usable
from aerona.agents.fate.naming import apply_naming
from aerona.agents.fate.rollback import roll_back_rejection
from aerona.agents.fate.threads import single_world_links, thread_closable
from aerona.agents.text import clean_fate_note, sanitize, shorten_rationale, strip_meta_sentences
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.lexicon import add_lexeme
from aerona.db.tables.entities import CreationVerdictRow, EntityRow
from aerona.db.tables.lore import FateRewardRow, LexemeRow, ThreadRow, lexeme_key
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.agent import Verdict
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind, PartOfSpeech, ThreadStatus
from aerona.domain.enums.entity import EntityStatus, EntityType, ProphecyReading
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.node import ActorKind
from aerona.engine.gods.progress import grant_progress
from aerona.engine.gods.rewards import adjust_reward
from aerona.engine.lore.prophecy import reward_fulfilment
from aerona.engine.primitives.canon_facts import FactDraft, apply_fate_facts, certain_facts
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.motifs import record_motifs
from aerona.engine.primitives.threads import advance_story, close_story, open_story
from aerona.prompts.schemas.fate import ClosedThreadOutput, FateJudgmentOutput, VerdictDecision, VerdictOutput
from aerona.rules.registry import Rules

PERCENT = 100
Marker = Callable[[AsyncSession], Awaitable[None]]
READING_TEXTS = {
    ProphecyReading.TRUE: "The prophecy came true as it was spoken",
    ProphecyReading.MISREAD: "The prophecy came true, but not as everyone expected",
    ProphecyReading.SELF_FULFILLING: "The prophecy came true because people believed it",
}

FIXED_REASON = "Fate fixed"


@dataclass
class FateRuling:
    epoch: int
    judged_epochs: dict[int, int]
    pending_ids: set[int]
    prophecy_ids: set[int]
    output: FateJudgmentOutput | None
    verdicts: list[VerdictOutput]
    debt: int | None
    fate_off: bool = False


@dataclass
class FateApplied:
    rejected: list[str] = field(default_factory=list)
    rejected_ids: list[int] = field(default_factory=list)
    fixed: list[str] = field(default_factory=list)
    limbo: list[int] = field(default_factory=list)
    renamed: list[tuple[str, str]] = field(default_factory=list)
    fate_debt: int | None = None


def first_by_id[T](items: Sequence[T], key: Callable[[T], int]) -> list[T]:
    seen: set[int] = set()
    unique = []
    for item in items:
        identifier = key(item)
        if identifier not in seen:
            seen.add(identifier)
            unique.append(item)
    return unique


async def record_verdict(session: AsyncSession, entity: EntityRow, verdict: Verdict, rationale: str | None, epoch: int) -> None:
    row = await session.get(CreationVerdictRow, entity.id)
    if row is None:
        session.add(CreationVerdictRow(entity_id=entity.id, epoch=entity.birth_epoch, verdict=verdict, rationale=rationale, judged_epoch=epoch))
        return
    row.verdict = verdict
    row.rationale = rationale
    row.judged_epoch = epoch


async def apply_verdicts(session: AsyncSession, rules: Rules, ruling: FateRuling, applied: FateApplied) -> None:
    words = rules.fate.reason_max_words
    for verdict in first_by_id(ruling.verdicts, lambda item: item.id):
        entity = await session.get(EntityRow, verdict.id)
        if verdict.id not in ruling.judged_epochs or entity is None or entity.status is not EntityStatus.CANON:
            continue
        rationale = shorten_rationale(verdict.rationale, words)
        await record_motifs(session, entity, verdict.motifs, ruling.epoch, replace=True)
        if ruling.fate_off:
            await record_verdict(session, entity, Verdict.UNJUDGED, rationale, ruling.epoch)
            continue
        if verdict.decision is VerdictDecision.REJECT:
            await EntityRepository(session).set_status(entity, EntityStatus.REJECTED, ruling.epoch, rationale or "Fate rejected.")
            await record_verdict(session, entity, Verdict.REJECTED, rationale, ruling.epoch)
            await record_line(
                session,
                rules,
                "fate.rejected",
                roles={IncidentRole.SUBJECT: entity.id},
                facts={"detail": f": {rationale}" if rationale else ""},
                kind=ChronicleKind.FATE,
                son_id=entity.creator_son_id,
            )
            applied.rejected.append(entity.name)
            applied.rejected_ids.append(entity.id)
        elif verdict.decision is VerdictDecision.FIX and not verdict.fixed_description.strip():
            await record_verdict(session, entity, Verdict.LIMBO, rationale, ruling.epoch)
            applied.limbo.append(entity.id)
        elif verdict.decision is VerdictDecision.FIX:
            entity.description = strip_meta_sentences(sanitize(verdict.fixed_description)) or entity.description
            entity.fate_note = f"Fate fixed: {rationale}" if rationale else "Fate fixed."
            await record_verdict(session, entity, Verdict.FIXED, rationale, ruling.epoch)
            await adjust_reward(session, rules, entity.id, rules.son_tools.fix_take_back_pct, raise_only=True, reason=FIXED_REASON)
            await record_line(
                session,
                rules,
                "fate.fixed",
                roles={IncidentRole.SUBJECT: entity.id},
                facts={"detail": f": {rationale}" if rationale else ""},
                kind=ChronicleKind.FATE,
                son_id=entity.creator_son_id,
            )
            applied.fixed.append(entity.name)
        else:
            entity.fate_note = rationale or "Fate accepted."
            await record_verdict(session, entity, Verdict.ACCEPTED, rationale, ruling.epoch)


async def apply_prophecies(session: AsyncSession, rules: Rules, ruling: FateRuling, output: FateJudgmentOutput) -> None:
    for item in first_by_id(output.fulfilled_prophecies, lambda prophecy: prophecy.id):
        prophecy = await session.get(EntityRow, item.id)
        if item.id not in ruling.prophecy_ids or prophecy is None or prophecy.status is not EntityStatus.CANON:
            continue
        how = clean_fate_note(item.how)
        prophecy.status = EntityStatus.FULFILLED
        prophecy.fate_note = how or "The prophecy came true."
        prophecy.prophecy_reading = item.reading
        bonds = BondRepository(session)
        for target in await entities_in_text(session, item.how, prophecy.world_id, prophecy.id):
            await bonds.connect(BondDraft(prophecy.id, target.id, BondKind.PROPHESIES, ruling.epoch, "came true"))
        await record_line(
            session,
            rules,
            "fate.prophecy_fulfilled",
            roles={IncidentRole.SUBJECT: prophecy.id},
            facts={"reading": item.reading, "reading_text": READING_TEXTS[item.reading], "how": how or ""},
            kind=ChronicleKind.PROPHECY,
            son_id=prophecy.creator_son_id,
        )
        ctx = await manual_context(session, "fate_prophecy", rules, key=str(prophecy.id))
        await reward_fulfilment(ctx, prophecy, misread=item.reading is ProphecyReading.MISREAD)


async def apply_threads(session: AsyncSession, rules: Rules, ruling: FateRuling, output: FateJudgmentOutput) -> None:
    epoch = ruling.epoch
    closing: list[ClosedThreadOutput] = []
    if output.resolved_story is not None:
        closing.append(ClosedThreadOutput(id=output.resolved_story.id, how=output.resolved_story.how))
    closing.extend(output.closed_stories)
    closed_ids = {item.id for item in closing}
    for advanced in output.advanced_stories[: rules.fate.thread_advance_cap]:
        thread = await session.get(ThreadRow, advanced.id)
        record = await session.get(EntityRow, advanced.record_id)
        how = clean_fate_note(advanced.how)
        if thread is None or record is None or record.birth_epoch != epoch or not usable(record) or not how:
            continue
        if not await advance_story(session, thread, record.id, epoch):
            continue
        if thread.id not in closed_ids:
            await record_line(session, rules, "fate.story_advanced", roles={IncidentRole.SUBJECT: record.id}, facts={"how": how}, kind=ChronicleKind.FATE)
    for item in first_by_id(closing, lambda closed: closed.id):
        thread = await session.get(ThreadRow, item.id)
        if thread is None or thread.status is ThreadStatus.CLOSED or not await thread_closable(session, rules, thread, epoch):
            continue
        how = clean_fate_note(item.how) or ""
        related = await close_story(session, thread, how or None, epoch)
        await record_line(session, rules, "fate.story_closed", roles={IncidentRole.SUBJECT: list(related)}, facts={"how": how}, kind=ChronicleKind.FATE)


async def new_stories(session: AsyncSession, ruling: FateRuling, output: FateJudgmentOutput, limit: int) -> None:
    for item in output.new_stories[:limit]:
        await open_story(session, sanitize(item.text), await single_world_links(session, item.related_ids), ruling.epoch)


async def apply_facts(session: AsyncSession, rules: Rules, ruling: FateRuling, output: FateJudgmentOutput) -> None:
    touched = set(ruling.judged_epochs) | ruling.pending_ids
    drafts = [FactDraft(fact.subject_id, fact.relation, fact.object_id, fact.object) for fact in output.facts]
    await apply_fate_facts(session, rules, drafts, ruling.epoch, touched)
    await certain_facts(session, touched, ruling.epoch)


async def apply_words(session: AsyncSession, rules: Rules, ruling: FateRuling, output: FateJudgmentOutput) -> None:
    for item in output.words[: rules.fate.words_per_epoch_cap]:
        language = await session.get(EntityRow, item.language_id)
        word, meaning = item.word.strip(), item.meaning.strip()
        if language is None or language.entity_type is not EntityType.LANGUAGE or language.status is not EntityStatus.CANON or not word or not meaning:
            continue
        exists = await session.scalar(select(LexemeRow.id).where(LexemeRow.language_entity_id == language.id, LexemeRow.word_key == lexeme_key(word)).limit(1))
        if exists is not None:
            continue
        await add_lexeme(
            session,
            LexemeRow(
                language_entity_id=language.id,
                word=word,
                meaning=meaning,
                part_of_speech=PartOfSpeech.NOUN,
                etymology=item.origin.strip() or f"Born in Age {ruling.epoch}",
                added_by_kind=ActorKind.FATE,
                epoch=ruling.epoch,
            ),
        )


async def reward_streak(session: AsyncSession, son_id: int, epoch: int, window: int) -> int:
    statement = select(func.count(func.distinct(FateRewardRow.epoch))).where(
        FateRewardRow.son_id == son_id, FateRewardRow.epoch.between(epoch - window, epoch - 1)
    )
    return int(await session.scalar(statement) or 0)


async def apply_rewards(session: AsyncSession, rules: Rules, ruling: FateRuling, output: FateJudgmentOutput) -> None:
    fate = rules.fate
    cap = max(1, fate.reward_cap)
    for item in output.rewards:
        son = await session.get(SonRow, item.son_id)
        if son is None:
            continue
        given = int(
            await session.scalar(
                select(func.coalesce(func.sum(FateRewardRow.fame), 0)).where(FateRewardRow.son_id == son.id, FateRewardRow.epoch == ruling.epoch)
            )
            or 0
        )
        streak = await reward_streak(session, son.id, ruling.epoch, fate.reward_streak_window) if fate.reward_streak_window else 0
        raw = max(1, min(item.fame, cap)) * (fate.reward_streak_keep_pct / PERCENT) ** streak
        fame = min(round(raw), fate.reward_cap - given)
        if fame <= 0:
            continue
        xp = fame * fate.xp_per_renown
        reason = clean_fate_note(item.reason)
        session.add(FateRewardRow(son_id=son.id, epoch=ruling.epoch, fame=fame, xp=xp, reason=reason))
        await record_line(
            session,
            rules,
            "fate.reward",
            roles={IncidentRole.BENEFICIARY: son.id},
            facts={"fame": fame, "xp": xp, "detail": f": {reason}" if reason else "."},
            kind=ChronicleKind.FATE,
            son_id=son.id,
        )
        await grant_progress(await manual_context(session, "fate_reward", rules, key=str(son.id)), son, xp=xp, fame=fame)


async def apply_namings(session: AsyncSession, ruling: FateRuling, output: FateJudgmentOutput, applied: FateApplied) -> None:
    for item in first_by_id(output.namings, lambda naming: naming.id):
        if item.id not in ruling.pending_ids:
            continue
        renamed = await apply_naming(session, item, ruling.epoch)
        if renamed is not None and renamed[0] != renamed[1]:
            applied.renamed.append(renamed)


async def apply_fate_ruling(session: AsyncSession, rules: Rules, ruling: FateRuling, marker: Marker | None = None) -> FateApplied:
    applied = FateApplied()
    await apply_verdicts(session, rules, ruling, applied)
    output = ruling.output
    if output is not None:
        await apply_namings(session, ruling, output, applied)
        await apply_prophecies(session, rules, ruling, output)
        await apply_threads(session, rules, ruling, output)
        await apply_facts(session, rules, ruling, output)
        await new_stories(session, ruling, output, rules.fate.new_thread_cap)
        await apply_words(session, rules, ruling, output)
        await apply_rewards(session, rules, ruling, output)
    debt = ruling.debt
    if applied.limbo:
        debt = min([debt if debt is not None else ruling.epoch, *(ruling.judged_epochs[entity_id] for entity_id in applied.limbo)])
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.fate_debt_epoch = debt
    applied.fate_debt = debt
    for entity_id in applied.rejected_ids:
        await roll_back_rejection(session, rules, entity_id)
    if marker is not None:
        await marker(session)
    await session.flush()
    return applied
