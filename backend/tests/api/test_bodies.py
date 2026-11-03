from aerona.domain.enums.body import HarmCause, InjuryKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.models.entity_stats import MortalStats
from aerona.engine.body.hits import Harm
from aerona.engine.lifecycle.wounds import WoundOutcome, apply_hits
from tests.api.conftest import ApiWorld, seeded
from tests.engine.core.factories import entity
from tests.engine.society.factories import context


async def test_a_fallen_body_shows_the_wound_that_killed_it(api: ApiWorld) -> None:
    core = seeded(api).core
    async with api.services.database.write() as session:
        victim = await entity(session, "Bera", EntityType.MORTAL, MortalStats(hp=100), world_id=core.world.id, location_id=core.regions[0].id)
        ctx = context(session)
        await apply_hits(ctx, victim, Harm(5, HarmCause.BATTLE, "cut on the arm", part="left_arm", kind=InjuryKind.CUT, severity=2))
        wounding = await apply_hits(ctx, victim, Harm(10, HarmCause.BATTLE, "fell in battle", part="heart", kind=InjuryKind.DESTROYED, severity=5))
        assert wounding.outcome is WoundOutcome.DIED
        victim_id = victim.id
    body = (await api.http.get(f"/api/bodies/{victim_id}")).json()
    parts = {part["key"]: part for part in body["parts"]}
    assert body["alive"] is False
    assert parts["heart"]["state"] == "lethal"
    assert parts["left_arm"]["state"] == "fresh"
    assert parts["right_arm"]["state"] is None
