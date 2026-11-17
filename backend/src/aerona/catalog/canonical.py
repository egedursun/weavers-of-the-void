from collections.abc import Iterable, Mapping
from enum import StrEnum

from aerona.domain.enums.culture import ArtMode
from aerona.domain.enums.cycles import ReproductiveSystem
from aerona.domain.enums.demography import FuneralCustom, MotifSource
from aerona.domain.enums.ecology import AnimalRole, Diet
from aerona.domain.enums.kinds import GoodCategory
from aerona.domain.enums.mind import Attribute
from aerona.domain.enums.mythic import ServitorRole
from aerona.domain.enums.society_kinds import OrganisationPurpose, ProfessionCategory
from aerona.domain.enums.son import Stat
from aerona.domain.enums.unions import UnionForm
from aerona.domain.enums.urban import HousingLevel

CANONICAL: Mapping[str, type[StrEnum]] = {
    "housing": HousingLevel,
    "mind and body abilities": Attribute,
    "abilities of gods": Stat,
    "servitors": ServitorRole,
    "organisations": OrganisationPurpose,
    "goods": GoodCategory,
    "work": ProfessionCategory,
    "sexes": ReproductiveSystem,
    "funerals": FuneralCustom,
    "diets": Diet,
    "marriage": UnionForm,
    "art": ArtMode,
    "plant and animal uses": AnimalRole,
    "aesthetics": MotifSource,
}

RETIRED: Mapping[str, tuple[str, ...]] = {
    "housing": ("DwellingKind",),
    "mind and body abilities": ("Ability",),
    "servitors": ("ServitorRank",),
    "diets": ("FolkDiet",),
    "marriage": ("MarriageKind", "MarriageCustom", "MarriagePreference", "MarriagePayment"),
    "aesthetics": ("Aesthetic",),
    "art": ("ArtMedium", "ArtDiscipline"),
    "plant and animal uses": ("SpeciesUse",),
}


def parallel_enums(names: Iterable[str]) -> list[str]:
    canonical = {kind.__name__ for kind in CANONICAL.values()}
    retired = {name for group in RETIRED.values() for name in group}
    return sorted(name for name in set(names) if name in retired and name not in canonical)
