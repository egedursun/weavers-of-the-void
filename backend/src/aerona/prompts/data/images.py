import re
from dataclasses import dataclass
from enum import StrEnum

from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.travel import VehicleKind

DEFAULT_DIRECTION = "the subject in its setting"
AMBIENCE_BIOME_COUNT = 5

IMAGE_DIRECTION: dict[EntityType, str] = {
    EntityType.LANGUAGE: "an object that shows this language: a carved tablet, manuscript page, inscription or glyph-covered artifact",
    EntityType.KNOWLEDGE: "people practicing this technique or knowledge, with its tools, materials and workplace",
    EntityType.TRADITION: "the ritual or festival being performed by the community",
    EntityType.LEGEND: "a scene illustrating the legend at its turning point",
    EntityType.NATURAL_LAW: "a cosmic visual metaphor of this natural law at work in the world",
    EntityType.PROPHECY: "a visionary scene of the prophecy, as a seer would see it",
    EntityType.EVENT: "the event as it happens, caught in the moment",
    EntityType.CELESTIAL: "the celestial body in the night sky above the landscape",
    EntityType.PEOPLE: "a group portrait of these people in their daily life: clothing, tools, faces, dwellings behind them",
    EntityType.SETTLEMENT: "an establishing shot of the settlement from a nearby rise, people and smoke for life and scale",
    EntityType.MORTAL: "a full-length character portrait in their environment; face, garments, posture that reveal their role",
    EntityType.ARMY: "the army on the march or arrayed for battle, banners and equipment, dust and weather",
    EntityType.TRADE_ROUTE: "the route seen from along its way: the way goods and travellers move along it, its stopping places and the land it crosses",
    EntityType.STRUCTURE: "the monument or work in its setting, with people for scale",
    EntityType.ITEM: "a museum-grade still life of the object on a surface that fits its origin, raking light",
    EntityType.RESOURCE: "the resource where it is found or harvested, with the workers or creatures who gather it",
    EntityType.SPIRIT: "a translucent presence half-visible in a place of this world, uncanny but restrained",
    EntityType.REGION: "a sweeping landscape of the region, atmospheric perspective, characteristic weather",
    EntityType.PLACE: "the place itself in its surroundings, characteristic light and weather",
    EntityType.SPECIES: "the creature in its habitat, observed in the wild",
    EntityType.VESSEL: "the vehicle or conveyance in use, with its crew or riders",
    EntityType.OUTER_BEING: "an Outer Being: NEVER show it fully, only a fragment, a silhouette, a reflection, or its effect on the world",
    EntityType.CULT: "the cult gathered at its rite: robed members, sacred objects, the place of worship, faces lit by its particular light",
    EntityType.FACTION: "members of the faction in their meeting place, their insignia, colors and tools of their trade, a sense of hierarchy",
    EntityType.ARTWORK: "the artwork itself (song performed, statue, fresco, book) in the place it is kept or performed, with its audience or keeper",
    EntityType.LAW: "the law being proclaimed or carved: a stele, scroll or assembly, the people who live under it watching",
    EntityType.PHENOMENON: "the phenomenon over the land it holds, at a scale that shows the whole region",
    EntityType.COSMIC_BEING: "the being at its own scale against the place it is in, with something in view that shows its size",
}

VESSEL_DIRECTIONS: dict[VehicleKind, str] = {
    VehicleKind.GATE: "a gate between worlds: its frame, what shows through it, travellers before it for scale",
    VehicleKind.SHIP: "a vessel between worlds: its frame and what moves it, its crew, the way it crosses",
    VehicleKind.MOUNT: "a mount carrying its rider between worlds, in motion, at a scale that shows its size",
    VehicleKind.BRIDGE: "a bridge spanning the gap between worlds, travellers crossing it",
}

MEGAFAUNA_DIRECTION = "a colossal megafauna in its habitat with small figures of the folk who live there for scale, seen from a distance"

OUTER_BEING_TAIL = ", shown only partially: a fragment glimpsed through fog, glare or a reflection, its full shape never visible."
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
    CosmosSubjectKind.WORLD: "the whole world seen from orbit or high above its sky, its unique physics visible (rings, seas, ice, glow), then a hint of its surface",
    CosmosSubjectKind.STAR: "the star itself in deep space with its planets as small discs nearby, its color and character exaggerated just enough",
    CosmosSubjectKind.FOREIGN_GOD: "a foreign god as its worshippers imagine it: a monumental idol or vision in its home world",
    CosmosSubjectKind.SON: "a divine child of the creator, a god in full figure as their worshippers see them, their two domains shaping their body, garb and the light around them, of the age, form and gender their description gives",
    CosmosSubjectKind.CREATOR: "the creator, a primordial god at the scale of the cosmos they shaped, a full-figure vision among stars and newborn worlds, in the form their description gives",
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
