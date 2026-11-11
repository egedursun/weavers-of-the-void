from aerona.domain.enums.faction import FactionKind, FoundableFaction
from aerona.engine.phases.factions import BLUEPRINTS


def test_every_foundable_faction_has_a_blueprint() -> None:
    drawn = {item.kind for item in BLUEPRINTS}
    assert [kind for kind in FoundableFaction if FactionKind(kind.value) not in drawn] == []
