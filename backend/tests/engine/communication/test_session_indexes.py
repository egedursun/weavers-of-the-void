from sqlalchemy import event

from aerona.db.read_memo import KEEP_KEY
from aerona.db.tables.intrigue import BeliefRow
from aerona.db.tables.mind import ThoughtRow
from aerona.db.tables.relations import RelationshipRow
from aerona.domain.enums.intrigue import BeliefSource
from aerona.domain.enums.mind import Emotion, ThoughtKind
from aerona.engine.intrigue.beliefs import beliefs_of
from aerona.engine.mind.thoughts import same_thought
from aerona.engine.relations.book import relation, relations_about, relations_of
from aerona.prompts.contexts.base import RulesContext
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, mortal, settlement


def steps_session(realm: Realm) -> None:
    realm.session.sync_session.info[KEEP_KEY] = []


async def test_the_relation_index_follows_inserts_moves_and_deletes(realm: Realm) -> None:
    steps_session(realm)
    first, second, third = [await mortal(realm, name) for name in ("Ash", "Bay", "Cole")]
    assert await relation(realm.session, first.id, second.id) is None
    row = RelationshipRow(holder_node_id=first.id, subject_node_id=second.id, kinds=[], since_epoch=1, last_epoch=1, locked=[])
    realm.session.add(row)
    assert await relation(realm.session, first.id, second.id) is row
    assert await relations_of(realm.session, first.id) == [row] and await relations_about(realm.session, second.id) == [row]
    row.subject_node_id = third.id
    await realm.session.flush()
    assert await relation(realm.session, first.id, second.id) is None
    assert await relation(realm.session, first.id, third.id) is row
    await realm.session.delete(row)
    await realm.session.flush()
    assert await relation(realm.session, first.id, third.id) is None and await relations_of(realm.session, first.id) == []


async def test_the_thought_index_only_holds_the_epoch_it_was_built_for(realm: Realm) -> None:
    steps_session(realm)
    thinker = await mortal(realm, "Dell")
    old = ThoughtRow(holder_node_id=thinker.id, kind=next(iter(ThoughtKind)), emotion=next(iter(Emotion)), intensity=10, epoch=1, decay_pct=10)
    realm.session.add(old)
    await realm.session.flush()
    assert await same_thought(realm.session, thinker.id, old.kind, 2, None) is None
    fresh = ThoughtRow(holder_node_id=thinker.id, kind=old.kind, emotion=next(iter(Emotion)), intensity=10, epoch=2, decay_pct=10)
    realm.session.add(fresh)
    assert await same_thought(realm.session, thinker.id, old.kind, 2, None) is fresh
    assert await same_thought(realm.session, thinker.id, old.kind, 1, None) is old


async def test_the_belief_index_loads_once_and_follows_new_beliefs(realm: Realm) -> None:
    steps_session(realm)
    holder = await settlement(realm, "Eastmere")
    other = await settlement(realm, "Westmere")
    seen: list[str] = []
    event.listen(realm.session.sync_session.bind, "before_cursor_execute", lambda *args: seen.append(args[2]))
    assert await beliefs_of(realm.session, holder.id) == {}
    assert await beliefs_of(realm.session, other.id) == {}
    reads = [statement for statement in seen if statement.startswith("SELECT") and "FROM beliefs" in statement]
    assert len(reads) == 1
    row = BeliefRow(holder_node_id=holder.id, subject_node_id=other.id, attribute="wealth", value=10, confidence=50, source=BeliefSource.SPY, as_of_epoch=1)
    realm.session.add(row)
    await realm.session.flush()
    assert (await beliefs_of(realm.session, holder.id))[(other.id, "wealth")] is row


async def test_rows_of_one_table_with_different_changes_update_in_one_batch(realm: Realm) -> None:
    steps_session(realm)
    holder = await settlement(realm, "Northmere")
    subjects = [await settlement(realm, f"Vale {index}") for index in range(4)]
    rows = [
        BeliefRow(holder_node_id=holder.id, subject_node_id=subject.id, attribute="wealth", value=10, confidence=50, source=BeliefSource.SPY, as_of_epoch=1)
        for subject in subjects
    ]
    realm.session.add_all(rows)
    await realm.session.flush()
    for index, row in enumerate(rows):
        row.confidence = 40
        if index % 2:
            row.value = 20
    seen: list[str] = []
    event.listen(realm.session.sync_session.bind, "before_cursor_execute", lambda *args: seen.append(args[2]))
    await realm.session.flush()
    assert len([statement for statement in seen if statement.startswith("UPDATE beliefs")]) == 1
    assert [row.value for row in rows] == [10, 20, 10, 20]


def test_a_prompt_context_holds_rules_without_building_their_schema() -> None:
    rules = Rules()
    assert RulesContext(rules=rules).rules is rules
    assert RulesContext(rules=rules).model_dump() == {"rules": None}
