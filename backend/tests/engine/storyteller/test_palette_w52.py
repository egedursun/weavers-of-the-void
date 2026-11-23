from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.db.tables.storyteller import StorytellerRow
from aerona.domain.enums.storyteller import PaletteDirection, StorytellerProfile
from aerona.engine.storyteller.palette import SPEC_PALETTE
from aerona.engine.storyteller.regions import deeper_aim
from aerona.rules.model import keyed
from aerona.rules.registry import Rules

RULES = Rules()


def test_every_spec_happening_has_a_palette_row_that_names_known_kinds_and_a_weight() -> None:
    known = set(INCIDENT_KINDS)
    missing = [(row.key, key) for row in SPEC_PALETTE for key in row.struck if not any(kind == key or kind.startswith(key) for kind in known)]
    assert missing == []
    assert all(row.rule is not None and keyed(RULES.storyteller, row.rule, "weight") >= 0 for row in SPEC_PALETTE)
    assert {row.direction for row in SPEC_PALETTE} == set(PaletteDirection)


def test_gentle_aims_low_and_seasonal_turns_with_the_seasons() -> None:
    gentle = StorytellerRow(world_id=1, profile=StorytellerProfile.GENTLE, cycle_offset=0, target_points=[])
    seasonal = StorytellerRow(world_id=1, profile=StorytellerProfile.SEASONAL, cycle_offset=0, target_points=[])
    low = deeper_aim(RULES, gentle, 3)
    assert low is not None and low < RULES.storyteller.steady_target
    high, after = deeper_aim(RULES, seasonal, 0, 4), deeper_aim(RULES, seasonal, 2, 4)
    assert high is not None and after is not None and high > after
