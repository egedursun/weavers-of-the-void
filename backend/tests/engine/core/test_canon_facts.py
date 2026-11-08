import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.lore import CanonFactRow
from aerona.domain.enums.bond import BondKind
from aerona.engine.primitives.canon_facts import (
    FactDraft,
    Predicate,
    add_manual_fact,
    apply_fate_facts,
    facts_about,
    rebuild_certain_facts,
    retract_fact,
    seed_if_empty,
)
from tests.engine.core.factories import CoreWorld, bond, settlement, tuned_rules


async def facts_of(session: AsyncSession, subject: int) -> dict[str, tuple[int | None, str | None]]:
    rows = await session.scalars(select(CanonFactRow).where(CanonFactRow.subject_entity_id == subject, CanonFactRow.active.is_(True)))
    return {row.predicate: (row.object_entity_id, row.object_text) for row in rows}


async def test_certain_facts_follow_a_things_place_tongue_god_and_lineage(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Brookhold", world, world.regions[0])
    await bond(session, town.id, world.language.id, BondKind.SPEAKS)
    await bond(session, town.id, world.son.id, BondKind.WORSHIPS)
    await bond(session, town.id, world.people.id, BondKind.DESCENDS_FROM)
    assert await seed_if_empty(session) > 0
    facts = await facts_of(session, town.id)
    assert facts[Predicate.LOCATED_IN] == (world.regions[0].id, None)
    assert facts[Predicate.LANGUAGE] == (world.language.id, None)
    assert facts[Predicate.WORSHIPS] == (None, world.son.name)
    assert facts[Predicate.DESCENDS] == (world.people.id, None)
    assert await seed_if_empty(session) == 0


async def test_a_moved_thing_loses_its_old_place_and_gains_the_new_one(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Brookhold", world, world.regions[0])
    await rebuild_certain_facts(session)
    town.location_id = world.regions[1].id
    await session.flush()
    await rebuild_certain_facts(session)
    assert (await facts_of(session, town.id))[Predicate.LOCATED_IN] == (world.regions[1].id, None)
    old = await session.scalar(select(CanonFactRow).where(CanonFactRow.subject_entity_id == town.id, CanonFactRow.object_entity_id == world.regions[0].id))
    assert old is not None and not old.active


async def test_fate_facts_are_cleaned_capped_and_never_repeated(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Brookhold", world, world.regions[0])
    drafts = [
        FactDraft(town.id, "  honours  ", object_entity_id=world.people.id),
        FactDraft(town.id, "honours", object_entity_id=world.people.id),
        FactDraft(town.id, " ", object_text="nothing"),
        FactDraft(town.id, "keeps", object_entity_id=999999),
        FactDraft(999999, "keeps", object_text="ghost"),
        FactDraft(world.people.id, "remembers", object_text="  the flood  "),
    ]
    stored = await apply_fate_facts(session, tuned_rules(), drafts, 3, judged_ids=[world.people.id])
    assert [(row.subject_entity_id, row.predicate, row.object_entity_id, row.object_text) for row in stored] == [
        (town.id, "honours", world.people.id, None),
        (world.people.id, "remembers", None, "the flood"),
    ]
    assert stored[0].source_entity_id is None and stored[1].source_entity_id == world.people.id
    capped = await apply_fate_facts(session, tuned_rules(fate={"canon_facts_max": 0}), [FactDraft(town.id, "fears", object_text="the dark")], 3, [])
    assert capped == []


async def test_a_god_adds_and_retracts_facts_and_reads_them_about_a_thing(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Brookhold", world, world.regions[0])
    fact = await add_manual_fact(session, FactDraft(town.id, "trades with", object_entity_id=world.people.id), 4)
    assert fact.id in {row.id for row in await facts_about(session, world.people.id, 10)}
    assert (await retract_fact(session, fact.id)).active is False
    assert fact.id not in {row.id for row in await facts_about(session, town.id, 10)}
    with pytest.raises(NotFoundError):
        await add_manual_fact(session, FactDraft(999999, "is"), 4)
    with pytest.raises(ValidationFailedError):
        await add_manual_fact(session, FactDraft(town.id, " ", object_text="x"), 4)
    with pytest.raises(ValidationFailedError):
        await add_manual_fact(session, FactDraft(town.id, "is"), 4)
    with pytest.raises(NotFoundError):
        await add_manual_fact(session, FactDraft(town.id, "is", object_entity_id=999999), 4)
    with pytest.raises(NotFoundError):
        await retract_fact(session, 999999)
