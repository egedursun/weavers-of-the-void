from aerona.catalog.anatomy import Part, anatomy_of
from aerona.catalog.harm_kinds import INJURIES, asphyxia_wound, blunt_wound
from aerona.catalog.incident_kinds.body_lines import INJURY_PHRASES
from aerona.domain.enums.body import BodyPart, BodyPlan, HarmCause, InjuryKind
from aerona.rules.registry import Rules

RULES = Rules()
BODY = anatomy_of(BodyPlan.HUMANOID)


def part(key: BodyPart) -> Part:
    found = BODY.part(key)
    assert found is not None
    return found


def test_twenty_seven_injury_kinds_each_told_and_cared_for() -> None:
    assert len(InjuryKind) == 30
    assert set(INJURY_PHRASES) == set(InjuryKind) and set(INJURIES) == set(InjuryKind)
    assert all(INJURIES[kind].noted for kind in (InjuryKind.ASPHYXIA, InjuryKind.DISLOCATION, InjuryKind.INTERNAL_BLEEDING))


def test_a_blow_inside_the_body_bleeds_inside_and_a_joint_can_slip_without_breaking() -> None:
    table = RULES.injury
    assert blunt_wound(table, part(BodyPart.GUT), table.blunt_fracture_at, HarmCause.BATTLE) is InjuryKind.INTERNAL_BLEEDING
    assert blunt_wound(table, part(BodyPart.LEFT_ARM), table.blunt_fracture_at - 1, HarmCause.BATTLE) is InjuryKind.DISLOCATION
    assert blunt_wound(table, part(BodyPart.LEFT_ARM), table.blunt_fracture_at, HarmCause.BATTLE) is InjuryKind.FRACTURE


def test_lack_of_air_harms_and_at_its_worst_kills() -> None:
    table = RULES.injury
    assert asphyxia_wound(table, part(BodyPart.LUNGS), 1, HarmCause.DISASTER) is InjuryKind.ASPHYXIA
    assert asphyxia_wound(table, part(BodyPart.LUNGS), table.blunt_crush_at, HarmCause.DISASTER) is InjuryKind.DESTROYED
