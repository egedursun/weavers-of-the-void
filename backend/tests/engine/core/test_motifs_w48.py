from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.kinds.motifs import MOTIF_SOURCES
from aerona.db.tables.demography import PeopleCultureRow
from aerona.domain.enums.creator import CreatorNature
from aerona.domain.enums.demography import MotifSource
from aerona.domain.enums.entity import EntityType
from aerona.domain.models.entity_stats import ArtworkStats, CelestialStats
from aerona.engine.collective.heraldry import chosen_charges
from aerona.engine.demography.control import edit_people
from aerona.engine.demography.peoples import culture_for
from aerona.engine.divine.creator_bonds import nature_for
from aerona.engine.lore.art import subject_of
from aerona.engine.lore.motifs import canon_motifs, motifs_of
from aerona.engine.primitives.manual import manual_context
from tests.engine.core.factories import CoreWorld, entity
from tests.engine.core.test_foodways_w48 import people_with_town


async def test_a_people_draws_its_motifs_from_what_its_world_holds(session: AsyncSession, world: CoreWorld) -> None:
    for index in range(6):
        await entity(session, f"Light {index}", EntityType.CELESTIAL, CelestialStats(brightness=50), world_id=world.world.id)
    motifs = await canon_motifs(session, world.people)
    assert MotifSource.SKY in motifs
    assert len(motifs) <= 3


async def test_motifs_lean_the_charges_of_arms_and_the_picture_of_the_creator(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "arms")
    charges = chosen_charges(ctx.rng("motif.arms"), [], [MotifSource.SKY])
    assert not charges or charges[0] in MOTIF_SOURCES[MotifSource.SKY].charges
    assert nature_for({}, [MotifSource.MADE_THINGS], 50) is CreatorNature.MAKER
    assert nature_for({}, [MotifSource.ANCESTORS], 50) is CreatorNature.ABSENT_ONE


async def test_the_god_sets_what_a_people_draws_its_motifs_from(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "people_edit")
    _, culture = await edit_people(ctx, world.people.id, {"motif_sources": ["gods", "pattern"]}, release=[])
    assert motifs_of(culture) == [MotifSource.GODS, MotifSource.PATTERN]
    assert "motif_sources" in culture.locked


def test_every_motif_source_has_charges_to_draw() -> None:
    assert all(spec.charges for spec in MOTIF_SOURCES.values())


async def test_an_artwork_with_no_one_to_honour_takes_its_subject_from_its_people_s_motifs(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "art")
    people, town = await people_with_town(session, world, "Ardan")
    culture = await session.get(PeopleCultureRow, people.id)
    if culture is None:
        culture = await culture_for(session, ctx.rules, people, None)
        session.add(culture)
    culture.motif_sources = [MotifSource.SKY.value]
    light = await entity(session, "Evening light", EntityType.CELESTIAL, CelestialStats(brightness=50), world_id=world.world.id)
    work = await entity(session, "Hymn", EntityType.ARTWORK, ArtworkStats(renown=40), world_id=world.world.id, location_id=town.id)
    await session.flush()
    assert await subject_of(ctx, work.id) == light.id
