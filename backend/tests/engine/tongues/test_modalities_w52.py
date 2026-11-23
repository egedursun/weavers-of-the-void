from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.tongues import MODALITY_RANGE, MODALITY_SENSE, WRITABLE
from aerona.db.tables.entities import LanguageProfileRow
from aerona.domain.enums.body import BodyFunction
from aerona.domain.enums.nature import SenseKind
from aerona.domain.enums.tongues import LanguageModality
from aerona.engine.context import TickContext
from aerona.engine.lore.language import compute
from aerona.engine.tongues.modality import suited
from tests.engine.core.factories import CoreWorld
from tests.engine.tongues.helpers import tongue, words

M = LanguageModality
NO_VOICE = frozenset({BodyFunction.GRASP, BodyFunction.PRESENCE, BodyFunction.COGNITION})


def test_field_senses_choose_field_tongues_and_touch_serves_those_without_sight_or_hearing() -> None:
    assert suited(NO_VOICE, frozenset({SenseKind.ELECTRIC})) is M.ELECTRIC
    assert suited(NO_VOICE, frozenset({SenseKind.VIBRATION})) is M.VIBRATION
    assert suited(NO_VOICE, frozenset()) is M.TACTILE
    assert suited(frozenset({BodyFunction.COGNITION}), frozenset()) is M.TELEPATHIC


def test_the_three_new_modalities_carry_their_senses_ranges_and_writing() -> None:
    assert MODALITY_SENSE[M.VIBRATION] is SenseKind.VIBRATION and MODALITY_SENSE[M.ELECTRIC] is SenseKind.ELECTRIC
    assert MODALITY_RANGE[M.VIBRATION] == "vibration_range" and MODALITY_RANGE[M.ELECTRIC] == "electric_range"
    assert WRITABLE[M.TACTILE] and not WRITABLE[M.VIBRATION]


async def test_tongues_of_different_modalities_need_interpreters(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    first, second = await tongue(session, world, "Hand"), await tongue(session, world, "Hum", parent_id=None)
    for language in (first, second):
        words(session, language, ("keta", "stone"), ("mora", "water"))
    await session.flush()
    alike = await compute(session, ctx.rules, first.id, second.id)
    (await session.get(LanguageProfileRow, second.id)).modality = M.VIBRATION
    await session.flush()
    apart = await compute(session, ctx.rules, first.id, second.id)
    assert apart < alike
