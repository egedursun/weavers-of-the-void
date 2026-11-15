from collections.abc import Callable
from dataclasses import dataclass

from aerona.catalog.goal_metrics import METRICS
from aerona.constants.units import PERCENT
from aerona.core.grammar import agree
from aerona.domain.enums.meta import AchievementKey, GoalCategory, GoalMetric
from aerona.rules.registry import Rules

ROMAN = {1: "I", 2: "II", 3: "III"}
TIER_PREFIXES = {1: "tier_1_", 2: "tier_2_", 3: "tier_3_"}
POINTS_PREFIX = "points_"


@dataclass(frozen=True)
class AchievementSpec:
    key: AchievementKey
    metric: GoalMetric
    title: str
    describe: Callable[[int], str]

    @property
    def category(self) -> GoalCategory:
        return METRICS[self.metric].category

    def name(self, tier: int) -> str:
        return self.title if tier <= 1 else f"{self.title} {ROMAN[tier]}"

    def threshold(self, rules: Rules, tier: int) -> int:
        return int(getattr(rules.achievements, f"{TIER_PREFIXES[tier]}{self.key.value}"))

    def description(self, rules: Rules, tier: int) -> str:
        return self.describe(self.threshold(rules, tier))

    def points(self, rules: Rules, tier: int) -> int:
        base = int(getattr(rules.achievements, f"{POINTS_PREFIX}{self.key.value}"))
        share = {1: PERCENT, 2: rules.achievements.tier_2_points_pct, 3: rules.achievements.tier_3_points_pct}[tier]
        return round(base * share / PERCENT)


A = AchievementKey
M = GoalMetric

ACHIEVEMENTS: dict[AchievementKey, AchievementSpec] = {
    spec.key: spec
    for spec in (
        AchievementSpec(A.SECOND_SKY, M.WORLDS, "Many skies", lambda n: f"{METRICS[M.WORLDS].count(n)} in the cosmos."),
        AchievementSpec(A.CONSTELLATION, M.STARS, "Constellation", lambda n: f"A cosmos of {METRICS[M.STARS].count(n)}."),
        AchievementSpec(A.PEOPLED_SKIES, M.INHABITED_WORLDS, "Peopled skies", lambda n: f"Peoples live on {METRICS[M.INHABITED_WORLDS].count(n)}."),
        AchievementSpec(
            A.MOONS_IN_ORBIT, M.MOONS, "Moons in orbit", lambda n: f"{METRICS[M.MOONS].count(n)} {agree(n, 'circles its', 'circle their')} planet."
        ),
        AchievementSpec(
            A.REKINDLED_STAR, M.REBORN_STARS, "Rekindled star", lambda n: f"{METRICS[M.REBORN_STARS].count(n)} {agree(n, 'burns', 'burn')} again after dying."
        ),
        AchievementSpec(A.MANY_GALAXIES, M.GALAXIES, "Many galaxies", lambda n: f"{METRICS[M.GALAXIES].count(n)} in the cosmos."),
        AchievementSpec(
            A.GALAXY_CLUSTERS, M.CLUSTERS, "Galaxy clusters", lambda n: f"{METRICS[M.CLUSTERS].count(n)} {agree(n, 'gathers', 'gather')} the galaxies."
        ),
        AchievementSpec(
            A.MANY_DIMENSIONS, M.DIMENSIONS, "Many dimensions", lambda n: f"{METRICS[M.DIMENSIONS].count(n)} {agree(n, 'lies', 'lie')} side by side."
        ),
        AchievementSpec(
            A.RIFTS_OPENED, M.OPEN_RIFTS, "Rifts opened", lambda n: f"{METRICS[M.OPEN_RIFTS].count(n)} {agree(n, 'stands', 'stand')} between dimensions."
        ),
        AchievementSpec(
            A.COSMIC_BEINGS, M.COSMIC_BEINGS, "Cosmic beings", lambda n: f"{METRICS[M.COSMIC_BEINGS].count(n)} {agree(n, 'moves', 'move')} through the cosmos."
        ),
        AchievementSpec(A.ACROSS_THE_GALAXIES, M.FAR_VOYAGES, "Across the galaxies", lambda n: f"{METRICS[M.FAR_VOYAGES].count(n)} arrived."),
        AchievementSpec(
            A.TRADE_BETWEEN_GALAXIES,
            M.FAR_TRADE_ROUTES,
            "Trade between galaxies",
            lambda n: f"{METRICS[M.FAR_TRADE_ROUTES].count(n)} {agree(n, 'carries', 'carry')} goods.",
        ),
        AchievementSpec(
            A.MANY_KINDS_OF_LIFE, M.SPECIES, "Many kinds of life", lambda n: f"{METRICS[M.SPECIES].count(n)} {agree(n, 'lives', 'live')} in the cosmos."
        ),
        AchievementSpec(
            A.BEASTS_OF_THE_WILD, M.BEASTS, "Beasts of the wild", lambda n: f"{METRICS[M.BEASTS].count(n)} {agree(n, 'roams', 'roam')} the worlds."
        ),
        AchievementSpec(A.SPIRITS_ABROAD, M.SPIRITS, "Spirits abroad", lambda n: f"{METRICS[M.SPIRITS].count(n)} {agree(n, 'dwells', 'dwell')} in the worlds."),
        AchievementSpec(
            A.SPECIES_AWAKENED, M.AWAKENED_SPECIES, "A species awakened", lambda n: f"{METRICS[M.AWAKENED_SPECIES].count(n)} rose to become a people."
        ),
        AchievementSpec(A.MANY_PEOPLES, M.PEOPLES, "Many peoples", lambda n: f"{METRICS[M.PEOPLES].count(n)} {agree(n, 'lives', 'live')} in the cosmos."),
        AchievementSpec(A.CROWDED_WORLD, M.POPULATION, "Crowded world", lambda n: f"The peoples number {METRICS[M.POPULATION].count(n)}."),
        AchievementSpec(
            A.SETTLED_LANDS, M.SETTLEMENTS, "Settled lands", lambda n: f"{METRICS[M.SETTLEMENTS].count(n)} {agree(n, 'stands', 'stand')} in the worlds."
        ),
        AchievementSpec(A.REALMS_RISE, M.POLITIES, "Realms rise", lambda n: f"{METRICS[M.POLITIES].count(n)} {agree(n, 'governs its', 'govern their')} lands."),
        AchievementSpec(A.EMPIRE, M.EMPIRES, "Empire", lambda n: f"{METRICS[M.EMPIRES].count(n)} {agree(n, 'rules', 'rule')} over other peoples."),
        AchievementSpec(A.GOLDEN_AGE, M.GOLDEN_AGES, "Golden age", lambda n: f"{METRICS[M.GOLDEN_AGES].count(n)} in a golden age at once."),
        AchievementSpec(A.HEIGHT_OF_CIVILIZATION, M.HIGHEST_CIV_TIER, "Height of civilization", lambda n: f"A community reached civilization stage {n}."),
        AchievementSpec(A.TREATIES_SIGNED, M.TREATIES, "Treaties signed", lambda n: f"{METRICS[M.TREATIES].count(n)} {agree(n, 'binds', 'bind')} the realms."),
        AchievementSpec(
            A.TRADE_ROUTES, M.TRADE_ROUTES, "Trade routes", lambda n: f"{METRICS[M.TRADE_ROUTES].count(n)} {agree(n, 'links', 'link')} the communities."
        ),
        AchievementSpec(A.BABEL, M.LANGUAGES, "Babel", lambda n: f"{METRICS[M.LANGUAGES].count(n)} {agree(n, 'is', 'are')} spoken."),
        AchievementSpec(A.FIRST_PRAYER, M.PRAYERS_TO_CREATOR, "Someone called you", lambda n: f"Prayers made to you directly: {n}."),
        AchievementSpec(
            A.CREATORS_CULT,
            M.CREATOR_WORSHIPPERS,
            "The Creator's cult",
            lambda n: f"{METRICS[M.CREATOR_WORSHIPPERS].count(n)} {agree(n, 'worships', 'worship')} you directly.",
        ),
        AchievementSpec(A.PROPHECY_FULFILLED, M.FULFILLED_PROPHECIES, "The word came true", lambda n: f"{METRICS[M.FULFILLED_PROPHECIES].count(n)} came true."),
        AchievementSpec(A.MANY_FAITHS, M.CULTS, "Many faiths", lambda n: f"{METRICS[M.CULTS].count(n)} {agree(n, 'gathers', 'gather')} the faithful."),
        AchievementSpec(
            A.ONE_GOD_MANY_PEOPLES,
            M.LARGEST_FAITH,
            "One god, many peoples",
            lambda n: f"{METRICS[M.LARGEST_FAITH].count(n)} {agree(n, 'worships', 'worship')} the same god.",
        ),
        AchievementSpec(
            A.MORTAL_MADE_DIVINE,
            M.ASCENDED_MORTALS,
            "A mortal made divine",
            lambda n: f"{METRICS[M.ASCENDED_MORTALS].count(n)} walked a god's path to its end.",
        ),
        AchievementSpec(
            A.CROWDED_PANTHEON, M.LIVING_SONS, "Crowded pantheon", lambda n: f"{METRICS[M.LIVING_SONS].count(n)} {agree(n, 'lives', 'live')} at once."
        ),
        AchievementSpec(A.MIGHTY_SON, M.HIGHEST_SON_LEVEL, "A mighty son", lambda n: f"A son reached level {n}."),
        AchievementSpec(A.RETURN_FROM_DEATH, M.RESURRECTIONS, "Return from death", lambda n: f"Dead sons resurrected: {n}."),
        AchievementSpec(A.CREATORS_HAND, M.SUPPRESSED_REBELLIONS, "The Creator's hand", lambda n: f"Rebellions suppressed by your hand: {n}."),
        AchievementSpec(
            A.OTHER_GODS,
            M.FOREIGN_GODS,
            "Other gods",
            lambda n: f"{METRICS[M.FOREIGN_GODS].count(n)} {agree(n, 'shares', 'share')} the cosmos with your pantheon.",
        ),
        AchievementSpec(A.STORE_OF_KNOWLEDGE, M.KNOWLEDGE, "A store of knowledge", lambda n: f"Records of knowledge: {n}."),
        AchievementSpec(A.THEORIES, M.THEORIES, "Theories", lambda n: f"{METRICS[M.THEORIES].count(n)} {agree(n, 'explains', 'explain')} the world."),
        AchievementSpec(A.WORKS_OF_ART, M.ARTWORKS, "Works of art", lambda n: f"{METRICS[M.ARTWORKS].count(n)} made by mortals."),
        AchievementSpec(A.ARTS, M.ART_FORMS, "The arts", lambda n: f"{METRICS[M.ART_FORMS].count(n)} {agree(n, 'is', 'are')} practised."),
        AchievementSpec(A.LEGENDS, M.LEGENDS, "Legends", lambda n: f"{METRICS[M.LEGENDS].count(n)} {agree(n, 'is', 'are')} told."),
        AchievementSpec(A.TRADITIONS, M.TRADITIONS, "Traditions", lambda n: f"{METRICS[M.TRADITIONS].count(n)} {agree(n, 'is', 'are')} kept."),
        AchievementSpec(A.RULE_OF_LAW, M.LAWS, "Rule of law", lambda n: f"{METRICS[M.LAWS].count(n)} in force."),
        AchievementSpec(A.WONDERS, M.WONDERS, "Wonders", lambda n: f"{METRICS[M.WONDERS].count(n)} raised."),
        AchievementSpec(A.COLLECTIONS, M.MUSEUMS, "Collections", lambda n: f"{METRICS[M.MUSEUMS].count(n)} {agree(n, 'is', 'are')} kept."),
        AchievementSpec(A.SAGA_COMPLETED, M.COMPLETED_SAGAS, "Saga completed", lambda n: f"{METRICS[M.COMPLETED_SAGAS].count(n)} ended successfully."),
        AchievementSpec(A.HEROES_RETURNED, M.HEROQUESTS_WON, "Heroes returned", lambda n: f"{METRICS[M.HEROQUESTS_WON].count(n)} by mortal heroes."),
        AchievementSpec(A.INTERSTELLAR_TRAVELLER, M.ARRIVED_JOURNEYS, "Interstellar traveller", lambda n: f"Journeys that reached another world: {n}."),
        AchievementSpec(A.FIRST_EXPLORERS, M.DISCOVERIES, "First explorers", lambda n: f"Lands found by mortals beyond the map: {n}."),
        AchievementSpec(A.SENSED_WORLD, M.SENSED_WORLDS, "Sensed world", lambda n: f"Worlds sensed by mortals that came to light: {n}."),
        AchievementSpec(A.VESSELS, M.VESSELS, "Vessels", lambda n: f"{METRICS[M.VESSELS].count(n)} built."),
        AchievementSpec(
            A.WEAPONS_SILENT, M.WARLESS_PEOPLES, "The weapons fell silent", lambda n: f"No war is fought while {METRICS[M.WARLESS_PEOPLES].count(n)} live."
        ),
        AchievementSpec(A.GOD_OF_EPOCHS, M.EPOCH, "God of epochs", lambda n: f"The cosmos has lived through {METRICS[M.EPOCH].count(n)} under your watch."),
        AchievementSpec(A.ANCIENT, M.EPOCH, "Ancient", lambda n: f"{METRICS[M.EPOCH].count(n)} {agree(n, 'lies', 'lie')} behind the cosmos."),
        AchievementSpec(A.CREATOR_AT_WORK, M.CREATOR_DEEDS, "The Creator at work", lambda n: f"Deeds of your hand: {n}."),
        AchievementSpec(A.MASTER_OF_LEVERS, M.LEVERS_USED, "Master of many deeds", lambda n: f"Kinds of deed done by your hand: {n}."),
        AchievementSpec(A.MIRACLES, M.MIRACLES, "Miracles", lambda n: f"{METRICS[M.MIRACLES].count(n)} worked by your hand."),
    )
}
