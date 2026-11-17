from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.schema import LEXEME_TEXT_MAX_LENGTH, LEXEME_WORD_MAX_LENGTH, NAME_MAX_LENGTH
from aerona.db.tables.discovery import NameExonymRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import LexemeRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.tongues import MeaningShiftRow
from aerona.db.write_guard import held
from aerona.domain.enums.culture import TraditionFunction
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.tongues import SenseShift, WordRegister
from aerona.engine.context import TickContext
from aerona.engine.gods.queries import worshippers_of
from aerona.engine.lore.taboos import kept
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.queries import canon, spoken_language
from aerona.engine.primitives.stats import stat_or
from aerona.engine.recording.record import record as record_incident
from aerona.engine.tongues.grammar import compounds, head_first

ALSO = "; also "
DRIFTS = (SenseShift.BROADENED, SenseShift.NARROWED, SenseShift.PEJORATIVE, SenseShift.AMELIORATIVE, SenseShift.RESTORED)
PAIR = 2


@dataclass
class DriftTally:
    shifted: int = 0
    veiled: int = 0


def clipped(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit].rstrip()


async def common_words(ctx: TickContext, language_id: int) -> list[LexemeRow]:
    rows = await ctx.session.scalars(
        select(LexemeRow).where(LexemeRow.language_entity_id == language_id, LexemeRow.register == WordRegister.COMMON).order_by(LexemeRow.id)
    )
    return list(rows)


def record(ctx: TickContext, lexeme: LexemeRow, shift: SenseShift, old: str, cause: int | None = None) -> MeaningShiftRow:
    row = MeaningShiftRow(
        lexeme_id=lexeme.id,
        shift=shift,
        old_meaning=clipped(old, NAME_MAX_LENGTH),
        new_meaning=clipped(lexeme.meaning, NAME_MAX_LENGTH),
        cause_node_id=cause,
        epoch=ctx.epoch,
    )
    ctx.session.add(row)
    return row


async def shift_word(ctx: TickContext, language: EntityRow, tally: DriftTally) -> MeaningShiftRow | None:
    words = await common_words(ctx, language.id)
    rng = ctx.rng(f"drift.{language.id}.{ctx.epoch}")
    if not words or not rng.chance(ctx.rules.semantic_drift.drift_pct):
        return None
    word = rng.pick(words)
    shift = rng.pick(list(DRIFTS))
    old = word.meaning
    other: LexemeRow | None = None
    if shift is SenseShift.BROADENED:
        others = [item for item in words if item.id != word.id and item.part_of_speech == word.part_of_speech and ALSO not in item.meaning]
        if not others or ALSO in word.meaning:
            return None
        other = rng.pick(others)
        word.meaning = clipped(f"{word.meaning}{ALSO}{other.meaning}", LEXEME_TEXT_MAX_LENGTH)
        other.register = WordRegister.ARCHAIC
    elif shift is SenseShift.NARROWED:
        if ALSO not in word.meaning:
            return None
        word.meaning = word.meaning.split(ALSO)[0]
    elif shift is SenseShift.RESTORED:
        archaic = list(
            await ctx.session.scalars(
                select(LexemeRow).where(LexemeRow.language_entity_id == language.id, LexemeRow.register == WordRegister.ARCHAIC).order_by(LexemeRow.id)
            )
        )
        if not archaic:
            return None
        word = rng.pick(archaic)
        old = word.meaning
        word.register = WordRegister.COMMON
    tally.shifted += 1
    row = record(ctx, word, shift, old)
    if other is not None:
        row.replaced_by_id = other.id
    return row


async def veiled(ctx: TickContext, language_id: int, node_id: int) -> bool:
    found = await ctx.session.scalar(
        select(MeaningShiftRow.id)
        .join(LexemeRow, LexemeRow.id == MeaningShiftRow.lexeme_id)
        .where(LexemeRow.language_entity_id == language_id, MeaningShiftRow.cause_node_id == node_id, MeaningShiftRow.shift == SenseShift.EUPHEMISM)
        .limit(1)
    )
    return found is not None


async def veil(ctx: TickContext, language: EntityRow, node_id: int, name: str) -> LexemeRow | None:
    words = await common_words(ctx, language.id)
    if len(words) < PAIR or held(language.id):
        return None
    rng = ctx.rng(f"veil.{language.id}.{node_id}")
    modifier, head = rng.sample(words, PAIR)
    first, second = (head, modifier) if await head_first(ctx.session, language.id) else (modifier, head)
    joined = f"{first.word}{second.word.casefold()}" if await compounds(ctx.session, language.id) else f"{first.word} {second.word.casefold()}"
    gloss = clipped(f"the {first.meaning.split(ALSO)[0]} {second.meaning.split(ALSO)[0]}", LEXEME_TEXT_MAX_LENGTH)
    euphemism = LexemeRow(
        language_entity_id=language.id,
        word=clipped(joined, LEXEME_WORD_MAX_LENGTH),
        meaning=clipped(f"{gloss}, said instead of {name}", LEXEME_TEXT_MAX_LENGTH),
        etymology=f"from {first.word} and {second.word}",
        added_by_kind=ActorKind.ENGINE,
        added_by_node_id=None,
        epoch=ctx.epoch,
        register=WordRegister.COMMON,
    )
    ctx.session.add(euphemism)
    ctx.session.add(
        LexemeRow(
            language_entity_id=language.id,
            word=clipped(name, LEXEME_WORD_MAX_LENGTH),
            meaning=clipped(f"the old name of {name}, kept in sacred speech", LEXEME_TEXT_MAX_LENGTH),
            added_by_kind=ActorKind.ENGINE,
            added_by_node_id=None,
            epoch=ctx.epoch,
            register=WordRegister.SACRED,
        )
    )
    await ctx.session.flush()
    exonym = await ctx.session.get(NameExonymRow, (node_id, language.id))
    if exonym is None:
        exonym = NameExonymRow(node_id=node_id, language_entity_id=language.id, form=euphemism.word, gloss=gloss, epoch=ctx.epoch, locked=[])
        ctx.session.add(exonym)
    elif "form" not in exonym.locked:
        exonym.form, exonym.gloss, exonym.epoch = euphemism.word, gloss, ctx.epoch
    row = record(ctx, euphemism, SenseShift.EUPHEMISM, name, node_id)
    row.new_meaning = clipped(gloss, NAME_MAX_LENGTH)
    await record_incident(
        ctx, "tongues.taboo", roles={IncidentRole.SUBJECT: language.id, IncidentRole.TARGET: node_id}, facts={"name": name, "euphemism": euphemism.word}
    )
    return euphemism


async def dreaded(ctx: TickContext) -> list[tuple[int, str, list[int]]]:
    table = ctx.rules.semantic_drift
    atlas = await RegionAtlas.load(ctx.session)
    found: list[tuple[int, str, list[int]]] = []
    for beast in await canon(ctx.session, [EntityType.BEAST]):
        region = atlas.top_region(beast.id)
        if stat_or(beast, "terror", 0) >= table.taboo_terror and region is not None:
            found.append((beast.id, beast.name, sorted(atlas.communities_in(region))))
    return found


async def holy(ctx: TickContext) -> list[tuple[int, str, list[int]]]:
    found: list[tuple[int, str, list[int]]] = []
    for son in await ctx.session.scalars(select(SonRow).where(SonRow.status == SonStatus.ACTIVE).order_by(SonRow.id)):
        folk = [row.id for row in await worshippers_of(ctx.session, son.id)]
        feared = Domain.DEATH in {son.domain_primary, son.domain_secondary}
        keepers = [community for community in folk if feared or await kept(ctx.session, community, TraditionFunction.TABOO)]
        if keepers:
            found.append((son.id, son.name, keepers))
    return found


async def lift_names(ctx: TickContext, tally: DriftTally) -> None:
    table = ctx.rules.semantic_drift
    for node_id, name, communities in [*await dreaded(ctx), *await holy(ctx)]:
        for community in communities:
            if tally.veiled + tally.shifted >= table.per_epoch:
                return
            language = await spoken_language(ctx.session, community)
            if language is None or held(community) or await veiled(ctx, language.id, node_id):
                continue
            boost = 2 if await kept(ctx.session, community, TraditionFunction.TABOO) else 1
            if ctx.rng(f"taboo.{language.id}.{node_id}.{ctx.epoch}").chance(table.taboo_pct * boost) and await veil(ctx, language, node_id, name) is not None:
                tally.veiled += 1


async def drift_meanings(ctx: TickContext, tally: DriftTally) -> None:
    for language in await canon(ctx.session, [EntityType.LANGUAGE]):
        if tally.shifted >= ctx.rules.semantic_drift.per_epoch:
            break
        if not held(language.id):
            await shift_word(ctx, language, tally)
    await lift_names(ctx, tally)
    await ctx.session.flush()
