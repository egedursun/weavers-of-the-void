from enum import StrEnum

from aerona.domain.enums.agrarian import LandUseRing
from aerona.domain.enums.body import MaimedKind
from aerona.domain.enums.collective import DatingSystemKind, NormBehaviour, NormSituation, RoleEligibility, RoleKind, Tincture
from aerona.domain.enums.cosmography import OmenReading
from aerona.domain.enums.culture import LanguageRegister, SpeakerKind, Technique
from aerona.domain.enums.cycles import ReproductiveCaste
from aerona.domain.enums.discovery import AgeKind, BlueprintKind
from aerona.domain.enums.divine import OuterHunger
from aerona.domain.enums.ecology import AnimalRole
from aerona.domain.enums.evolution import EvolvedTrait
from aerona.domain.enums.faction import MovementCause
from aerona.domain.enums.law_depth import JurisdictionClaim
from aerona.domain.enums.military import CommanderTrait
from aerona.domain.enums.mind import EthicalStance, HonourModel, PressureKind, WantKind
from aerona.domain.enums.operations import CrewStation, PointOfSail, ShotKind
from aerona.domain.enums.relations import CircleKind
from aerona.domain.enums.society_depth import DriftCause
from aerona.domain.enums.statecraft import NobleWant, SubjectKind, TaxKind
from aerona.domain.enums.structure import StructureSection
from aerona.domain.enums.urban import RacketKind
from aerona.domain.enums.vehicles import VehicleSection


def first(kind: type[StrEnum]) -> str:
    return next(iter(kind)).value


def last(kind: type[StrEnum]) -> str:
    return list(kind)[-1].value


TINCTURE = first(Tincture)
DATING = last(DatingSystemKind)
SITUATION = first(NormSituation)
BEHAVIOUR = first(NormBehaviour)
STANCE = next(stance.value for stance in EthicalStance if stance is not EthicalStance.ACCEPTABLE)
ROLE = first(RoleKind)
ELIGIBILITY = last(RoleEligibility)
OMEN = first(OmenReading)
REGISTER = first(LanguageRegister)
SPEAKER = first(SpeakerKind)
CASTE = first(ReproductiveCaste)
AGE = last(AgeKind)
BLUEPRINT = first(BlueprintKind)
ANIMAL_ROLE = first(AnimalRole)
MOVEMENT = first(MovementCause)
CLAIM = first(JurisdictionClaim)
COMMANDER_TRAIT = first(CommanderTrait)
WANT = first(WantKind)
PRESSURE = first(PressureKind)
HONOUR = last(HonourModel)
DRIFT = first(DriftCause)
STATION = first(CrewStation)
POINT_OF_SAIL = last(PointOfSail)
SHOT = last(ShotKind)
CIRCLE = first(CircleKind)
NOBLE_WANT = first(NobleWant)
SUBJECT = first(SubjectKind)
TAX = first(TaxKind)
RACKET = first(RacketKind)
VEHICLE_SECTION = first(VehicleSection)
STRUCTURE_SECTION = first(StructureSection)
RING = last(LandUseRing)
MAIMED = first(MaimedKind)
TECHNIQUE_BASE = first(Technique)
OUTER_HUNGER = last(OuterHunger)
EVOLVED_TRAIT = first(EvolvedTrait)
