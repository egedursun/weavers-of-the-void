from aerona.catalog.kinds.life_stages import LIFE_STAGES
from aerona.catalog.kinds.morphologies import MORPHOLOGIES
from aerona.catalog.kinds.war_causes import WAR_CAUSES
from aerona.catalog.kinds.world_bodies import WORLD_BODIES
from aerona.domain.enums.mortal import LifeStage
from aerona.domain.enums.war import WarCause
from aerona.domain.enums.world import WorldType
from aerona.engine.belonging.identities import FAITH_CAUSES
from aerona.engine.cosmos.orbits import GAS_WORLDS
from aerona.engine.military.peace import TRADE_CAUSES
from aerona.rules.registry import Rules


def test_every_rule_a_value_table_names_exists() -> None:
    rules = Rules()
    for spec in MORPHOLOGIES.values():
        for key in (spec.fire_rule, spec.hauling_rule, spec.siege_rule):
            assert key is None or isinstance(getattr(rules.morphology, key), int)
    for stage in LIFE_STAGES.values():
        assert stage.age_loss is None or isinstance(getattr(rules.aging, stage.age_loss), int)


def test_world_bodies_keep_the_shape_of_each_kind_of_world() -> None:
    assert all(WORLD_BODIES[kind].radius == 10.0 and WORLD_BODIES[kind].gas == 85 for kind in GAS_WORLDS)
    assert WORLD_BODIES[WorldType.IRON].iron == 70
    assert WORLD_BODIES[WorldType.GREENHOUSE].pressure_factor == 90.0
    assert WORLD_BODIES[WorldType.METHANE].methane == 30
    assert WORLD_BODIES[WorldType.SUPER_EARTH].radius == 1.6


def test_war_cause_classes_come_from_the_table() -> None:
    assert {WarCause.HOLY_WAR, WarCause.SCHISM, WarCause.DIVINE_GRUDGE} == FAITH_CAUSES
    assert {WarCause.TRADE_ROUTE, WarCause.RESOURCE, WarCause.DEBT} == TRADE_CAUSES
    assert {cause for cause, spec in WAR_CAUSES.items() if spec.within_realm} == {
        WarCause.CLAIM,
        WarCause.INDEPENDENCE,
        WarCause.SUCCESSION,
        WarCause.UPRISING,
        WarCause.TRIBUTE_REVOLT,
    }


def test_only_the_old_stop_recovering_and_only_grown_folk_come_of_age() -> None:
    assert {stage for stage, spec in LIFE_STAGES.items() if not spec.recovers} == {LifeStage.ELDER, LifeStage.ANCIENT}
    assert {stage for stage, spec in LIFE_STAGES.items() if spec.counts_as_adult} == {LifeStage.ADULT, LifeStage.ELDER}
