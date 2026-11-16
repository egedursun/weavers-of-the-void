from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.quests import AIM_DEFAULTS, LEGACY_HERO, LEGACY_LEGENDARY
from aerona.catalog.strata import STRATUM_AXES
from aerona.db.tables.cosmography import DimensionRow
from aerona.db.tables.dimension_aspects import DimensionAspectRow
from aerona.db.tables.faith import AfterlifeStratumRow, SpiritProfileRow
from aerona.db.tables.horror import HorrorEventRow
from aerona.db.tables.lore import LexemeRow
from aerona.db.tables.storyteller import StorytellerRow
from aerona.domain.enums.arcana import SpellForm
from aerona.domain.enums.cosmography import DimensionElement, DimensionKind
from aerona.domain.enums.ecology import TissueMaterial
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faith import AfterlifeState, StratumKind, StratumPermanence
from aerona.domain.enums.horror import HorrorEffect, HorrorTarget
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.quests import QuestAim, QuestTargetKind
from aerona.domain.enums.storyteller import PaletteDirection, PaletteSubsystem, TensionBand
from aerona.domain.models.entity_stats import SpiritStats
from aerona.engine.cosmos.aspects import aspect_row, keep_aspects
from aerona.engine.cosmos.horror_model import EFFECT_DIRECTION, HORROR_PRESETS, HorrorSpec, horror_event
from aerona.engine.cosmos.ladder import DimensionDraft, create_dimension
from aerona.engine.faith.judgement import new_stratum
from aerona.engine.faith.strata_life import stratum_turn
from aerona.engine.phases.society_support.quest_claims import CLAIMS
from aerona.engine.storyteller.pace import storyteller_of
from aerona.engine.storyteller.palette import BY_KEY, PALETTE, keep_palette
from tests.engine.core.factories import CoreWorld, entity
from tests.engine.core.test_minds_w44 import at

EVERY_LEGACY_HORROR = 7


def test_every_old_list_is_a_preset_or_a_mapping_of_the_typed_models() -> None:
    assert len(HORROR_PRESETS) == EVERY_LEGACY_HORROR
    assert set(EFFECT_DIRECTION) == set(HorrorEffect)
    assert LEGACY_HERO["thread"] == (QuestAim.RESOLVE, QuestTargetKind.INCIDENT_ARC)
    assert LEGACY_LEGENDARY["dead_star"] == (QuestAim.RESTORE, QuestTargetKind.STAR)
    assert set(CLAIMS) == set(QuestAim) == set(AIM_DEFAULTS)
    assert set(STRATUM_AXES) == set(StratumKind)
    assert {item.subsystem for item in PALETTE} == set(PaletteSubsystem)
    assert {item.direction for item in PALETTE} == set(PaletteDirection)
    assert "soft_tissue" in {item.value for item in TissueMaterial}


async def test_a_horror_takes_words_by_target_and_effect_and_lingers(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 3)
    for index in range(10):
        session.add(LexemeRow(language_entity_id=world.language.id, word=f"word{index}", meaning="thing", added_by_kind=ActorKind.ENGINE, epoch=1))
    await session.flush()
    before = int(await session.scalar(select(func.count()).select_from(LexemeRow).where(LexemeRow.language_entity_id == world.language.id)) or 0)
    text = await horror_event(ctx, HorrorSpec(HorrorTarget.LANGUAGE, HorrorEffect.TAKE), world.world)
    after = int(await session.scalar(select(func.count()).select_from(LexemeRow).where(LexemeRow.language_entity_id == world.language.id)) or 0)
    assert after < before and world.world.name in text
    row = await session.scalar(select(HorrorEventRow).order_by(HorrorEventRow.id.desc()).limit(1))
    assert row is not None and row.target is HorrorTarget.LANGUAGE and row.until_epoch == 3 + ctx.rules.cosmic_horror.horror_duration


async def test_a_soul_fades_from_a_realm_where_souls_fade(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 3)
    stratum = new_stratum(ctx.rules, world.regions[0], StratumKind.DISSOLUTION)
    session.add(stratum)
    await session.flush()
    assert stratum.permanence is StratumPermanence.FADING
    spirit = await entity(session, "Shade", EntityType.SPIRIT, SpiritStats(), world_id=world.world.id, location_id=world.regions[0].id)
    profile = SpiritProfileRow(spirit_entity_id=spirit.id, state=AfterlifeState.IN_REALM, stratum_id=stratum.id, memory_strength=1, locked=[])
    session.add(profile)
    await session.flush()
    assert await stratum_turn(ctx, profile, spirit) == "faded"
    assert profile.state is AfterlifeState.CONSUMED
    assert (await session.get(AfterlifeStratumRow, stratum.id)) is not None


async def test_aspects_pull_their_dimension_each_epoch(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 3)
    dimension = await create_dimension(session, ctx.rules, DimensionDraft("Hollow Reach", DimensionKind.POCKET, 3, element=DimensionElement.VOID))
    await session.flush()
    rows = list(await session.scalars(select(DimensionAspectRow).where(DimensionAspectRow.dimension_id == dimension.id)))
    assert {row.form for row in rows if row.form} == {SpellForm.SPACE} and {row.element for row in rows if row.element} == {DimensionElement.VOID}
    session.add(aspect_row(dimension.id, strength=100, form=SpellForm.TIME))
    await session.flush()
    leak, time = dimension.leak, dimension.time_factor
    assert await keep_aspects(ctx, dimension) == len(rows) + 1
    fresh = await session.get(DimensionRow, dimension.id)
    assert fresh is not None and fresh.leak > leak and fresh.time_factor > time


async def test_the_storyteller_weighs_only_events_whose_causes_hold(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 3)
    row = await storyteller_of(ctx, world.world.id)
    row.band = TensionBand.QUIET
    weights = await keep_palette(ctx, row)
    assert "beast_awakening" in weights and "art_flowering" not in weights
    assert all(weight >= 100 for weight in weights.values())
    assert all(BY_KEY[key].direction in set(PaletteDirection) for key in weights)
    row.locked = ["palette"]
    row.palette = {"raid": 5}
    assert await keep_palette(ctx, row) == {"raid": 5}
    assert isinstance(await session.get(StorytellerRow, world.world.id), StorytellerRow)
