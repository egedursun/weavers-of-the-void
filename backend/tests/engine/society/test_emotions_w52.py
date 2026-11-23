from sqlalchemy import select

from aerona.catalog.thoughts import EMOTIONS
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.mind import MemoryRow, ThoughtRow
from aerona.domain.enums.mind import Emotion, MemoryKind, ThoughtKind
from aerona.engine.mind.emotions_w52 import act_on
from aerona.engine.mind.thoughts import think
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, mortal, tuned

RULES = Rules()
NEW = (Emotion.SURPRISE, Emotion.CURIOSITY, Emotion.COMPASSION, Emotion.CONTEMPT)


def test_twenty_eight_emotions_each_with_its_own_decay_and_the_new_four_push_acts() -> None:
    assert len(EMOTIONS) == len(Emotion) == 28
    assert all(0 <= spec.decay(RULES) <= 50 for spec in EMOTIONS.values())
    assert all(EMOTIONS[emotion].act_weight is not None for emotion in NEW)
    assert EMOTIONS[Emotion.SURPRISE].decay(RULES) > EMOTIONS[Emotion.JOY].decay(RULES)


async def test_a_surprise_sharpens_the_next_feeling_of_the_same_epoch(realm: Realm) -> None:
    calm, startled = await mortal(realm, "Calm"), await mortal(realm, "Startled")
    first = await think(realm.session, RULES, calm.id, ThoughtKind.SAW_MIRACLE, 3, intensity=30)
    await think(realm.session, RULES, startled.id, ThoughtKind.WAS_SURPRISED, 3)
    second = await think(realm.session, RULES, startled.id, ThoughtKind.SAW_MIRACLE, 3, intensity=30)
    assert first is not None and second is not None and second.intensity > first.intensity


async def test_compassion_gives_and_contempt_insults(realm: Realm) -> None:
    giver, sufferer = await mortal(realm, "Giver"), await mortal(realm, "Sufferer")
    sure = tuned(emotions={"compassion_act_weight": 100, "contempt_act_weight": 100, "felt_intensity": 0})
    ctx = context(realm.session, sure)
    pity = await think(realm.session, sure, giver.id, ThoughtKind.FELT_COMPASSION, 3, subject_id=sufferer.id, intensity=80)
    scorn = await think(realm.session, sure, giver.id, ThoughtKind.FELT_CONTEMPT, 3, subject_id=sufferer.id, intensity=80)
    assert pity is not None and scorn is not None
    assert await act_on(ctx, giver, pity) and await act_on(ctx, giver, scorn)
    kinds = set(await realm.session.scalars(select(MemoryRow.kind).where(MemoryRow.holder_node_id == sufferer.id)))
    assert {MemoryKind.GIFTED_ME, MemoryKind.HUMILIATED_ME} <= kinds
    assert "mind.emotion_felt" in set(await realm.session.scalars(select(IncidentRow.kind)))
    assert (await realm.session.scalar(select(ThoughtRow.emotion).where(ThoughtRow.id == pity.id))) is Emotion.COMPASSION
