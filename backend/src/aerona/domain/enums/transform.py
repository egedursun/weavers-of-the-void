from enum import StrEnum


class TransformKind(StrEnum):
    DEIFICATION = "deification"
    MANTLING = "mantling"
    SPIRIT_RISING = "spirit_rising"
    REINCARNATION = "reincarnation"
    POSSESSION = "possession"
    LOCAL_GOD = "local_god"
    BEAST_CURSE = "beast_curse"
    CURSE_LIFTED = "curse_lifted"
    UPLIFT = "uplift"
    CITY_STATE = "city_state"
    SECESSION = "secession"
    THEOCRACY = "theocracy"
    TITLE_RAISED = "title_raised"
    REALM_FROM_TITLE = "realm_from_title"
    MANIFESTATION = "manifestation"
    LEGEND_FIXED = "legend_fixed"
    ARTWORK_REMEMBERED = "artwork_remembered"
    EVENT_PHENOMENON = "event_phenomenon"
    DEAD_GOD = "dead_god"
    CONSTRUCT = "construct"
    BEAST_PROMOTION = "beast_promotion"
    LANGUAGE_DEATH = "language_death"
    LANGUAGE_REVIVAL = "language_revival"
    THEORY_SETTLED = "theory_settled"
    TRADITION_CODIFIED = "tradition_codified"
    FALL = "fall"
    RESTORATION = "restoration"
    LOSS_OF_SAPIENCE = "loss_of_sapience"
    ETHNORELIGIOUS = "ethnoreligious"
    NATION_BUILDING = "nation_building"
    HOUSE_PEOPLE = "house_people"
    POCKET_WORLD = "pocket_world"
    WORLD_SOUL = "world_soul"
    STAR_GOD = "star_god"
    SACRALISATION = "sacralisation"
    SECULARISATION = "secularisation"
    PROGENITOR = "progenitor"
    OUTER_ENTRY = "outer_entry"
    CORRUPTION = "corruption"
    COLOSSAL_CORPSE = "colossal_corpse"


class TransformEnd(StrEnum):
    SON = "son"
    MORTAL = "mortal"
    SPIRIT = "spirit"
    GOD = "god"
    BEAST = "beast"
    SPECIES = "species"
    PEOPLE = "people"
    CULT = "cult"
    POLITY = "polity"
    HOUSE = "house"
    SETTLEMENT = "settlement"
    FACTION = "faction"
    TITLE = "title"
    LEGEND = "legend"
    CREATION = "creation"
    ARTWORK = "artwork"
    EVENT = "event"
    PHENOMENON = "phenomenon"
    WORLD = "world"
    STAR = "star"
    IDEOLOGY = "ideology"
    OUTER_BEING = "outer_being"
    PLACE = "place"
    MADE_THING = "made_thing"
    LANGUAGE = "language"
    KNOWLEDGE = "knowledge"
    THEORY = "theory"
    TRADITION = "tradition"
    LAW = "law"


class TransformState(StrEnum):
    DONE = "done"
    REVERTED = "reverted"


class TransformTrigger(StrEnum):
    ENGINE = "engine"
    FORCED = "forced"
    CREATOR = "creator"
    COUNCIL = "council"
    FADING = "fading"
    SON = "son"
    CURSE = "curse"
    VOID = "void"
    DARK_AGE = "dark_age"
    PUNISHMENT = "punishment"
    BACKFILL = "backfill"


class ProspectStance(StrEnum):
    OPEN = "open"
    BLOCKED = "blocked"
    FORCED = "forced"


class GodDeathMode(StrEnum):
    IN_COSMOS = "in_cosmos"
    LEFT_COSMOS = "left_cosmos"


class StarModifierSource(StrEnum):
    GOD_DEATH = "god_death"
    DIVINE_ACT = "divine_act"
