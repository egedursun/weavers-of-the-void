from sqlalchemy import event, update
from sqlalchemy.orm import ORMExecuteState

from aerona.db.read_memo import forget_all, read_tables, table_names
from aerona.db.tables.belonging import HeldIdentityRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.mind import CultureValueRow, MemoryRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.relations import RelationshipRow
from aerona.db.tables.renown import ReputationRow, RulerCurrencyRow
from aerona.db.tables.society import CommunityRelationRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.belonging import IdentityLayer
from aerona.domain.enums.bond import BondKind, BondRole, BondState
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.mind import MemoryKind, TraitKind, TraitSource, ValueAxis, ValueHolder
from aerona.domain.enums.renown import ReputationAxis
from aerona.engine.mind.book import add_trait, write_values
from aerona.engine.mind.memories import remember
from aerona.engine.mind.opinion import composed, opinion
from aerona.engine.mind.opinion_cache import FOLLOWED_ROWS, OPINION_CACHE
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, link, mortal, people, settlement, son

RULES = Rules()
EPOCH = 4


async def agrees(realm: Realm, nodes: list[int]) -> int:
    kept = 0
    for holder in nodes:
        for subject in nodes:
            if holder == subject:
                continue
            fresh = await composed(realm.session, RULES, EPOCH, holder, subject)
            assert await opinion(realm.session, RULES, EPOCH, holder, subject) == fresh, (holder, subject)
            assert await opinion(realm.session, RULES, EPOCH, holder, subject) == fresh, (holder, subject)
            kept += 1
    return kept


async def test_kept_opinions_always_equal_a_fresh_reading_whatever_changes(realm: Realm) -> None:
    hill, marsh = await people(realm, "Hill Folk"), await people(realm, "Marsh Folk")
    town = await settlement(realm, "Fordham")
    homeland = await link(realm.session, hill.id, town.id, BondKind.LIVES_IN)
    homeland.role = BondRole.HOMELAND
    first, second = await mortal(realm, "Arn", location_id=town.id), await mortal(realm, "Ysa", location_id=town.id)
    god = await son(realm.session, "Vael", realm.world.id)
    await realm.session.flush()
    nodes = [hill.id, marsh.id, town.id, first.id, second.id, god.id]
    pairs = await agrees(realm, nodes)
    assert pairs == len(nodes) * (len(nodes) - 1)

    memory = await remember(realm.session, RULES, holder_id=hill.id, subject_id=marsh.id, kind=MemoryKind.FOUGHT_US, magnitude=-30, epoch=3)
    assert memory is not None
    await agrees(realm, nodes)
    memory.magnitude = -60
    await agrees(realm, nodes)
    await remember(realm.session, RULES, holder_id=first.id, subject_id=god.id, kind=MemoryKind.HARMED_ME, magnitude=-20, epoch=3)
    await agrees(realm, nodes)

    enmity = await link(realm.session, hill.id, marsh.id, BondKind.ENEMY)
    await link(realm.session, second.id, marsh.id, BondKind.ENEMY)
    await link(realm.session, first.id, god.id, BondKind.WORSHIPS)
    await agrees(realm, nodes)
    enmity.state = BondState.PAST
    await agrees(realm, nodes)

    await write_values(realm.session, ValueHolder.CULTURE, hill.id, {ValueAxis.HONOUR: 90, ValueAxis.MERCY: -70})
    await agrees(realm, nodes)
    await write_values(realm.session, ValueHolder.PERSONAL, first.id, {ValueAxis.HONOUR: -80})
    await add_trait(realm.session, second.id, next(iter(TraitKind)), TraitSource.BIRTH, EPOCH)
    await agrees(realm, nodes)

    realm.session.add(RelationshipRow(holder_node_id=first.id, subject_node_id=second.id, friendship=60, rivalry=20, since_epoch=1, last_epoch=3))
    realm.session.add(CommunityRelationRow(entity_a_id=min(hill.id, marsh.id), entity_b_id=max(hill.id, marsh.id), value=-20, blood_feud_since_epoch=2))
    realm.session.add(ReputationRow(subject_node_id=marsh.id, community_node_id=hill.id, axis=ReputationAxis.HEROISM, value=70, heard_epoch=3))
    realm.session.add(RulerCurrencyRow(subject_node_id=second.id, dread=40, tyranny=30, updated_epoch=3))
    realm.session.add(HeldIdentityRow(holder_entity_id=first.id, layer=IdentityLayer.LOCALITY, value_node_id=town.id, strength=80, salience=60))
    realm.session.add(HeldIdentityRow(holder_entity_id=second.id, layer=IdentityLayer.LOCALITY, value_node_id=town.id, strength=70, salience=50))
    await agrees(realm, nodes)

    hill.creator_son_id = god.id
    first.location_id = None
    await agrees(realm, nodes)
    marsh.status, marsh.end_epoch = EntityStatus.DEAD, 3
    await agrees(realm, nodes)

    await realm.session.delete(memory)
    await agrees(realm, nodes)
    await realm.session.execute(update(MemoryRow).where(MemoryRow.holder_node_id == first.id).values(magnitude=-90))
    await agrees(realm, nodes)
    await realm.session.rollback()
    assert OPINION_CACHE not in realm.session.sync_session.info


async def test_a_fresh_reading_reads_only_tables_whose_changes_the_kept_opinions_follow(realm: Realm) -> None:
    hill, marsh = await people(realm, "Hill Folk"), await people(realm, "Marsh Folk")
    town = await settlement(realm, "Fordham")
    first = await mortal(realm, "Arn", location_id=town.id)
    god = await son(realm.session, "Vael", realm.world.id)
    await link(realm.session, first.id, god.id, BondKind.WORSHIPS)
    await remember(realm.session, RULES, holder_id=hill.id, subject_id=marsh.id, kind=MemoryKind.FOUGHT_US, magnitude=-30, epoch=3)
    await realm.session.flush()
    followed = table_names((*FOLLOWED_ROWS, NodeRow, EntityRow, SonRow, ForeignGodRow, CultureValueRow))
    seen: set[str] = set()

    def note(state: ORMExecuteState) -> None:
        if state.is_select:
            seen.update(read_tables(state))

    sync = realm.session.sync_session
    event.listen(sync, "do_orm_execute", note)
    try:
        for holder, subject in ((hill.id, marsh.id), (town.id, hill.id), (first.id, god.id), (god.id, first.id)):
            forget_all(sync)
            sync.expunge_all()
            await composed(realm.session, RULES, EPOCH, holder, subject)
    finally:
        event.remove(sync, "do_orm_execute", note)
    assert seen and seen <= followed, sorted(seen - followed)
