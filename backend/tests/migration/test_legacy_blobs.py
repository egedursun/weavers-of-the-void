from aerona.domain.enums.agent import CouncilVote
from aerona.domain.enums.meta import ScoreComponent
from aerona.domain.enums.travel import JourneyEventKind
from aerona.migration.legacy.blobs import council_minutes, journey_events, score_breakdown
from aerona.migration.legacy.vocabulary import load_vocabulary

VOCABULARY = load_vocabulary()


def test_old_council_minutes_keep_speeches_ballots_and_the_verdict() -> None:
    payload = {
        "konu": "The flood",
        "cagiran": "kader",
        "konusmalar": [{"ogul_id": 3, "ad": "Velm", "soz": "Let the river rest."}, {"ogul_id": None, "soz": "lost"}],
        "onerge": "Raise the banks",
        "oylar": [{"ogul_id": 3, "ad": "Velm", "oy": "evet", "gerekce": "it is time"}, {"ogul_id": 4, "oy": "perhaps"}],
        "kabul": True,
        "karar": "The banks rise.",
        "notlar": ["first", None, "second"],
        "tutanak": "They agreed.",
    }
    minutes = council_minutes(VOCABULARY, payload, "fallback topic", {3: 30})
    assert minutes.topic == "The flood" and minutes.convened_by == "fate" and minutes.passed
    assert [(speech.son_id, speech.words) for speech in minutes.speeches] == [(30, "Let the river rest.")]
    assert [(ballot.son_id, ballot.vote) for ballot in minutes.ballots] == [(30, CouncilVote.YES)]
    assert minutes.notes == ("first", "second") and minutes.summary == "They agreed."
    empty = council_minutes(VOCABULARY, {}, "fallback topic", {})
    assert empty.topic == "fallback topic" and empty.convened_by == "creator" and not empty.passed


def test_old_journey_events_keep_their_epoch_and_loss_and_skip_blank_ones() -> None:
    events = journey_events(
        VOCABULARY, [{"cag": 4, "olay": "a storm", "kayip": 20}, {"cag": -2, "olay": "lost the way"}, {"olay": None}], 2, lambda _: JourneyEventKind.OTHER
    )
    assert [(event.epoch, event.text, event.loss) for event in events] == [(4, "a storm", 20), (2, "lost the way", 0)]


def test_an_old_score_breaks_down_by_known_parts_and_names_the_rest() -> None:
    breakdown, unknown = score_breakdown(VOCABULARY, {"nufus": 12, "dunyalar": "3", "mystery": 9, "diller": "many"})
    assert breakdown.parts == {ScoreComponent.POPULATION: 12, ScoreComponent.WORLDS: 3}
    assert sorted(unknown) == ["diller", "mystery"]
