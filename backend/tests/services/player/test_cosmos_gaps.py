import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.tables.celestial import WorldMapRow
from aerona.db.tables.entities import EntityRow, LanguageProfileRow
from aerona.domain.enums.chronicle import WritingSystem
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.world import StarType
from aerona.domain.models.entity_stats import LanguageStats
from aerona.domain.models.phonology import LanguageSignature
from aerona.engine.cosmos.maps import map_is_stale, regenerate_world_map
from aerona.services.player import canon, cosmic, languages, pantheon, world_edits
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld, make_entity, make_son


async def test_map_goes_stale_when_a_settlement_appears_and_an_edit_changes_terrain(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    await regenerate_world_map(session, scope.rules, world.world.id, 1)
    assert not await map_is_stale(session, world.world.id)
    await make_entity(session, "Ashford", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    assert await map_is_stale(session, world.world.id)
    await regenerate_world_map(session, scope.rules, world.world.id, 1)
    assert not await map_is_stale(session, world.world.id)
    await world_edits.edit_world(scope, world_edits.EditWorld(world_id=world.world.id, terrain_seed="fresh", sea_pct=70))
    assert world.world.terrain_seed == "fresh" and world.world.terrain_sea == 0.7
    assert await map_is_stale(session, world.world.id)
    stored = await session.get(WorldMapRow, world.world.id)
    assert stored is not None and stored.signature


async def test_a_region_can_be_made_water_by_edit(scope: PlayerScope, world: PlayerWorld) -> None:
    await canon.edit_record(scope, canon.EditRecord(entity_id=world.region.id, is_water=True))
    assert world.region.is_water
    with pytest.raises(ValidationFailedError):
        town = await make_entity(scope.session, "Ashford", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
        await canon.edit_record(scope, canon.EditRecord(entity_id=town.id, is_water=True))


async def test_language_script_signature_and_samples_are_editable(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    language = await make_entity(session, "Tarnic", EntityType.LANGUAGE, world_id=world.world.id, stats=LanguageStats(spread=10))
    signature = LanguageSignature(consonants="klmnr", cluster="rn", ending="ar", length_bias=1)
    await languages.edit_language(
        scope,
        languages.EditLanguage(
            language_id=language.id, writing_system=WritingSystem.ALPHABET, signature=signature, sample_names=["Kelar", "Mirnar"], alphabet="aeklmnr"
        ),
    )
    profile = await session.get(LanguageProfileRow, language.id)
    assert profile is not None and profile.writing_system is WritingSystem.ALPHABET
    assert profile.signature == signature and profile.phonology.sample_names == ("Kelar", "Mirnar") and profile.alphabet == "aeklmnr"
    await languages.edit_language(scope, languages.EditLanguage(language_id=language.id, clear_writing_system=True, clear_signature=True))
    assert profile.writing_system is None and profile.signature is None
    with pytest.raises(ValidationFailedError):
        await languages.edit_language(scope, languages.EditLanguage(language_id=language.id))


async def test_epoch_words_action_runs(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    outcome = await languages.run_epoch_words(scope, languages.EpochWords())
    assert outcome.values["words"] == 0


async def test_extinguish_star_and_outer_bargain_controls(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    star = await cosmic.hang_star(scope, cosmic.HangStar(name="Vael", star_type=StarType.YELLOW_DWARF))
    star_id = star.created_ids[0] if star.created_ids else star.target_node_id
    assert star_id is not None
    before = world.creator.essence
    outcome = await cosmic.extinguish(scope, cosmic.StarTarget(star_id=star_id))
    assert world.creator.essence == before - scope.rules.cosmic_costs.extinguish_star and outcome.essence_spent == scope.rules.cosmic_costs.extinguish_star
    with pytest.raises(ValidationFailedError):
        await cosmic.extinguish(scope, cosmic.StarTarget(star_id=star_id))
    son = await make_son(session, "Velkar", world.world.id)
    await pantheon.outer_bargain(scope, pantheon.OuterBargainOrder(son_id=son.id, mode=pantheon.OuterBargainMode.FORBID))
    assert son.outer_bargain_forbidden and son.status is not SonStatus.DEAD
    await pantheon.outer_bargain(scope, pantheon.OuterBargainOrder(son_id=son.id, mode=pantheon.OuterBargainMode.ALLOW))
    assert not son.outer_bargain_forbidden
    with pytest.raises(ValidationFailedError):
        await pantheon.outer_bargain(scope, pantheon.OuterBargainOrder(son_id=son.id, mode=pantheon.OuterBargainMode.FORCE))
    assert (await session.scalars(select(EntityRow.id).limit(1))).first() is not None
