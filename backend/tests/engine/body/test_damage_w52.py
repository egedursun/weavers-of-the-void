from aerona.catalog.anatomy import anatomy_of
from aerona.catalog.dangers import HAZARDS
from aerona.catalog.engagement import DAMAGE_SECTIONS
from aerona.catalog.harm_kinds import DAMAGE
from aerona.core.random import RandomKey, SeededRandom
from aerona.domain.enums.body import BodyFunction, BodyPlan, DamageType, HarmCause, InjuryKind
from aerona.domain.enums.region import TerrainHazard
from aerona.engine.body.hits import Armour, Harm, harm_resisted, hits_for
from aerona.rules.registry import Rules

RULES = Rules()


def test_eighteen_damage_types_and_asphyxia_reaches_every_table() -> None:
    assert len(DamageType) == 20
    assert DAMAGE[DamageType.ASPHYXIA].breathing and DamageType.ASPHYXIA in DAMAGE_SECTIONS
    drowning = {hazard for hazard, spec in HAZARDS.items() if spec.damage is DamageType.ASPHYXIA}
    assert {TerrainHazard.THIN_ICE, TerrainHazard.FLASH_FLOOD, TerrainHazard.SPRING_FLOOD} <= drowning


def test_the_breathless_and_the_water_breathers_are_spared_lack_of_air() -> None:
    assert harm_resisted(anatomy_of(BodyPlan.CONSTRUCT), DamageType.ASPHYXIA)
    assert harm_resisted(anatomy_of(BodyPlan.AQUATIC), DamageType.ASPHYXIA, HarmCause.DISASTER)
    assert not harm_resisted(anatomy_of(BodyPlan.AQUATIC), DamageType.ASPHYXIA, HarmCause.TORTURE)
    assert not harm_resisted(anatomy_of(BodyPlan.HUMANOID), DamageType.ASPHYXIA, HarmCause.DISASTER)


def test_lack_of_air_strikes_the_parts_that_breathe() -> None:
    body = anatomy_of(BodyPlan.HUMANOID)
    harm = Harm(40, HarmCause.DISASTER, "drowned", damage_type=DamageType.ASPHYXIA)
    hits = hits_for(RULES, body, harm, Armour(), SeededRandom(RandomKey(2, 0, "air")))
    assert hits and all(BodyFunction.BREATH in hit.part.functions for hit in hits)
    assert all(hit.kind in {InjuryKind.ASPHYXIA, InjuryKind.DESTROYED} for hit in hits)
