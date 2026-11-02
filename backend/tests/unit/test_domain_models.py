import pytest
from pydantic import TypeAdapter, ValidationError

from aerona.domain.enums.agent import PendingJobKind, TurnCounter
from aerona.domain.enums.node import NodeKind
from aerona.domain.enums.son import Passion, Stat
from aerona.domain.models.entity_stats import EntityStats, MortalStats, SettlementStats
from aerona.domain.models.node_ref import NodeRef
from aerona.domain.models.phonology import Phonology
from aerona.domain.models.stats import PassionBlock, StatBlock
from aerona.domain.models.turn import PendingJob, TurnContext


def test_stat_block_is_bounded_and_immutable() -> None:
    block = StatBlock.uniform(50)
    raised = block.with_value(Stat.MIGHT, 140)
    assert raised.get(Stat.MIGHT) == 100
    assert block.get(Stat.MIGHT) == 50
    with pytest.raises(ValidationError):
        StatBlock.uniform(0)
    assert PassionBlock(loyalty=1, ambition=2, wrath=3, mercy=4).with_value(Passion.WRATH, -5).wrath == 0


def test_entity_stats_are_discriminated_by_type() -> None:
    adapter: TypeAdapter[EntityStats] = TypeAdapter(EntityStats)
    parsed = adapter.validate_python({"kind": "settlement", "population": 400})
    assert isinstance(parsed, SettlementStats)
    assert parsed.prosperity is None
    with pytest.raises(ValidationError):
        adapter.validate_python({"kind": "mortal", "charisma": 140})
    with pytest.raises(ValidationError):
        adapter.validate_python({"kind": "mortal", "wings": 3})
    assert adapter.dump_python(MortalStats(age=3), mode="json")["kind"] == "mortal"


def test_turn_context_round_trips_and_updates_by_copy() -> None:
    context = TurnContext().bumped(TurnCounter.PRAYERS).bumped(TurnCounter.PRAYERS).with_creation(7)
    context = context.with_pending_job(PendingJob(kind=PendingJobKind.WORLD_BIRTH, essence=70, action_points=1, epoch=4))
    restored = TurnContext.model_validate_json(context.model_dump_json())
    assert restored == context
    assert restored.count(TurnCounter.PRAYERS) == 2
    assert restored.count(TurnCounter.GIFTS) == 0


def test_phonology_checks() -> None:
    phonology = Phonology(
        vowels=("a", "e", "i", "o"), consonants=("l", "m", "n"), forbidden_sounds=("u",), syllable_patterns=("CV",), min_syllables=1, max_syllables=3
    )
    assert phonology.allows_vowel("A")
    assert not phonology.allows_vowel("u")
    assert phonology.forbidden_in("Lumen") == ("u",)


def test_node_ref_key() -> None:
    assert NodeRef(kind=NodeKind.SON, id=3).key == "son:3"
