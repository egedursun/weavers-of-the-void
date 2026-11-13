from collections import Counter

from aerona.catalog.equipment import FAMILIES, ROLE_ARMS, UNIT_SLOTS
from aerona.catalog.units import ROLE_STYLES, UNITS
from aerona.catalog.vehicles import FRAMES, LAYOUTS, MOUNTS
from aerona.domain.enums.environment import TerrainKind
from aerona.domain.enums.military import UnitKind
from aerona.domain.enums.vehicles import MountKind, Propulsion, VehicleDomain, VehicleFamily, VehicleFrame
from aerona.engine.collective.designs import MOUNT_ARCS, home_section
from aerona.engine.equipment.models import MOUNT_FAMILIES
from aerona.engine.vehicles.caravans import suits

FRAMES_PER_DOMAIN = 3


def test_every_domain_a_vehicle_can_go_has_several_frames() -> None:
    counts = Counter(spec.domain for spec in FRAMES.values())
    assert {domain.value: counts[domain] for domain in VehicleDomain if counts[domain] < FRAMES_PER_DOMAIN} == {}


def test_every_way_of_moving_drives_some_frame() -> None:
    used = {spec.propulsion for spec in FRAMES.values()}
    assert [propulsion.value for propulsion in Propulsion if propulsion not in used] == []


def test_every_role_arms_its_slots_with_families_of_that_slot() -> None:
    wrong = [
        (role.value, slot.value, family.value)
        for role, kit in ROLE_ARMS.items()
        for slot, families in kit.items()
        for family in families
        if FAMILIES[family].slot is not slot
    ]
    unused = [(role.value, slot.value) for role, kit in ROLE_ARMS.items() for slot in kit if slot not in UNIT_SLOTS[UNITS[role].family]]
    assert wrong == []
    assert unused == []


def test_every_role_has_a_doctrine_to_fall_back_on() -> None:
    assert set(ROLE_STYLES) == set(UnitKind)


def test_every_mount_kind_is_aimed_and_finds_a_section_on_every_family_that_carries_it() -> None:
    assert set(MOUNT_ARCS) == set(MountKind)
    assert all(MOUNT_FAMILIES[mount] for mount in MountKind)
    unseated = [
        (family.value, mount.value)
        for family in VehicleFamily
        for mount in MOUNTS[family]
        if home_section(mount, {part.section for part in LAYOUTS[family]}) is None
    ]
    assert unseated == []


def test_sledges_are_drawn_only_where_the_ground_holds_snow() -> None:
    sledge = FRAMES[VehicleFrame.SLEDGE]
    assert not suits(sledge, TerrainKind.PLAIN)
    assert not suits(sledge, None)
    assert suits(sledge, TerrainKind.TUNDRA)
    assert suits(FRAMES[VehicleFrame.CART], TerrainKind.PLAIN)
