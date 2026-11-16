from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.technology import ERA_LEVEL, FAMILY_BRANCHES, FAMILY_TECHNIQUES
from aerona.db.tables.technology import TechnologyProfileRow
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.eras import TechFamily
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.world import TechnologyEra
from aerona.engine.technology.profiles import derived, family_level, keep_technology
from tests.engine.core.factories import CoreWorld
from tests.engine.core.test_minds_w44 import at


def test_every_family_reads_branches_and_techniques_and_every_era_has_a_level() -> None:
    assert all(FAMILY_BRANCHES[family] and FAMILY_TECHNIQUES[family] for family in TechFamily)
    assert ERA_LEVEL[TechnologyEra.BEYOND] > ERA_LEVEL[TechnologyEra.ADVANCED] > ERA_LEVEL[TechnologyEra.GUNPOWDER]


def test_a_people_can_be_far_along_in_one_family_and_early_in_another() -> None:
    levels = {KnowledgeBranch.MEDICINE: 8, KnowledgeBranch.WARFARE: 1}
    known = {Technique.VACCINES, Technique.ANTIBIOTICS}
    assert derived(levels, known, TechFamily.MEDICINE) > derived(levels, known, TechFamily.WARFARE)


async def test_worlds_take_their_starting_era_and_a_held_level_stays(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 2)
    await keep_technology(ctx)
    row = await session.get(TechnologyProfileRow, (world.world.id, TechFamily.SPACE))
    assert row is not None
    row.level, row.locked = 9, ["level"]
    await keep_technology(ctx)
    assert await family_level(session, world.world.id, TechFamily.SPACE) == 9
