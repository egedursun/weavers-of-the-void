from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.marks import AUGMENT_MEANINGS, MARKABLE, MARKS, MEANINGS
from aerona.db.tables.customs import BodyMarkRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.justice import CrimeCaseRow
from aerona.db.tables.made import AugmentRow
from aerona.domain.enums.customs import MarkKind, MarkMeaning
from aerona.domain.enums.justice import CaseStage, Verdict
from aerona.domain.enums.made import AugmentKind
from aerona.domain.enums.mortal import CrimeKind
from aerona.domain.enums.society import SocialClass
from aerona.engine.context import TickContext
from aerona.engine.customs.marks import MarkTally, implant_meaning, place, unshown_augment
from tests.engine.core.factories import CoreWorld, mortal


def test_ten_marks_and_eleven_meanings() -> None:
    assert len(MARKS) == len(MarkKind) == 12 and len(MEANINGS) == len(MarkMeaning) == 13
    assert MARKS[MarkKind.IMPLANT].shows_augment and MarkKind.IMPLANT not in MARKABLE
    assert MARKS[MarkKind.HAIR].quick
    assert MEANINGS[MarkMeaning.FAITH].reading == "loyalty_god" and MEANINGS[MarkMeaning.PROFESSION].guild


def test_every_augment_kind_reads_as_a_meaning() -> None:
    assert set(AUGMENT_MEANINGS) == set(AugmentKind)
    assert AUGMENT_MEANINGS[AugmentKind.COSMETIC] is MarkMeaning.BEAUTY and AUGMENT_MEANINGS[AugmentKind.INTERFACE] is MarkMeaning.PROFESSION


async def test_an_implant_shows_faith_crime_or_the_augment_it_is(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    bearer = await mortal(session, "Iria", world, world.regions[0].id)
    priest = await mortal(session, "Ilse Varrow", world, world.regions[0].id)
    priest.social_class = SocialClass.PRIEST
    plain = AugmentRow(bearer_node_id=bearer.id, kind=AugmentKind.COSMETIC, installed_epoch=ctx.epoch, locked=[])
    blessed = AugmentRow(bearer_node_id=bearer.id, kind=AugmentKind.COSMETIC, installed_by_node_id=priest.id, installed_epoch=ctx.epoch, locked=[])
    session.add_all([plain, blessed])
    await session.flush()
    assert await implant_meaning(ctx, bearer, plain) is MarkMeaning.BEAUTY
    assert await implant_meaning(ctx, bearer, blessed) is MarkMeaning.FAITH
    session.add(
        CrimeCaseRow(
            crime=CrimeKind.THEFT,
            accused_entity_id=bearer.id,
            stage=CaseStage.CLOSED,
            verdict=Verdict.GUILTY,
            opened_epoch=ctx.epoch,
            closed_epoch=ctx.epoch,
            locked=[],
        )
    )
    await session.flush()
    assert await implant_meaning(ctx, bearer, plain) is MarkMeaning.CRIME


async def test_an_implant_mark_names_the_one_augment_not_yet_shown(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    bearer = await mortal(session, "Iria", world, world.regions[0].id)
    assert await unshown_augment(ctx, bearer.id) is None
    first = AugmentRow(bearer_node_id=bearer.id, kind=AugmentKind.SENSE, installed_epoch=ctx.epoch, locked=[])
    second = AugmentRow(bearer_node_id=bearer.id, kind=AugmentKind.WEAPON, installed_epoch=ctx.epoch, locked=[])
    session.add_all([first, second])
    await session.flush()
    assert await unshown_augment(ctx, bearer.id) is first
    await place(ctx, bearer, MarkKind.IMPLANT, MarkMeaning.PROFESSION, MarkTally(), augment_id=first.id, told=False)
    await session.flush()
    assert await unshown_augment(ctx, bearer.id) is second
    marks = list(await session.scalars(select(BodyMarkRow).where(BodyMarkRow.holder_node_id == bearer.id)))
    assert [(row.kind, row.augment_id) for row in marks] == [(MarkKind.IMPLANT, first.id)]
    assert "body.marked" not in set(await session.scalars(select(IncidentRow.kind)))
