from aerona.db.kind_concepts.society import BUILT_IN_ORGANISATIONS
from aerona.engine.phases.factions import BLUEPRINTS


def test_every_foundable_organisation_kind_has_a_blueprint() -> None:
    drawn = set(BLUEPRINTS)
    assert all(BLUEPRINTS[kind].kind is kind for kind in drawn)
    assert [kind for kind, body in BUILT_IN_ORGANISATIONS.items() if body.foundable and kind not in drawn] == []
