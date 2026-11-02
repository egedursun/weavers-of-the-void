from enum import StrEnum

from aerona.constants.language import PEOPLE_COLLECTIVE_ENDINGS
from aerona.domain.enums.entity import EntityType


class HolderTitle(StrEnum):
    KEEPER = "Keeper"
    OWNER = "Owner"
    BEARER = "Bearer"
    GUARDIAN = "Guardian"
    MASTER = "Master"
    TELLER = "Teller"
    RULER = "Ruler"


HOLDER_TITLES: dict[EntityType, HolderTitle] = {
    EntityType.LAW: HolderTitle.KEEPER,
    EntityType.RESOURCE: HolderTitle.OWNER,
    EntityType.ITEM: HolderTitle.BEARER,
    EntityType.TRADITION: HolderTitle.GUARDIAN,
    EntityType.KNOWLEDGE: HolderTitle.MASTER,
    EntityType.STRUCTURE: HolderTitle.OWNER,
    EntityType.ARTWORK: HolderTitle.GUARDIAN,
    EntityType.LANGUAGE: HolderTitle.GUARDIAN,
    EntityType.LEGEND: HolderTitle.TELLER,
}

WITHIN_TYPES = frozenset({EntityType.FACTION, EntityType.CULT, EntityType.ARMY})


def holder_title(governed_type: EntityType) -> HolderTitle:
    return HOLDER_TITLES.get(governed_type, HolderTitle.RULER)


def holder_title_of(governed_type: EntityType, governed_name: str) -> str:
    return f"{holder_title(governed_type).value} of {governed_name}"


def community_phrase(entity_type: EntityType, name: str) -> str:
    if entity_type is EntityType.MORTAL:
        return f"around {name}"
    if entity_type is EntityType.PEOPLE:
        last = name.rsplit(maxsplit=1)[-1].casefold() if name.strip() else ""
        return f"among the {name}" if last in PEOPLE_COLLECTIVE_ENDINGS else f"among the {name} people"
    if entity_type in WITHIN_TYPES:
        return f"within {name}"
    return f"in {name}"


def possessive(name: str) -> str:
    return f"{name}'" if name.endswith(("s", "S")) else f"{name}'s"


def from_among(name: str, plural: str) -> str:
    return f"from among {possessive(name)} {plural}"
