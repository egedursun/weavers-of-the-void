from enum import StrEnum


class ScenarioKey(StrEnum):
    DOOM_FAR = "doom_far"
    ONE_FAITH = "one_faith"
    LOST_STAR = "lost_star"
    MANY_WORLDS = "many_worlds"
    LONG_PEACE = "long_peace"
    COSMIC_POWER = "cosmic_power"
    LOYAL_PANTHEON = "loyal_pantheon"
    NEW_HORIZONS = "new_horizons"


class ScenarioStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"


class AchievementKey(StrEnum):
    SECOND_SKY = "second_sky"
    CONSTELLATION = "constellation"
    PROPHECY_FULFILLED = "prophecy_fulfilled"
    RETURN_FROM_DEATH = "return_from_death"
    FATHERS_HAND = "fathers_hand"
    BABEL = "babel"
    CROWDED_WORLD = "crowded_world"
    FIRST_PRAYER = "first_prayer"
    CREATORS_CULT = "creators_cult"
    INTERSTELLAR_TRAVELLER = "interstellar_traveller"
    SAGA_COMPLETED = "saga_completed"
    GOD_OF_EPOCHS = "god_of_epochs"
    ANCIENT = "ancient"
    CROWDED_PANTHEON = "crowded_pantheon"
    FIRST_EXPLORERS = "first_explorers"
    SENSED_WORLD = "sensed_world"
    WEAPONS_SILENT = "weapons_silent"


class ScoreComponent(StrEnum):
    POPULATION = "population"
    DIVERSITY = "diversity"
    LANGUAGES = "languages"
    WORLDS = "worlds"
    CIVILIZATION = "civilization"
    DOOMSDAY = "doomsday"
    ACHIEVEMENTS = "achievements"
    SCENARIOS = "scenarios"


class LedgerOperation(StrEnum):
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"


class ImageMime(StrEnum):
    PNG = "image/png"
    JPEG = "image/jpeg"
    WEBP = "image/webp"


class ImageOrigin(StrEnum):
    GENERATED = "generated"
    UPLOADED = "uploaded"
