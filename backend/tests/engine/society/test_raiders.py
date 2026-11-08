import pytest

from aerona.db.tables.mind import CultureValueRow
from aerona.domain.enums.mind import ActKind, ValueAxis
from aerona.engine.context import TickContext
from aerona.engine.military import causes
from tests.engine.society.factories import Realm, context, people, tuned


async def test_a_raid_is_judged_as_raiding_by_those_who_see_it(realm: Realm, monkeypatch: pytest.MonkeyPatch) -> None:
    raider = await people(realm, "Iron Folk", wealth=5, prosperity=5)
    victim = await people(realm, "Reed Folk", wealth=90, prosperity=90)
    realm.session.add(CultureValueRow(entity_id=raider.id, axis=ValueAxis.MARTIAL, value=90))
    await realm.session.flush()
    seen: list[tuple[int, int, ActKind]] = []
    real = causes.judged

    async def watched(ctx: TickContext, actor_id: int, victim_id: int, act: ActKind, *, note: str | None = None) -> int:
        seen.append((actor_id, victim_id, act))
        return await real(ctx, actor_id, victim_id, act, note=note)

    monkeypatch.setattr(causes, "judged", watched)
    ctx = context(realm.session, tuned(campaign_depth={"raid_war_chance": 100}))
    assert await causes.raiders(ctx) == 1
    assert seen == [(raider.id, victim.id, ActKind.RAIDING)]
