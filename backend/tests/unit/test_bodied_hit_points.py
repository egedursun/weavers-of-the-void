import typing

from aerona.domain.models.entity_stats import EntityStats
from aerona.engine.body.book import BODIED


def test_every_kind_that_grows_a_body_keeps_its_hit_points() -> None:
    models = {model.model_fields["kind"].default: model for model in typing.get_args(typing.get_args(EntityStats)[0])}
    assert [kind.value for kind in BODIED if "hp" not in models[kind.value].model_fields] == []
