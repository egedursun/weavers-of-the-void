from aerona.agents.fate.threads import ThreadState, closable, quota
from aerona.db.tables.lore import ThreadRow
from aerona.rules.registry import Rules
from aerona.rules.registry.fate import FateRules


def state(thread_id: int, progress: int, stagnant: int) -> ThreadState:
    return ThreadState(thread=ThreadRow(id=thread_id, epoch=1, text="t", progress=progress), advancers=[], advance_count=progress, stagnant=stagnant)


def test_young_unadvanced_threads_cannot_close_and_the_most_advanced_come_first() -> None:
    rules = Rules(fate=FateRules(stale_thread_epochs=2, long_thread_steps=5, zero_progress_close_epochs=6, open_thread_cap=3))
    young = state(1, 0, 3)
    forgotten = state(2, 0, 7)
    long_story = state(3, 9, 0)
    stale = state(4, 2, 4)
    assert not closable(rules, young)
    assert closable(rules, forgotten)
    plan = quota(rules, [young, forgotten, long_story, stale])
    assert plan.candidates == [3, 4, 2]
    assert 1 not in plan.closable_ids
    assert plan.min_close <= len(plan.closable_ids)
