from typing import Annotated, Literal

from pydantic import Field

from aerona.domain.models.base import ValueObject

Percent = Annotated[int, Field(ge=0, le=100)]
Count = Annotated[int, Field(ge=0)]


class RegionStats(ValueObject):
    kind: Literal["region"] = "region"
    breadth: Percent | None = None
    danger: Percent | None = None
    fertility: Percent | None = None
    magic: Percent | None = None


class PlaceStats(ValueObject):
    kind: Literal["place"] = "place"
    danger: Percent | None = None
    fertility: Percent | None = None
    mystery: Percent | None = None


class ResourceStats(ValueObject):
    kind: Literal["resource"] = "resource"
    abundance: Percent | None = None
    value: Percent | None = None
    might: Percent | None = None


class SettlementStats(ValueObject):
    kind: Literal["settlement"] = "settlement"
    population: Count | None = None
    prosperity: Percent | None = None
    defense: Percent | None = None
    piety: Percent | None = None
    wealth: Percent | None = None


class SpeciesStats(ValueObject):
    kind: Literal["species"] = "species"
    hp: Count | None = None
    strength: Percent | None = None
    agility: Percent | None = None
    intelligence: Percent | None = None
    danger: Percent | None = None
    might: Percent | None = None
    abundance: Percent | None = None


class PeopleStats(ValueObject):
    kind: Literal["people"] = "people"
    population: Count | None = None
    martiality: Percent | None = None
    magic: Percent | None = None
    craft: Percent | None = None
    piety: Percent | None = None
    prosperity: Percent | None = None
    wealth: Percent | None = None


class MortalStats(ValueObject):
    kind: Literal["mortal"] = "mortal"
    hp: Count | None = None
    strength: Percent | None = None
    agility: Percent | None = None
    intellect: Percent | None = None
    charisma: Percent | None = None
    endurance: Percent | None = None
    willpower: Percent | None = None
    perception: Percent | None = None
    wisdom: Percent | None = None
    creativity: Percent | None = None
    beauty: Percent | None = None
    age: Count | None = None
    lifespan: Count | None = None
    death_year: int | None = None
    sex: Literal["female", "male", "other"] | None = None


class ItemStats(ValueObject):
    kind: Literal["item"] = "item"
    damage: Percent | None = None
    protection: Percent | None = None
    might: Percent | None = None
    curse: Percent | None = None


class StructureStats(ValueObject):
    kind: Literal["structure"] = "structure"
    splendor: Percent | None = None
    durability: Percent | None = None
    function: Percent | None = None


class LanguageStats(ValueObject):
    kind: Literal["language"] = "language"
    spread: Percent | None = None
    complexity: Percent | None = None
    sacredness: Percent | None = None


class LegendStats(ValueObject):
    kind: Literal["legend"] = "legend"
    spread: Percent | None = None


class TraditionStats(ValueObject):
    kind: Literal["tradition"] = "tradition"
    spread: Percent | None = None
    rigidity: Percent | None = None


class CultStats(ValueObject):
    kind: Literal["cult"] = "cult"
    followers: Count | None = None
    zeal: Percent | None = None
    influence: Percent | None = None
    devotion: Count | None = None


class FactionStats(ValueObject):
    kind: Literal["faction"] = "faction"
    strength: Percent | None = None
    wealth: Percent | None = None
    sway: Percent | None = None


class CelestialStats(ValueObject):
    kind: Literal["celestial"] = "celestial"
    brightness: Percent | None = None
    influence: Percent | None = None


class ArtworkStats(ValueObject):
    kind: Literal["artwork"] = "artwork"
    renown: Percent | None = None
    influence: Percent | None = None


class LawStats(ValueObject):
    kind: Literal["law"] = "law"
    rigidity: Percent | None = None
    justice: Percent | None = None


class SpiritStats(ValueObject):
    kind: Literal["spirit"] = "spirit"
    strength: Percent | None = None
    unrest: Percent | None = None


class KnowledgeStats(ValueObject):
    kind: Literal["knowledge"] = "knowledge"
    level: Annotated[int, Field(ge=1, le=10)] | None = None
    spread: Percent | None = None


class ProphecyStats(ValueObject):
    kind: Literal["prophecy"] = "prophecy"
    certainty: Percent | None = None


class EventStats(ValueObject):
    kind: Literal["event"] = "event"
    severity: Percent | None = None


class VesselStats(ValueObject):
    kind: Literal["vessel"] = "vessel"
    speed: Percent | None = None
    range: Percent | None = None
    crew: Count | None = None
    armor: Percent | None = None
    strangeness: Percent | None = None


class OuterBeingStats(ValueObject):
    kind: Literal["outer_being"] = "outer_being"
    size: Percent | None = None
    interest: Percent | None = None
    influence: Percent | None = None


class ArmyStats(ValueObject):
    kind: Literal["army"] = "army"
    size: Count | None = None
    morale: Percent | None = None
    equipment: Percent | None = None
    experience: Percent | None = None


class NaturalLawStats(ValueObject):
    kind: Literal["natural_law"] = "natural_law"


class TradeRouteStats(ValueObject):
    kind: Literal["trade_route"] = "trade_route"
    capacity: Count | None = None
    danger: Percent | None = None
    renown: Percent | None = None
    culture: Percent | None = None


class DiseaseStats(ValueObject):
    kind: Literal["disease"] = "disease"
    virulence: Percent | None = None
    lethality: Percent | None = None
    infected: Count | None = None
    dead: Count | None = None


class PolityStats(ValueObject):
    kind: Literal["polity"] = "polity"
    legitimacy: Percent | None = None
    stability: Percent | None = None
    subjects: Count | None = None
    territory: Count | None = None


class HouseStats(ValueObject):
    kind: Literal["house"] = "house"
    prestige: Percent | None = None
    members: Count | None = None
    wealth: Percent | None = None


class TreatyStats(ValueObject):
    kind: Literal["treaty"] = "treaty"
    parties: Count | None = None
    trust: Percent | None = None


class IdeologyStats(ValueObject):
    kind: Literal["ideology"] = "ideology"
    adherents: Count | None = None
    appeal: Percent | None = None


class BeastStats(ValueObject):
    kind: Literal["beast"] = "beast"
    hp: Count | None = None
    danger: Percent | None = None
    strength: Percent | None = None
    agility: Percent | None = None
    cunning: Percent | None = None
    renown: Percent | None = None
    terror: Percent | None = None


class RiteStats(ValueObject):
    kind: Literal["rite"] = "rite"
    power: Annotated[int, Field(ge=1, le=10)] | None = None
    castings: Count | None = None


EntityStats = Annotated[
    RegionStats
    | PlaceStats
    | ResourceStats
    | SettlementStats
    | SpeciesStats
    | PeopleStats
    | MortalStats
    | ItemStats
    | StructureStats
    | LanguageStats
    | LegendStats
    | TraditionStats
    | CultStats
    | FactionStats
    | CelestialStats
    | ArtworkStats
    | LawStats
    | SpiritStats
    | KnowledgeStats
    | ProphecyStats
    | EventStats
    | VesselStats
    | OuterBeingStats
    | ArmyStats
    | TradeRouteStats
    | DiseaseStats
    | PolityStats
    | HouseStats
    | TreatyStats
    | IdeologyStats
    | RiteStats
    | BeastStats
    | NaturalLawStats,
    Field(discriminator="kind"),
]
