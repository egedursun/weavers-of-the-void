from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.entities import EntityRepository
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.engine.primitives.subtypes import normalize_subtype
from aerona.services import narrative
from tests.services.app.factories import Cosmos, make_entity


def test_scrub_ids_keeps_names_and_replaces_handles() -> None:
    text = "son#3 Haevaron met thread#67 and [thread#12] the Ash (#795) under world#2 near #44."
    assert narrative.scrub_ids(text) == "Haevaron met a story and the Ash under near."


def test_scrub_ids_capitalizes_at_sentence_start() -> None:
    assert narrative.scrub_ids("son#4 wept. thread#9 began.") == "A son wept. A story began."


def test_collapse_type_repetition() -> None:
    assert narrative.clean_chronicle_text("The Sand Language language spread.") == "The Sand Language spread."


def test_prompt_safe_strips_numbers() -> None:
    text = "Ithren's essence fell to 20 and faith rose to 90 after a duel (122\u201394); he gained 15 essence, from 90 to 20."
    assert narrative.prompt_safe(text) == "Ithren's essence fell and faith rose after a duel; he gained essence."


def test_clean_narrative_removes_editorial_marks() -> None:
    text = "<!-- hidden -->A tower classified as P7 (P7) stood \u2605 3 tall (130\u2013102).\nNote: this record was moved."
    assert narrative.clean_narrative(text) == "A tower stood tall."


def test_clean_fate_note_drops_internal_clauses() -> None:
    note = "The river is old; this was a tired motif. However, it carries salt. A cliche warning applies."
    assert narrative.clean_fate_note(note) == "The river is old. However, it carries salt."
    assert narrative.clean_fate_note("Pre-screen warning only.") is None


def test_meta_sentences_are_removed() -> None:
    text = "The keep stands. Fate rewrote the record's account here. The first account said otherwise."
    assert narrative.remove_meta_sentences(text) == "The keep stands."


def test_subtype_normalization_snaps_to_existing_spelling() -> None:
    assert normalize_subtype("magic_storm") == "magic storm"
    assert normalize_subtype("currency: salt coin") == "currency: salt coin"
    assert normalize_subtype("river spirit", ["River Spirit", "River Spirit", "river spirit"]) == "River Spirit"


def test_ruler_titles_and_community_phrases() -> None:
    assert narrative.ruler_title(EntityType.LAW) == "Keeper"
    assert narrative.ruler_title(EntityType.SETTLEMENT) == "Lord"


def test_mortals_are_not_called_sons() -> None:
    assert narrative.mortal_description("Ora is a quiet son who hunts. He was a son of the river.") == (
        "Ora is a quiet mortal who hunts. He was a son of the river."
    )


async def test_backfill_endings_and_sweep(session: AsyncSession, world: Cosmos) -> None:
    hero = await make_entity(session, "Ora", EntityType.MORTAL, world_id=world.world.id, location_id=world.region.id)
    await EntityRepository(session).set_status(hero, EntityStatus.DEAD, 3, fate_note="Ora fell at the ford in Epoch 3.")
    ruin = await make_entity(session, "Old Keep", EntityType.PLACE, world_id=world.world.id, location_id=world.region.id)
    await EntityRepository(session).set_status(ruin, EntityStatus.DESTROYED, 4)
    assert await narrative.backfill_endings(session) == 2
    assert hero.description.endswith("Ora fell at the ford in Epoch 3.")
    assert ruin.description.endswith("Vanished in Epoch 4.")
    assert await narrative.backfill_endings(session) == 0
    world.people.description = "The folk (#12) of son#3 Ithren."
    assert await narrative.sweep_narratives(session) == 1
    assert world.people.description == "The folk of Ithren."
