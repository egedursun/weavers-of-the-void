import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.lore import CanonFactRow, FolkBeliefRow, ThreadRow
from aerona.db.tables.meta import MapNoteRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ThreadStatus
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.services.player import canon
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld, action_kinds, bond, make_entity, make_son


async def test_strike_and_restore_canon(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    city = await make_entity(session, "Ashford", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    friend = await make_entity(session, "Bralk", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    await bond(session, city.id, friend.id, BondKind.ALLY)
    struck = await canon.set_canon(scope, canon.SetCanon(entity_id=city.id, status=canon.CanonVerdict.REJECTED))
    assert city.status is EntityStatus.REJECTED
    assert struck.values["bonds_hidden"] >= 1
    with pytest.raises(ValidationFailedError):
        await canon.set_canon(scope, canon.SetCanon(entity_id=city.id, status=canon.CanonVerdict.REJECTED))
    await canon.set_canon(scope, canon.SetCanon(entity_id=city.id, status=canon.CanonVerdict.CANON))
    assert city.status is EntityStatus.CANON
    assert await BondRepository(session).exists_between(city.id, friend.id, BondKind.ALLY)
    assert await action_kinds(session) == [ActionKind.CANON_STRIKE, ActionKind.CANON_RESTORE]


async def test_edit_record_keeps_description(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    city = await make_entity(session, "Ashford", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    await canon.edit_record(scope, canon.EditRecord(entity_id=city.id, name="Ashport", subtype="harbour"))
    assert city.name == "Ashport" and city.subtype == "harbour"
    with pytest.raises(ValidationFailedError):
        await canon.edit_record(scope, canon.EditRecord(entity_id=city.id, description="  "))


async def test_threads_facts_beliefs(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    city = await make_entity(session, "Ashford", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    opened = await canon.open_thread(scope, canon.OpenThread(text="The salt war looms.", related_ids=(city.id, 99999)))
    thread_id = opened.values["thread_id"]
    assert isinstance(thread_id, int)
    await canon.close_thread(scope, canon.CloseThread(thread_id=thread_id))
    thread = await session.get(ThreadRow, thread_id)
    assert thread is not None and thread.status is ThreadStatus.CLOSED
    with pytest.raises(NotFoundError):
        await canon.close_thread(scope, canon.CloseThread(thread_id=thread_id))
    added = await canon.add_fact(scope, canon.AddFact(subject_id=city.id, relation="trades in", object_text="salt"))
    fact_id = added.values["fact_id"]
    assert isinstance(fact_id, int)
    await canon.remove_fact(scope, canon.FactTarget(fact_id=fact_id))
    fact = await session.get(CanonFactRow, fact_id)
    assert fact is not None and not fact.active
    with pytest.raises(ValidationFailedError):
        await canon.add_fact(scope, canon.AddFact(subject_id=city.id, relation="trades in"))
    son = await make_son(session, "Velkar", world.world.id)
    await canon.edit_belief(scope, canon.EditBelief(people_id=city.id, son_id=son.id, narrative="He drowns the proud."))
    belief = await session.get(FolkBeliefRow, (city.id, son.id))
    assert belief is not None and belief.local_name != "Velkar"
    await canon.edit_belief(scope, canon.EditBelief(people_id=city.id, son_id=son.id, name="The Drowner", narrative="He drowns the proud."))
    assert belief.local_name == "The Drowner"


async def test_bonds_add_and_break(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    first = await make_entity(session, "Ashford", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    second = await make_entity(session, "Bralk", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    outcome = await canon.add_bond(scope, canon.AddBond(source_id=first.id, target_id=second.id, kind=BondKind.TRADES_WITH))
    with pytest.raises(ValidationFailedError):
        await canon.add_bond(scope, canon.AddBond(source_id=first.id, target_id=second.id, kind=BondKind.TRADES_WITH))
    with pytest.raises(ValidationFailedError):
        await canon.add_bond(scope, canon.AddBond(source_id=first.id, target_id=second.id, kind=BondKind.INSIDE))
    await canon.remove_bond(scope, canon.BondTarget(bond_id=outcome.created_ids[0]))
    row = await session.get(BondRow, outcome.created_ids[0])
    assert row is not None and row.state is not BondState.ACTIVE
    inside = await session.scalar(select(BondRow).where(BondRow.kind == BondKind.INSIDE, BondRow.source_node_id == first.id))
    assert inside is not None
    with pytest.raises(ValidationFailedError):
        await canon.remove_bond(scope, canon.BondTarget(bond_id=inside.id))


async def test_map_notes_favourite_and_note(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    added = await canon.add_map_note(scope, canon.AddMapNote(world_id=world.world.id, x=0.4, y=0.6, text="Here be salt", color="#aa8800"))
    note_id = added.values["note_id"]
    assert isinstance(note_id, int)
    await canon.remove_map_note(scope, canon.MapNoteTarget(note_id=note_id))
    assert await session.get(MapNoteRow, note_id) is None
    with pytest.raises(NotFoundError):
        await canon.remove_map_note(scope, canon.MapNoteTarget(note_id=note_id))
    await canon.set_favorite(scope, canon.Favorite(entity_id=world.region.id))
    assert world.region.favorite
    with pytest.raises(ValidationFailedError):
        await canon.set_private_note(scope, canon.PrivateNote(entity_id=world.region.id, text="x" * 5000))


async def test_merge_requires_confirmation_and_repoints(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    main = await make_entity(session, "Ashford", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    other = await make_entity(session, "Ashfort", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    friend = await make_entity(session, "Bralk", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    hero = await make_entity(session, "Asha", EntityType.MORTAL, world_id=world.world.id, location_id=other.id)
    await bond(session, other.id, friend.id, BondKind.TRADES_WITH)
    await EntityRepository(session).add_flag(other.id, EntityFlag.WONDER, 1)
    with pytest.raises(ValidationFailedError):
        await canon.merge_records(scope, canon.MergeRecords(entity_id=main.id, other_id=other.id, confirm="merge"))
    with pytest.raises(ValidationFailedError):
        await canon.merge_records(scope, canon.MergeRecords(entity_id=main.id, other_id=world.region.id, confirm="MERGE"))
    await canon.merge_records(scope, canon.MergeRecords(entity_id=main.id, other_id=other.id, confirm="MERGE"))
    assert other.status is EntityStatus.DESTROYED
    assert hero.location_id == main.id
    assert await BondRepository(session).exists_between(main.id, friend.id, BondKind.TRADES_WITH)
    assert await EntityRepository(session).has_flag(main.id, EntityFlag.WONDER)
    assert "Also known as Ashfort" in main.description
