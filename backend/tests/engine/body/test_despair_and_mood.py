from sqlalchemy import select

from aerona.db.tables.body import ConditionRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.mind import TraitRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.domain.enums.body import ConditionKind
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.mind import TraitKind, TraitSource
from aerona.domain.enums.mortal import DeathCause, StressBreak
from aerona.engine.mind.thoughts import mood_factor, mood_of
from aerona.engine.mortal.acts import BREAKS, despair, stress_break
from aerona.engine.mortal.profile import ensure_profile
from tests.engine.society.factories import Realm, context, mortal, tuned


async def melancholy(realm: Realm, bearer_id: int) -> ConditionRow | None:
    return await realm.session.scalar(select(ConditionRow).where(ConditionRow.bearer_node_id == bearer_id, ConditionRow.kind == ConditionKind.MELANCHOLY))


async def test_despair_brings_melancholy_and_never_death_where_the_world_forbids_it(realm: Realm) -> None:
    sufferer = await mortal(realm, "Oda")
    ctx = context(realm.session, tuned(stress={"despair_suicide": 0, "despair_suicide_chance": 100}))
    assert not await despair(ctx, sufferer, ctx.rng("test.despair"))
    assert await melancholy(realm, sufferer.id) is not None and sufferer.status is EntityStatus.CANON


async def test_despair_can_end_a_life_where_the_world_allows_it(realm: Realm) -> None:
    sufferer = await mortal(realm, "Ivar")
    ctx = context(realm.session, tuned(stress={"despair_suicide": 1, "despair_suicide_chance": 100}))
    assert await despair(ctx, sufferer, ctx.rng("test.despair"))
    profile = await realm.session.get(MortalProfileRow, sufferer.id)
    assert sufferer.status is not EntityStatus.CANON and profile is not None and profile.cause_of_death is DeathCause.DESPAIR


async def test_a_despairing_break_is_told_and_eases_the_strain(realm: Realm) -> None:
    ctx = context(realm.session, tuned(stress={"despair_suicide": 0}))
    seen = None
    for index in range(30):
        sufferer = await mortal(realm, f"Mourner {index}")
        for trait in (TraitKind.MELANCHOLIC, TraitKind.RECLUSIVE):
            realm.session.add(TraitRow(node_id=sufferer.id, trait=trait, source=TraitSource.BIRTH, epoch=1))
        profile, _ = await ensure_profile(realm.session, sufferer.id, ctx.epoch)
        profile.stress = 100
        await realm.session.flush()
        if await stress_break(ctx, sufferer, profile) is StressBreak.DESPAIR:
            seen = (sufferer, profile)
            break
    assert seen is not None
    sufferer, profile = seen
    assert profile.last_break is StressBreak.DESPAIR and profile.stress < 100
    assert await melancholy(realm, sufferer.id) is not None
    assert await realm.session.scalar(select(ChronicleRow).where(ChronicleRow.template_key == "stress.despair")) is not None


async def test_the_sorrow_break_is_told_as_despair_with_its_melancholy(realm: Realm) -> None:
    sufferer = await mortal(realm, "Lysa")
    ctx = context(realm.session)
    profile, _ = await ensure_profile(realm.session, sufferer.id, ctx.epoch)
    broke = await BREAKS[StressBreak.DESPAIR](ctx, sufferer, profile, ctx.rng("test.despair"))
    assert broke.key == "stress.despair" and broke.facts["condition"] is ConditionKind.MELANCHOLY


async def test_mood_is_read_from_the_profile_and_scales_labour_without_going_negative(realm: Realm) -> None:
    worker = await mortal(realm, "Hale")
    ctx = context(realm.session)
    assert await mood_of(realm.session, None) == 0
    assert await mood_of(realm.session, worker.id) == 0
    profile, _ = await ensure_profile(realm.session, worker.id, ctx.epoch)
    profile.mood_score = -40
    await realm.session.flush()
    assert await mood_of(realm.session, worker.id) == -40
    assert mood_factor(0, 50) == 1.0
    assert mood_factor(100, 50) == 1.5
    assert mood_factor(-100, 50) == 0.5
    assert mood_factor(-100, 200) == 0.0
