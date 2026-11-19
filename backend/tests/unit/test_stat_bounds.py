from typing import get_args

from aerona.catalog.entity_types import ENTITY_TYPES
from aerona.constants.engine import UNBOUNDED_STAT
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.models.entity_stats import EntityStats, PeopleStats
from aerona.engine.primitives.stats import model_bounds, put_stat, stat_bounds
from aerona.rules.registry import Rules

MODELS = {model.model_fields["kind"].default: model for model in get_args(get_args(EntityStats)[0])}


def test_a_stat_the_catalogue_leaves_unbounded_still_stops_at_its_model_bound() -> None:
    people = EntityRow(name="Folk", entity_type=EntityType.PEOPLE, stats=PeopleStats(wealth=100))
    assert put_stat(Rules(), people, "wealth", 101) == 100


def test_no_stat_of_any_type_is_bounded_wider_than_its_model_allows() -> None:
    rules = Rules()
    for entity_type in ENTITY_TYPES:
        model = MODELS.get(entity_type.value)
        if model is None:
            continue
        thing = EntityRow(name="Thing", entity_type=entity_type, stats=model())
        for key in model.model_fields:
            if key == "kind":
                continue
            low, high = stat_bounds(rules, thing, key)
            floor, ceiling = model_bounds(thing, key)
            assert low >= floor, (entity_type, key)
            assert ceiling is None or (high != UNBOUNDED_STAT and high <= ceiling), (entity_type, key)
