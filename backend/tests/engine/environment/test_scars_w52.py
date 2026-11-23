from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.scars import SCARS
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.domain.enums.environment import CleansingMethod, ScarKind, SoilKind
from aerona.domain.enums.evolution import SuccessionStage
from aerona.engine.environment.profile import scar_passage, scar_penalty
from aerona.engine.environment.soil_life import hold_back, scar_by_use
from aerona.engine.phases.environment import decay_scars
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from aerona.tools.mortal.sea_waves import cleansing_depth
from tests.engine.core.factories import seed_core_world, surveyed

RULES = Rules()
K = ScarKind


def test_every_scar_has_a_row_and_deep_scars_cut_passage_and_harvest() -> None:
    assert set(SCARS) == set(ScarKind)
    assert scar_passage(RULES, {}) == 0 and scar_passage(RULES, {K.MINED_OUT.value: 100}) == SCARS[K.MINED_OUT].passage(RULES)
    assert scar_passage(RULES, {K.FLOODED.value: 100}) > scar_passage(RULES, {K.FLOODED.value: 20})
    assert scar_penalty(RULES, {K.POISONED.value: 100}) > scar_penalty(RULES, {K.DRAINED.value: 100})


def test_poison_and_spent_mines_never_fade_on_their_own_and_others_do() -> None:
    land = RegionEnvironmentRow(scars={K.POISONED.value: 40, K.MINED_OUT.value: 30, K.FLOODED.value: 5}, locked=[])
    healed = decay_scars(RULES, land)
    assert K.FLOODED in healed and land.scars == {K.POISONED.value: 40, K.MINED_OUT.value: 30}
    assert cleansing_depth(RULES, CleansingMethod.POWER) > cleansing_depth(RULES, CleansingMethod.WORKS) > cleansing_depth(RULES, CleansingMethod.RITE)


async def test_use_scars_the_land_and_a_deep_scar_holds_back_its_growth(session: AsyncSession) -> None:
    world = await seed_core_world(session)
    await surveyed(session, world)
    ctx = await manual_context(session, "test", RULES)
    land = await session.get(RegionEnvironmentRow, world.regions[0].id)
    assert land is not None
    land.scars, land.base_forest, land.cleared, land.grazed, land.soil = {}, 90, 80, 80, SoilKind.LOAM
    made = await scar_by_use(ctx, land)
    assert {K.DEFORESTED, K.OVERGRAZED} <= set(made)
    land.succession, land.scars = SuccessionStage.OLD_FOREST, {K.FLOODED.value: RULES.scars.reset_depth}
    assert await hold_back(ctx, land) is SCARS[K.FLOODED].resets_to and land.succession is SuccessionStage.YOUNG_FOREST
    land.scars = {K.FLOODED.value: RULES.scars.reset_depth - 1}
    land.succession = SuccessionStage.OLD_FOREST
    assert await hold_back(ctx, land) is None
    kinds = set(await session.scalars(select(IncidentRow.kind)))
    assert {"scar.made", "succession.reset"} <= kinds
