from types import SimpleNamespace
from typing import Any, cast

import pytest

from aerona.catalog.estates import ESTATE_CLASSES, ESTATE_LAWS, ESTATE_NAMES, PRIVILEGE_WISHES
from aerona.catalog.laws import LAW_PARAMS
from aerona.catalog.materials import SPECIES_GOODS, SPECIES_GROUNDS
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.domain.enums.collective import PartitionLine
from aerona.domain.enums.culture import ItemClass
from aerona.domain.enums.economy import ExtractionKind, MaterialOrigin
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.eras import ProgrammeStage
from aerona.domain.enums.mortal import EquipmentSlot
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.travel import VehicleKind
from aerona.engine.body import hits
from aerona.engine.collective.armory import along
from aerona.engine.economy import deposits, household
from aerona.engine.economy.extraction import KIND_JOBS, labour_pool
from aerona.engine.economy.provenance import HULLS, wanted_slots
from aerona.engine.eras.progress import STAGE_WORDS
from aerona.engine.mortal.equipment import fits_slot
from aerona.engine.phases import travel
from aerona.engine.polity import offices
from aerona.engine.transform import run
from aerona.prompts.data.images import ImageSubjectTraits, image_direction
from aerona.rules.registry import Rules

IMAGE_WORDS = ("blood", "bone", "scale", "wound", "smith")


class Book:
    def hands(self, community_id: int, job: object) -> int:
        return 40


class Session:
    def __init__(self, kind: VehicleKind) -> None:
        self.kind = kind

    async def get(self, table: type, key: int) -> object:
        return SimpleNamespace(kind=self.kind) if table is VesselProfileRow else None


@pytest.mark.parametrize("kind", list(ExtractionKind))
def test_every_way_of_extraction_finds_its_hands(kind: ExtractionKind) -> None:
    assert labour_pool(Rules(), cast(Any, Book()), cast(Any, SimpleNamespace(id=1)), kind) > 0
    assert kind in KIND_JOBS


@pytest.mark.parametrize("kind", list(VehicleKind))
async def test_every_kind_of_vessel_has_hull_materials(kind: VehicleKind) -> None:
    vessel = cast(Any, SimpleNamespace(id=7, entity_type=EntityType.VESSEL))
    slots = await wanted_slots(cast(Any, Session(kind)), vessel)
    assert slots[next(iter(slots))] == HULLS[kind] and HULLS[kind]


@pytest.mark.parametrize("kind", list(VehicleKind))
def test_every_kind_of_vessel_has_an_image_direction(kind: VehicleKind) -> None:
    assert image_direction(ImageSubjectTraits(entity_type=EntityType.VESSEL, megafauna=False, vehicle=kind))


@pytest.mark.parametrize("social_class", list(SocialClass))
def test_every_class_can_gather_as_an_estate_with_a_valid_law(social_class: SocialClass) -> None:
    kind, params = ESTATE_LAWS[social_class]
    assert ESTATE_NAMES[social_class] and PRIVILEGE_WISHES[social_class]
    assert all(name in LAW_PARAMS[kind] and LAW_PARAMS[kind][name].valid(value) for name, value in params.items())


def test_the_engine_still_founds_only_its_own_estate_classes() -> None:
    assert set(ESTATE_CLASSES) < set(SocialClass)


def test_every_stage_of_a_programme_has_words() -> None:
    assert set(STAGE_WORDS) == set(ProgrammeStage) and all(STAGE_WORDS.values())


def test_a_straight_partition_line_keeps_its_points() -> None:
    points = [(0.0, 0.0), (10.0, 0.0)]
    assert along(points, PartitionLine.STRAIGHT) == points


@pytest.mark.parametrize("origin", list(MaterialOrigin))
def test_every_origin_of_a_substance_is_told_plainly(origin: MaterialOrigin) -> None:
    words = deposits.ORIGIN_WORDS[origin]
    assert words and not any(image in words for image in IMAGE_WORDS)


def test_a_mount_slot_fits_no_item() -> None:
    profile = cast(Any, SimpleNamespace(item_class=ItemClass.SHIELD, material=None))
    assert fits_slot(EquipmentSlot.MOUNT, profile) is False


def test_the_reads_proven_safe_still_hold() -> None:
    assert set(hits.FIXED_KINDS) | set(hits.KIND_RULES) == set(type(next(iter(hits.FIXED_KINDS))))
    assert not set(hits.FIXED_KINDS) & set(hits.KIND_RULES)
    assert set(household.FUEL_FAMILY) - {household.CommodityKind.FUEL, household.CommodityKind.TIMBER} <= set(household.FUEL_HEAT)
    assert {*travel.MEDIUM_EVENTS.values(), *travel.COMMON_EVENTS, travel.JourneyEventKind.PIRATES} <= set(travel.LOSS_TEXT) & set(travel.ROAD_EVENT_TEXT)
    assert set(offices.POWER_SKILLS.values()) <= set(offices.OFFICE_SKILLS)
    assert {good for goods in SPECIES_GOODS.values() for good in goods} <= set(SPECIES_GROUNDS)
    assert set(run.WARNED_KINDS) == set(run.WARNINGS)
