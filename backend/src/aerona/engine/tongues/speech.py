from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.tongues import REGISTERS
from aerona.core.random import SeededRandom
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import LexemeRow
from aerona.db.tables.tongues import LanguageGrammarRow
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.tongues import WordRegister
from aerona.engine.context import TickContext
from aerona.engine.primitives.queries import spoken_language
from aerona.engine.recording.record import record
from aerona.engine.relations.book import ensure_relation, shift


async def tongue_of(session: AsyncSession, mortal: EntityRow) -> int | None:
    for holder in (mortal.id, mortal.location_id, mortal.affiliated_entity_id):
        found = await spoken_language(session, holder) if holder is not None else None
        if found is not None:
            return found.id
    return None


async def has_register(session: AsyncSession, language_id: int, register: WordRegister) -> bool:
    found = await session.scalar(select(LexemeRow.id).where(LexemeRow.language_entity_id == language_id, LexemeRow.register == register).limit(1))
    return found is not None


async def honours_rank(session: AsyncSession, language_id: int) -> bool:
    grammar = await session.get(LanguageGrammarRow, language_id)
    return grammar is not None and grammar.honorific_levels > 0


async def offend(ctx: TickContext, actor: EntityRow, target: EntityRow, register: WordRegister, place: int | None) -> None:
    rule = REGISTERS[register].insult_rule
    loss = int(getattr(ctx.rules.tongues, rule)) if rule is not None else 0
    heard = await ensure_relation(ctx.session, target.id, actor.id, ctx.epoch)
    if heard is not None:
        shift(ctx.rules, heard, ctx.epoch, friendship=-loss, rivalry=loss / 2)
    await record(ctx, "social.taboo_word", roles={IncidentRole.ACTOR: actor.id, IncidentRole.TARGET: target.id}, facts={"register": register}, place=place)


async def slips(ctx: TickContext, actor: EntityRow, target: EntityRow, *, hostile: bool, rng: SeededRandom, place: int | None) -> WordRegister | None:
    language = await tongue_of(ctx.session, actor)
    if language is None:
        return None
    if hostile and await has_register(ctx.session, language, WordRegister.TABOO) and rng.chance(ctx.rules.tongues.taboo_slip_pct):
        await offend(ctx, actor, target, WordRegister.TABOO, place)
        return WordRegister.TABOO
    lesser = actor.power_level < target.power_level
    if lesser and await honours_rank(ctx.session, language) and rng.chance(ctx.rules.tongues.honorific_slip_pct):
        await offend(ctx, actor, target, WordRegister.HONORIFIC, place)
        return WordRegister.HONORIFIC
    return None
