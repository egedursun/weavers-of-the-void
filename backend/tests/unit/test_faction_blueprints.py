from aerona.domain.enums.faction import FactionKind, FoundableFaction
from aerona.engine.phases.factions import BLUEPRINTS


def test_every_faction_the_god_may_found_has_a_blueprint_and_every_blueprint_can_be_founded() -> None:
    founded = {kind.value for kind in FoundableFaction}
    assert founded == {plan.kind.value for plan in BLUEPRINTS}
    assert founded <= {kind.value for kind in FactionKind}
