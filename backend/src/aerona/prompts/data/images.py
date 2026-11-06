import re
from dataclasses import dataclass
from enum import StrEnum

from aerona.domain.enums.entity import EntityType

DEFAULT_DIRECTION = "the subject in its setting"
AMBIENCE_BIOME_COUNT = 5

IMAGE_DIRECTION: dict[EntityType, str] = {
    EntityType.LANGUAGE: "an object that shows this language: a carved tablet, manuscript page, inscription or glyph-covered artifact",
    EntityType.KNOWLEDGE: "people practicing this technique or knowledge, with its tools, materials and workplace",
    EntityType.TRADITION: "the ritual or festival being performed by the community",
    EntityType.LEGEND: "a painterly-yet-photoreal scene illustrating the legend",
    EntityType.NATURAL_LAW: "a cosmic visual metaphor of this natural law at work in the world",
    EntityType.PROPHECY: "a visionary scene of the prophecy, as a seer would see it",
    EntityType.EVENT: "the event as it happens, documentary style",
    EntityType.CELESTIAL: "the celestial body in the night sky above the landscape",
    EntityType.PEOPLE: "a group portrait of these people in their daily life: clothing, tools, faces, dwellings behind them",
    EntityType.SETTLEMENT: "an establishing shot of the settlement from a nearby rise, people and smoke for life and scale",
    EntityType.MORTAL: "a full-length character portrait in their environment; face, garments, posture that reveal their role",
    EntityType.ARMY: "the army on the march or arrayed for battle, banners and equipment, dust and weather",
    EntityType.TRADE_ROUTE: "the route seen from along its way: caravans, boats or porters with their loads, waystations and the land it crosses",
    EntityType.STRUCTURE: "the monument or work in its setting, with people for scale",
    EntityType.ITEM: "a museum-grade still life of the object on a surface that fits its origin, raking light",
    EntityType.RESOURCE: "the resource where it is found or harvested, with the workers or creatures who gather it",
    EntityType.SPIRIT: "a translucent presence half-visible in a real place, long exposure, uncanny but restrained",
    EntityType.REGION: "a sweeping landscape of the region, atmospheric perspective, characteristic weather",
    EntityType.PLACE: "the place itself in its surroundings, characteristic light and weather",
    EntityType.SPECIES: "the creature in its habitat, wildlife photography",
    EntityType.VESSEL: "the vehicle or conveyance in use, with its crew or riders",
    EntityType.OUTER_BEING: "an Outer Being: NEVER show it fully, only a fragment, a silhouette, a reflection, or its effect on the world",
    EntityType.CULT: "the cult gathered at its rite: robed members, sacred objects, the place of worship, faces lit by its particular light",
    EntityType.FACTION: "members of the faction in their meeting place, their insignia, colors and tools of their trade, a sense of hierarchy",
    EntityType.ARTWORK: "the artwork itself (song performed, statue, fresco, book) in the place it is kept or performed, with its audience or keeper",
    EntityType.LAW: "the law being proclaimed or carved: a stele, scroll or assembly, the people who live under it watching",
}

VESSEL_DIRECTIONS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"\b(gate|portal|passage)", re.IGNORECASE),
        "a gate or portal between worlds: the frame, the impossible view through it, travelers dwarfed before it",
    ),
    (
        re.compile(r"\b(ship|vessel|boat|raft)", re.IGNORECASE),
        "a ship between worlds: hull, sails or engines, crew on deck, the void or alien sky around it",
    ),
    (
        re.compile(r"\b(mount|wing|dragon|horse)", re.IGNORECASE),
        "a mount carrying its rider across the sky or between worlds, motion and scale",
    ),
    (re.compile(r"\bbridge", re.IGNORECASE), "a bridge spanning the gap between worlds, travelers crossing, vertiginous depth"),
)

MEGAFAUNA_DIRECTION = "a colossal megafauna in its habitat with tiny human figures for scale; wildlife photography from a distance"

OUTER_BEING_TAIL = ", shown only partially: a fragment glimpsed through fog, glare or a reflection, its full shape never visible."
OUTER_BEING_WORDS = re.compile(
    r"\b(partial|partially|fragment|silhouette|glimpse|glimpsed|obscured|hidden|reflection|never (fully )?(seen|visible|shown))\b", re.IGNORECASE
)
SCALE_TAIL = ", with tiny human figures for scale."
SCALE_WORDS = re.compile(r"\b(scale|tiny (human )?figures?|dwarf(ed|s|ing)?|colossal|towering over)\b", re.IGNORECASE)


class CosmosSubjectKind(StrEnum):
    WORLD = "world"
    STAR = "star"
    FOREIGN_GOD = "foreign_god"
    SON = "son"
    CREATOR = "creator"


COSMOS_DIRECTION: dict[CosmosSubjectKind, str] = {
    CosmosSubjectKind.WORLD: "the whole world seen from orbit or high above its sky, its unique physics visible (rings, seas, ice, glow), then a hint of its surface",
    CosmosSubjectKind.STAR: "the star itself in deep space with its planets as small discs nearby, astrophotography, its color and character exaggerated just enough",
    CosmosSubjectKind.FOREIGN_GOD: "a foreign god as its worshippers imagine it: a monumental idol or vision in its home world, never a cartoon",
    CosmosSubjectKind.SON: "a divine child of the creator, a god in full figure as their worshippers see them, their two domains shaping their body, garb and the light around them, of the age, form and gender their description gives, never a cartoon",
    CosmosSubjectKind.CREATOR: "the creator, a primordial god at the scale of the cosmos they shaped, a full-figure vision among stars and newborn worlds, in the form their description gives, never a cartoon",
}


@dataclass(frozen=True)
class ImageSubjectTraits:
    entity_type: EntityType
    name: str
    subtype: str | None
    megafauna: bool


def image_direction(traits: ImageSubjectTraits) -> str:
    if traits.entity_type is EntityType.VESSEL:
        probe = f"{traits.subtype or ''} {traits.name}"
        for pattern, direction in VESSEL_DIRECTIONS:
            if pattern.search(probe):
                return direction
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
