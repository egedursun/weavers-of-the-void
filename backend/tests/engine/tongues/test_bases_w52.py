from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.tongues import BASES
from aerona.db.tables.crafts import NumberSystemRow
from aerona.db.tables.culture import LanguageStandingRow, SpeakerCohortRow
from aerona.db.tables.entities import LanguageProfileRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import WritingSystem
from aerona.domain.enums.culture import SpeakerKind
from aerona.domain.enums.tongues import NumeralBase
from aerona.engine.context import TickContext
from aerona.engine.crafts.reckoning import numeracy_of
from aerona.engine.primitives.language_profile import language_profile
from aerona.engine.tongues.counting import backfill_bases, base_contact, derived_base
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, bond
from tests.engine.tongues.helpers import tongue, tuned


def test_every_base_names_its_reckoning_rule() -> None:
    table = Rules().tongues
    assert all(hasattr(table, spec.rule) for spec in BASES.values())
    assert BASES[NumeralBase.SEXAGESIMAL].fine_division and BASES[NumeralBase.BODY_TALLY].needs_writing


async def test_a_people_counting_in_sixties_reckons_finer_than_one_counting_along_the_body(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    session.add(NumberSystemRow(people_entity_id=world.people.id, numeracy=50))
    await bond(session, world.people.id, world.language.id, BondKind.SPEAKS)
    profile = await language_profile(session, world.language)
    profile.numeral_base = NumeralBase.SEXAGESIMAL
    await session.flush()
    fine = await numeracy_of(session, ctx.rules, world.people.id)
    profile.numeral_base = NumeralBase.BODY_TALLY
    profile.writing_system = None
    await session.flush()
    tallied = await numeracy_of(session, ctx.rules, world.people.id)
    profile.writing_system = WritingSystem.ALPHABET
    await session.flush()
    written = await numeracy_of(session, ctx.rules, world.people.id)
    assert fine > written > tallied


async def test_a_tongue_takes_the_base_of_a_prestigious_neighbour(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await tuned(session, tongues={"base_contact_pct": 100})
    lender = await tongue(session, world, "Ulmar")
    (await session.get(LanguageProfileRow, lender.id)).numeral_base = NumeralBase.DUODECIMAL
    session.add(LanguageStandingRow(language_entity_id=lender.id, prestige=90, standardisation=0, locked=[]))
    session.add(LanguageStandingRow(language_entity_id=world.language.id, prestige=10, standardisation=0, locked=[]))
    await bond(session, world.people.id, world.language.id, BondKind.SPEAKS)
    session.add(
        SpeakerCohortRow(community_entity_id=world.people.id, language_entity_id=lender.id, kind=SpeakerKind.SECOND, share=40, since_epoch=1, locked=[])
    )
    own = await language_profile(session, world.language)
    await session.flush()
    assert await base_contact(ctx) >= 1
    assert own.numeral_base is NumeralBase.DUODECIMAL
    told = await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "language.base_changed").limit(1))
    assert told is not None


async def test_the_fixup_gives_a_daughter_its_parent_base_and_an_unwritten_unreckoning_tongue_the_body(
    ctx: TickContext, session: AsyncSession, world: CoreWorld
) -> None:
    parent = await tongue(session, world, "Elder")
    (await session.get(LanguageProfileRow, parent.id)).numeral_base = NumeralBase.VIGESIMAL
    daughter = await tongue(session, world, "Younger", parent_id=parent.id)
    assert (await session.get(LanguageProfileRow, daughter.id)).numeral_base is NumeralBase.VIGESIMAL
    lone = await tongue(session, world, "Lone")
    profile = await session.get(LanguageProfileRow, lone.id)
    assert await derived_base(session, lone, profile) is NumeralBase.BODY_TALLY
    assert await backfill_bases(ctx) >= 1
    assert await backfill_bases(ctx) == 0
