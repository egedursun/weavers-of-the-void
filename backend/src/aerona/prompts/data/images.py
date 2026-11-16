import re
from dataclasses import dataclass
from enum import StrEnum

from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.travel import VehicleKind

DEFAULT_DIRECTION = "the subject in its setting"
AMBIENCE_BIOME_COUNT = 5

IMAGE_DIRECTION: dict[EntityType, str] = {
    EntityType.LANGUAGE: "this language in use as its speakers make it seen, heard or felt, among those who use it",
    EntityType.KNOWLEDGE: "those who practise this knowledge at work, with what they use for it and where they do it",
    EntityType.TRADITION: "the tradition as its keepers practise it, among the community that keeps it",
    EntityType.LEGEND: "a scene illustrating the legend at its turning point",
    EntityType.NATURAL_LAW: "this natural law at work in the world, shown by what it does to the things it governs",
    EntityType.PROPHECY: "the prophecy as it is foreseen",
    EntityType.EVENT: "the event as it happens, caught in the moment",
    EntityType.CELESTIAL: "the body of the sky as it is seen from the world beneath it",
    EntityType.PEOPLE: "these people together in their daily life, as their account gives them",
    EntityType.SETTLEMENT: "the settlement seen whole from nearby, its inhabitants in view for life and scale",
    EntityType.MORTAL: "a full portrait of them in their surroundings that shows their role",
    EntityType.ARMY: "the army on the move or drawn up, as its makers field it",
    EntityType.TRADE_ROUTE: "the route seen from along its way: the way goods and travellers move along it, its stopping places and the land it crosses",
    EntityType.STRUCTURE: "the work in its setting, with those who use it in view for scale",
    EntityType.ITEM: "the object itself, whole, on a surface that fits its origin",
    EntityType.RESOURCE: "the resource where it is found or harvested, with the workers or creatures who gather it",
    EntityType.SPIRIT: "the spirit as its account gives it, in a place of this world",
    EntityType.REGION: "the region seen whole, its land and weather as its account gives them",
    EntityType.PLACE: "the place itself in its surroundings",
    EntityType.SPECIES: "the kind in the place where it lives",
    EntityType.VESSEL: "the vehicle or conveyance in use, with its crew or riders",
    EntityType.OUTER_BEING: "an Outer Being: only part of it in view, or its effect on the world, its whole shape never shown",
    EntityType.CULT: "the cult as its account gives it, its faithful in the place where they worship",
    EntityType.FACTION: "members of the faction where they meet, as its account gives them",
    EntityType.ARTWORK: "the work itself where it is kept or performed, with those who keep or hear it",
    EntityType.LAW: "the law as it is made known to those who live under it",
    EntityType.PHENOMENON: "the phenomenon over the land it holds, at a scale that shows the whole region",
    EntityType.COSMIC_BEING: "the being at its own scale against the place it is in, with something in view that shows its size",
    EntityType.VEHICLE_TYPE: "the vehicle as its makers build it, seen whole from the side so its sections and fittings show, in a place where it is made or used",
    EntityType.UNIT_TYPE: "soldiers of this kind standing together in their gear and order, as their makers field them",
    EntityType.EQUIPMENT_MODEL: "the piece itself, whole, on a surface that fits its makers, with its make and material clear",
    EntityType.DISH: "the dish as its makers serve it, with the foods it is made of and the vessels it is served in",
    EntityType.BUILDING_TYPE: "a building of this type as its makers raise it, whole, with its form, storeys and material clear",
    EntityType.NETWORK: "the stations and links of the network across the land it joins, with what passes along them",
}

VESSEL_DIRECTIONS: dict[VehicleKind, str] = {
    VehicleKind.GATE: "a gate between worlds with what shows through it and travellers before it for scale",
    VehicleKind.SHIP: "a vessel between worlds with what moves it and its crew on the way it crosses",
    VehicleKind.MOUNT: "a mount carrying its rider between worlds, in motion, at a scale that shows its size",
    VehicleKind.BRIDGE: "a bridge spanning the gap between worlds, travellers crossing it",
}

MEGAFAUNA_DIRECTION = "a colossal megafauna in its habitat with small figures of the folk who live there for scale, seen from a distance"

OUTER_BEING_TAIL = ", shown only in part, its whole shape never in view."
OUTER_BEING_WORDS = re.compile(
    r"\b(partial|partially|fragment|silhouette|glimpse|glimpsed|obscured|hidden|reflection|never (fully )?(seen|visible|shown))\b", re.IGNORECASE
)
SCALE_TAIL = ", with small figures of the folk who live there for scale."
SCALE_WORDS = re.compile(r"\b(scale|tiny (human )?figures?|dwarf(ed|s|ing)?|colossal|towering over)\b", re.IGNORECASE)


class CosmosSubjectKind(StrEnum):
    WORLD = "world"
    STAR = "star"
    FOREIGN_GOD = "foreign_god"
    SON = "son"
    CREATOR = "creator"
    GALAXY = "galaxy"
    CLUSTER = "cluster"
    DIMENSION = "dimension"


COSMOS_DIRECTION: dict[CosmosSubjectKind, str] = {
    CosmosSubjectKind.WORLD: "the whole world seen from high above its sky with its own physics in view, then a hint of its surface",
    CosmosSubjectKind.STAR: "the star itself in deep space with its planets as small discs nearby, as its type and account give it",
    CosmosSubjectKind.FOREIGN_GOD: "a foreign god as its worshippers imagine it, in its home world",
    CosmosSubjectKind.SON: "a divine child of the creator, a god in full figure as their worshippers see them, shaped by their two domains, of the age, form and gender their description gives",
    CosmosSubjectKind.CREATOR: "the creator, a primordial god in full figure at the scale of the cosmos they shaped, in the form their description gives",
    CosmosSubjectKind.GALAXY: "the whole galaxy seen from far outside it, its form, nucleus and age as its type and account give them",
    CosmosSubjectKind.CLUSTER: "the whole cluster seen from far outside it, its galaxies gathered as its kind and account give them",
    CosmosSubjectKind.DIMENSION: "the dimension as a traveller would first see it on arriving, its nature, laws and light as its kind and account give them",
}


@dataclass(frozen=True)
class ImageSubjectTraits:
    entity_type: EntityType
    megafauna: bool
    vehicle: VehicleKind | None = None


def image_direction(traits: ImageSubjectTraits) -> str:
    if traits.entity_type is EntityType.VESSEL and traits.vehicle is not None:
        return VESSEL_DIRECTIONS[traits.vehicle]
    if traits.entity_type is EntityType.SPECIES and traits.megafauna:
        return MEGAFAUNA_DIRECTION
    return IMAGE_DIRECTION.get(traits.entity_type, DEFAULT_DIRECTION)


def fix_image_prompt(prompt: str, entity_type: EntityType, megafauna: bool, max_chars: int) -> str:
    body = prompt.strip()
    tail = ""
    if entity_type is EntityType.OUTER_BEING and not OUTER_BEING_WORDS.search(body):
        tail = OUTER_BEING_TAIL
    elif megafauna and not SCALE_WORDS.search(body):
        tail = SCALE_TAIL
    if tail:
        body = body.rstrip(" .")
    room = max(0, max_chars - len(tail))
    return body[:room] + tail
