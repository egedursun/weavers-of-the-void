from sqlalchemy.ext.asyncio import AsyncSession

from aerona.rules.registry import Rules
from aerona.services.integrity.retuned_rules import RETUNED, move_retuned_rules
from tests.engine.core.factories import CoreWorld


def test_every_retuned_rule_lands_on_its_current_default() -> None:
    defaults = Rules()
    assert {key: float(getattr(getattr(defaults, key[0]), key[1])) for key in RETUNED} == {key: after for key, (_, after) in RETUNED.items()}


async def test_an_untouched_old_default_moves_and_a_chosen_value_stays(session: AsyncSession, world: CoreWorld) -> None:
    snapshot = {namespace: {} for namespace, _ in RETUNED}
    for namespace, name in RETUNED:
        snapshot[namespace][name] = RETUNED[(namespace, name)][0]
    snapshot["survey"]["conquest_level"] = 2.0
    world.cosmos.rules_snapshot = snapshot
    await session.flush()
    assert await move_retuned_rules(session) == len(RETUNED) - 1
    assert world.cosmos.rules_snapshot["demography"]["endemic_baseline"] == 30.0
    assert world.cosmos.rules_snapshot["survey"]["conquest_level"] == 2.0
    assert await move_retuned_rules(session) == 0
