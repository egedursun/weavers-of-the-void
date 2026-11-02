from collections import Counter

from aerona.engine.primitives.tired_motifs import rising_tags
from aerona.rules.registry import Rules
from aerona.rules.registry.language import LanguageRules


def test_a_tag_that_grew_past_its_earlier_share_is_tired() -> None:
    rules = Rules(language=LanguageRules(motif_min_repeats=2, motif_rising_min_pct=10, motif_rising_ratio_pct=140))
    recent = Counter({"salt": 6, "ash": 3, "reed": 1})
    earlier = Counter({"salt": 4, "ash": 12})
    found = {motif.key for motif in rising_tags(recent, 20, earlier, 40, rules)}
    assert found == {"salt"}
    assert rising_tags(Counter(), 0, earlier, 40, rules) == []
