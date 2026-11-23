from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.tongues import DRIFTS, REGISTERS, SHIFTS
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.lore import LexemeRow
from aerona.db.tables.tongues import LanguageGrammarRow, MeaningShiftRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import PartOfSpeech
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.tongues import SenseShift, WordRegister
from aerona.engine.tongues.meaning import DriftTally, shift_word, veil
from aerona.engine.tongues.speech import slips
from tests.engine.core.factories import CoreWorld, bond, mortal, settlement
from tests.engine.tongues.helpers import tongue, tuned, words


def test_shift_weights_and_register_insults_come_from_the_catalogue() -> None:
    assert SenseShift.EXTENDED in DRIFTS and SenseShift.ASSOCIATED in DRIFTS and SenseShift.EUPHEMISM not in DRIFTS
    assert SHIFTS[SenseShift.EXTENDED].rule == "extended_rate"
    assert REGISTERS[WordRegister.TABOO].insult_rule == "taboo_insult" and REGISTERS[WordRegister.TECHNICAL].marks_members


async def test_a_meaning_carried_by_nearness_turns_a_place_name_toward_its_people(session: AsyncSession, world: CoreWorld) -> None:
    rates = {f"{shift.value}_rate": 0 for shift in DRIFTS} | {"associated_rate": 100}
    ctx = await tuned(session, tongues=rates, semantic_drift={"drift_pct": 100})
    language = await tongue(session, world)
    session.add(
        LexemeRow(
            language_entity_id=language.id, word="Vael", meaning="the valley", part_of_speech=PartOfSpeech.PLACE_NAME, added_by_kind=ActorKind.ENGINE, epoch=1
        )
    )
    await session.flush()
    row = await shift_word(ctx, language, DriftTally())
    assert row is not None and row.shift is SenseShift.ASSOCIATED and "those of" in row.new_meaning


async def test_a_veiled_name_becomes_a_word_not_to_be_said(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await tuned(session)
    language = await tongue(session, world)
    words(session, language, ("keta", "stone"), ("mora", "water"), ("sela", "night"))
    await session.flush()
    await veil(ctx, language, world.son.id, world.son.name)
    hidden = await session.scalar(select(LexemeRow.register).where(LexemeRow.language_entity_id == language.id, LexemeRow.word == world.son.name))
    assert hidden is WordRegister.TABOO
    assert await session.scalar(select(MeaningShiftRow.id).where(MeaningShiftRow.shift == SenseShift.EUPHEMISM)) is not None


async def test_a_hostile_word_that_must_not_be_said_and_a_slip_of_honorifics_give_offence(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await tuned(session, tongues={"taboo_slip_pct": 100, "honorific_slip_pct": 100})
    town = await settlement(session, "Harrowmere", world, world.regions[0])
    language = await tongue(session, world)
    words(session, language, ("Nethra", "a name not to be said"), register=WordRegister.TABOO)
    session.add(LanguageGrammarRow(language_entity_id=language.id, honorific_levels=2, locked=[]))
    await bond(session, town.id, language.id, BondKind.SPEAKS)
    low = await mortal(session, "Ilsa", world, town.id)
    high = await mortal(session, "Corvan", world, town.id)
    low.power_level, high.power_level = 1, 5
    await session.flush()
    assert await slips(ctx, low, high, hostile=True, rng=ctx.rng("t"), place=town.id) is WordRegister.TABOO
    session.add(LexemeRow(language_entity_id=language.id, word="Placeholder", meaning="x", added_by_kind=ActorKind.ENGINE, epoch=1))
    for row in await session.scalars(select(LexemeRow).where(LexemeRow.register == WordRegister.TABOO)):
        row.register = WordRegister.COMMON
    await session.flush()
    assert await slips(ctx, low, high, hostile=False, rng=ctx.rng("u"), place=town.id) is WordRegister.HONORIFIC
    told = list(await session.scalars(select(IncidentRow.id).where(IncidentRow.kind == "social.taboo_word")))
    assert len(told) == 2
