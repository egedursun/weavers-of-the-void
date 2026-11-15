from dataclasses import dataclass

from aerona.core.grammar import several
from aerona.domain.enums.meta import GoalCategory, GoalMetric, ScoreComponent


@dataclass(frozen=True)
class MetricSpec:
    metric: GoalMetric
    category: GoalCategory
    label: str
    singular: str
    plural: str
    lower_is_better: bool = False

    def count(self, value: int) -> str:
        return several(value, self.singular, self.plural)


C = GoalCategory
M = GoalMetric

METRICS: dict[GoalMetric, MetricSpec] = {
    spec.metric: spec
    for spec in (
        MetricSpec(M.WORLDS, C.COSMOS, "Worlds in the cosmos", "world", "worlds"),
        MetricSpec(M.INHABITED_WORLDS, C.COSMOS, "Worlds with a living people", "inhabited world", "inhabited worlds"),
        MetricSpec(M.MOONS, C.COSMOS, "Moons", "moon", "moons"),
        MetricSpec(M.STARS, C.COSMOS, "Stars", "star", "stars"),
        MetricSpec(M.REBORN_STARS, C.COSMOS, "Reborn stars", "reborn star", "reborn stars"),
        MetricSpec(M.DEAD_STARS, C.COSMOS, "Dead stars", "dead star", "dead stars", lower_is_better=True),
        MetricSpec(M.GALAXIES, C.SCALES, "Galaxies", "galaxy", "galaxies"),
        MetricSpec(M.CLUSTERS, C.SCALES, "Galaxy clusters", "galaxy cluster", "galaxy clusters"),
        MetricSpec(M.DIMENSIONS, C.SCALES, "Dimensions", "dimension", "dimensions"),
        MetricSpec(M.OPEN_RIFTS, C.SCALES, "Open rifts", "open rift", "open rifts"),
        MetricSpec(M.COSMIC_BEINGS, C.SCALES, "Cosmic beings", "cosmic being", "cosmic beings"),
        MetricSpec(M.FAR_VOYAGES, C.SCALES, "Voyages arrived beyond a galaxy", "voyage beyond a galaxy", "voyages beyond a galaxy"),
        MetricSpec(M.FAR_TRADE_ROUTES, C.SCALES, "Busy trade routes beyond a galaxy", "busy route beyond a galaxy", "busy routes beyond a galaxy"),
        MetricSpec(M.SPECIES, C.LIFE, "Species", "species", "species"),
        MetricSpec(M.BEASTS, C.LIFE, "Beasts", "beast", "beasts"),
        MetricSpec(M.SPIRITS, C.LIFE, "Spirits", "spirit", "spirits"),
        MetricSpec(M.AWAKENED_SPECIES, C.LIFE, "Species that became peoples", "awakened species", "awakened species"),
        MetricSpec(M.PEOPLES, C.PEOPLES, "Peoples", "people", "peoples"),
        MetricSpec(M.POPULATION, C.PEOPLES, "Population of the peoples", "soul", "souls"),
        MetricSpec(M.SETTLEMENTS, C.PEOPLES, "Settlements", "settlement", "settlements"),
        MetricSpec(M.POLITIES, C.PEOPLES, "Realms", "realm", "realms"),
        MetricSpec(M.EMPIRES, C.PEOPLES, "Empires", "empire", "empires"),
        MetricSpec(M.GOLDEN_AGES, C.PEOPLES, "Communities in a golden age", "community", "communities"),
        MetricSpec(M.HIGHEST_CIV_TIER, C.PEOPLES, "Highest civilization stage", "stage", "stages"),
        MetricSpec(M.TREATIES, C.PEOPLES, "Treaties", "treaty", "treaties"),
        MetricSpec(M.TRADE_ROUTES, C.PEOPLES, "Trade routes", "trade route", "trade routes"),
        MetricSpec(M.LANGUAGES, C.PEOPLES, "Languages", "language", "languages"),
        MetricSpec(M.CULTS, C.FAITH, "Cults", "cult", "cults"),
        MetricSpec(M.CREATOR_WORSHIPPERS, C.FAITH, "Communities worshipping the Creator", "community", "communities"),
        MetricSpec(M.PRAYERS_TO_CREATOR, C.FAITH, "Prayers to the Creator", "prayer", "prayers"),
        MetricSpec(M.FULFILLED_PROPHECIES, C.FAITH, "Fulfilled prophecies", "fulfilled prophecy", "fulfilled prophecies"),
        MetricSpec(M.LARGEST_FAITH, C.FAITH, "Peoples sharing the widest faith", "people", "peoples"),
        MetricSpec(M.ASCENDED_MORTALS, C.FAITH, "Ascended mortals", "ascended mortal", "ascended mortals"),
        MetricSpec(M.LIVING_SONS, C.PANTHEON, "Living sons", "son", "sons"),
        MetricSpec(M.HIGHEST_SON_LEVEL, C.PANTHEON, "Highest son level", "level", "levels"),
        MetricSpec(M.RESURRECTIONS, C.PANTHEON, "Resurrections", "resurrection", "resurrections"),
        MetricSpec(M.SUPPRESSED_REBELLIONS, C.PANTHEON, "Suppressed rebellions", "suppressed rebellion", "suppressed rebellions"),
        MetricSpec(M.FOREIGN_GODS, C.PANTHEON, "Foreign gods", "foreign god", "foreign gods"),
        MetricSpec(M.KNOWLEDGE, C.CULTURE, "Knowledge", "knowledge", "knowledge"),
        MetricSpec(M.THEORIES, C.CULTURE, "Theories", "theory", "theories"),
        MetricSpec(M.ARTWORKS, C.CULTURE, "Artworks", "artwork", "artworks"),
        MetricSpec(M.ART_FORMS, C.CULTURE, "Art forms", "art form", "art forms"),
        MetricSpec(M.LEGENDS, C.CULTURE, "Legends", "legend", "legends"),
        MetricSpec(M.TRADITIONS, C.CULTURE, "Traditions", "tradition", "traditions"),
        MetricSpec(M.LAWS, C.CULTURE, "Laws", "law", "laws"),
        MetricSpec(M.WONDERS, C.CULTURE, "Wonders", "wonder", "wonders"),
        MetricSpec(M.MUSEUMS, C.CULTURE, "Museum collections", "museum collection", "museum collections"),
        MetricSpec(M.COMPLETED_SAGAS, C.CULTURE, "Completed legendary quests", "completed legendary quest", "completed legendary quests"),
        MetricSpec(M.HEROQUESTS_WON, C.CULTURE, "Won heroquests", "won heroquest", "won heroquests"),
        MetricSpec(M.ARRIVED_JOURNEYS, C.DISCOVERY, "Journeys arrived at another world", "arrived journey", "arrived journeys"),
        MetricSpec(M.DISCOVERIES, C.DISCOVERY, "Lands found by mortals", "discovery", "discoveries"),
        MetricSpec(M.SENSED_WORLDS, C.DISCOVERY, "Sensed worlds born", "sensed world", "sensed worlds"),
        MetricSpec(M.VESSELS, C.DISCOVERY, "Vessels", "vessel", "vessels"),
        MetricSpec(M.ONGOING_WARS, C.ORDER, "Ongoing wars", "war", "wars", lower_is_better=True),
        MetricSpec(M.WARLESS_PEOPLES, C.ORDER, "Peoples in a cosmos without war", "people", "peoples"),
        MetricSpec(M.EPOCH, C.TIME, "Epochs behind the cosmos", "epoch", "epochs"),
        MetricSpec(M.DOOM_PERCENT, C.TIME, "Doomsday clock (% of the threshold)", "percent", "percent", lower_is_better=True),
        MetricSpec(M.CREATOR_DEEDS, C.CREATOR, "Deeds of the Creator", "deed", "deeds"),
        MetricSpec(M.LEVERS_USED, C.CREATOR, "Kinds of deed done by the Creator", "kind of deed", "kinds of deed"),
        MetricSpec(M.MIRACLES, C.CREATOR, "Miracles of the Creator", "miracle", "miracles"),
    )
}

CATEGORY_LABELS: dict[GoalCategory, str] = {
    C.COSMOS: "Cosmos",
    C.SCALES: "Scales of the cosmos",
    C.LIFE: "Life",
    C.PEOPLES: "Peoples",
    C.FAITH: "Faith",
    C.PANTHEON: "Pantheon",
    C.CULTURE: "Learning and the arts",
    C.DISCOVERY: "Discovery",
    C.ORDER: "Order",
    C.TIME: "Time",
    C.CREATOR: "The Creator's hand",
}

SCORE_PART_LABELS: dict[ScoreComponent, str] = {
    ScoreComponent.POPULATION: "Population",
    ScoreComponent.DIVERSITY: "Diversity of records",
    ScoreComponent.LANGUAGES: "Languages",
    ScoreComponent.WORLDS: "Worlds",
    ScoreComponent.CIVILIZATION: "Civilization",
    ScoreComponent.LIFE: "Life",
    ScoreComponent.FAITH: "Faith",
    ScoreComponent.CULTURE: "Culture",
    ScoreComponent.KNOWLEDGE: "Knowledge",
    ScoreComponent.WONDERS: "Wonders",
    ScoreComponent.SCALES: "Scales of the cosmos",
    ScoreComponent.EXPLORATION: "Exploration",
    ScoreComponent.DOOMSDAY: "Doomsday",
    ScoreComponent.ACHIEVEMENTS: "Achievements",
    ScoreComponent.SCENARIOS: "Goals",
}
