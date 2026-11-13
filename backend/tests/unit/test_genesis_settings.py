from aerona.db.tables.celestial import WorldRow
from aerona.domain.enums.cosmography import WorldAge
from aerona.domain.enums.world import CosmosShape, WorldType
from aerona.domain.models.genesis import GenesisSettings
from aerona.engine.cosmos.worldlife import grown_age
from aerona.rules.registry import Rules


def test_settings_stored_before_the_rename_read_their_darkness_as_danger() -> None:
    stored = GenesisSettings.model_validate({"magic": 40, "darkness": 70, "peoples": 2, "technology": "iron"})
    assert stored.danger == 70
    assert stored.cosmos_shape is CosmosShape.ONE_SUN and stored.world_type is None
    assert "darkness" not in stored.model_dump()
    assert GenesisSettings.model_validate({"magic": 40, "danger": 10, "darkness": 90, "peoples": 2}).danger == 10


def test_a_world_born_old_never_grows_younger_on_the_clock() -> None:
    rules = Rules()
    old = WorldRow(world_type=WorldType.ORDINARY, created_epoch=1, age_stage=WorldAge.OLD)
    assert grown_age(rules, old, 2) is WorldAge.OLD
    young = WorldRow(world_type=WorldType.ORDINARY, created_epoch=1, age_stage=WorldAge.YOUNG)
    assert grown_age(rules, young, 2) is WorldAge.YOUNG
    life = rules.world_life
    assert grown_age(rules, young, 1 + life.young_epochs + life.mature_epochs + life.old_epochs) is WorldAge.DYING
