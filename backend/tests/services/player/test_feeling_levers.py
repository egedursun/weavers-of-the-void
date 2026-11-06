import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.tables.mind import DreamRow, GriefRow, ThoughtRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import DreamKind, DreamReading, Emotion, GriefStage, MoodState, ThoughtKind
from aerona.services.player import feelings
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld, make_entity


async def test_the_god_sends_reshapes_and_takes_away_thoughts_and_holds_a_mood(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    hero = await make_entity(session, "Vash", EntityType.MORTAL, world_id=world.world.id, location_id=world.region.id)
    sent = await feelings.send_thought(scope, feelings.SendThought(holder_id=hero.id, kind=ThoughtKind.SAW_MIRACLE, intensity=40, emotion=Emotion.HOPE))
    row = await session.get(ThoughtRow, sent.values["thought_id"])
    assert row is not None and row.emotion is Emotion.HOPE
    await feelings.edit_thought(scope, feelings.EditThought(thought_id=row.id, intensity=90, decay_pct=5))
    assert row.intensity == 90 and row.decay_pct == 5
    await feelings.remove_thought(scope, feelings.ThoughtTarget(thought_id=row.id))
    assert await session.get(ThoughtRow, row.id) is None
    await feelings.set_mood(scope, feelings.SetMood(node_id=hero.id, score=-85))
    profile = await session.get(MortalProfileRow, hero.id)
    assert profile is not None and profile.mood is MoodState.BROKEN and "mood" in profile.locked
    region = world.region
    with pytest.raises(ValidationFailedError):
        await feelings.send_thought(scope, feelings.SendThought(holder_id=region.id))


async def test_the_god_begins_moves_and_lifts_a_grief(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    mourner = await make_entity(session, "Ilka", EntityType.MORTAL, world_id=world.world.id, location_id=world.region.id)
    lost = await make_entity(session, "Teo", EntityType.MORTAL, world_id=world.world.id, location_id=world.region.id)
    made = await feelings.begin_grief(scope, feelings.StartGrief(mourner_id=mourner.id, deceased_id=lost.id, strength=80))
    row = await session.get(GriefRow, made.values["grief_id"])
    assert row is not None and row.stage is GriefStage.SHOCK
    await feelings.edit_grief(scope, feelings.EditGrief(grief_id=row.id, stage=GriefStage.ACCEPTANCE, length_epochs=6))
    assert row.stage is GriefStage.ACCEPTANCE and row.length_epochs == 6
    await feelings.remove_grief(scope, feelings.GriefTarget(grief_id=row.id))
    assert await session.get(GriefRow, row.id) is None


async def test_the_god_sends_reads_and_erases_a_dream(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    dreamer = await make_entity(session, "Sela", EntityType.MORTAL, world_id=world.world.id, location_id=world.region.id)
    made = await feelings.send_dream(scope, feelings.SendDream(dreamer_id=dreamer.id, kind=DreamKind.PROPHETIC, intensity=70))
    row = await session.get(DreamRow, made.values["dream_id"])
    assert row is not None and row.kind is DreamKind.PROPHETIC
    await feelings.edit_dream(scope, feelings.EditDream(dream_id=row.id, reading=DreamReading.OMEN_OF_WAR, reading_true=True, recurring=True))
    assert row.reading is DreamReading.OMEN_OF_WAR and row.reading_true and row.recurring
    await feelings.remove_dream(scope, feelings.DreamTarget(dream_id=row.id))
    assert await session.get(DreamRow, row.id) is None
