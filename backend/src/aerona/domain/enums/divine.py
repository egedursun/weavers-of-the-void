from enum import StrEnum


class DomainHook(StrEnum):
    NAVAL_MIGHT = "naval_might"
    SEA_CALM = "sea_calm"
    CATCH = "catch"
    FIRE_CURSE = "fire_curse"
    LEVY_MORALE = "levy_morale"
    DUEL_WOUNDS = "duel_wounds"
    SOUL_HOLD = "soul_hold"
    DEATH_TOLL = "death_toll"
    PLAGUE_TITHE = "plague_tithe"
    IMMUNITY = "immunity"
    HARVEST_FLOOR = "harvest_floor"
    OATH_TITHE = "oath_tithe"
    MEMORY_KEEPING = "memory_keeping"
    BORDER_GUARD = "border_guard"
    PRESERVATION = "preservation"
    STARGAZING = "stargazing"
    FASTING = "fasting"
    SIEGE_STARVING = "siege_starving"
    RUMOUR_TWIST = "rumour_twist"
    SPY_DEPTH = "spy_depth"
    ROAD_SAFETY = "road_safety"
    BLOOD_RITE = "blood_rite"
    BLOODLINE = "bloodline"
    RELIC_POWER = "relic_power"
    AGING = "aging"
    PROPHECY = "prophecy"
    TRADE_GAIN = "trade_gain"
    CRAFT_SKILL = "craft_skill"
    LEARNING = "learning"
    KINDLING_LOVE = "kindling_love"
    HUNT_YIELD = "hunt_yield"
    FERTILITY = "fertility"
    HEALING = "healing"
    DREAM_SENDING = "dream_sending"
    STONEWORK = "stonework"
    SANITY_WARD = "sanity_ward"
    FRENZY = "frenzy"
    COLD_ENDURANCE = "cold_endurance"
    REST = "rest"
    LEGEND_SPREAD = "legend_spread"


class DomainActivity(StrEnum):
    BATTLES = "battles"
    DEATHS = "deaths"
    BIRTHS = "births"
    VOYAGES = "voyages"
    TRADE = "trade"
    SICKNESS = "sickness"
    OATHS = "oaths"
    LEGENDS = "legends"
    WORKS = "works"
    DISCOVERIES = "discoveries"
    MARRIAGES = "marriages"
    HUNTS = "hunts"
    SCHEMES = "schemes"
    RITES = "rites"
    DREAMS = "dreams"
    HUNGER = "hunger"
    MADNESS = "madness"
    JOURNEYS = "journeys"
    HARVESTS = "harvests"
    BUILDING = "building"


class GodGoalKind(StrEnum):
    BE_WORSHIPPED = "be_worshipped"
    FOUND_REALM = "found_realm"
    DESTROY_RIVAL = "destroy_rival"
    SPREAD_DOMAIN = "spread_domain"
    WIN_WAR = "win_war"
    ACQUIRE_RELIC = "acquire_relic"
    RAISE_HERO = "raise_hero"
    AWAKEN_GOD = "awaken_god"
    DEFEAT_FOREIGN_GOD = "defeat_foreign_god"
    RECONCILE = "reconcile"
    REBEL = "rebel"


class GoalState(StrEnum):
    ACTIVE = "active"
    DONE = "done"
    FAILED = "failed"
    DROPPED = "dropped"


class GoalSource(StrEnum):
    ENGINE = "engine"
    AGENT = "agent"
    CREATOR = "creator"


class DivineWoundKind(StrEnum):
    SEVERED_DOMAIN = "severed_domain"
    SHATTERED_MANIFESTATION = "shattered_manifestation"
    STOLEN_NAME = "stolen_name"
    VOID_WOUND = "void_wound"


class WoundCause(StrEnum):
    DUEL = "duel"
    GOD_WAR = "god_war"
    CREATOR = "creator"
    AVATAR_SLAIN = "avatar_slain"
    OUTER_BARGAIN = "outer_bargain"


class CouncilMotion(StrEnum):
    NONE = "none"
    AGAINST_DOOMSDAY = "against_doomsday"
    JOINT_BLESSING = "joint_blessing"
    CONDEMN_REBEL = "condemn_rebel"
    CALL_FOR_PEACE = "call_for_peace"
    WAR_ON_FOREIGN_GOD = "war_on_foreign_god"
    DIVIDE_WORLDS = "divide_worlds"
    OUTLAW_RITE = "outlaw_rite"
    PUNISH_SON = "punish_son"
    BLESS_HERO = "bless_hero"
    HOLY_WORLD = "holy_world"
    COSMIC_TRUCE = "cosmic_truce"
    PETITION_CREATOR = "petition_creator"


class SonPunishment(StrEnum):
    CHAIN = "chain"
    EXILE = "exile"
    STRIP_POWER = "strip_power"


class LawScope(StrEnum):
    COSMOS = "cosmos"
    WORLD = "world"
    REGION = "region"


class LawException(StrEnum):
    NONE = "none"
    CREATOR_CHOSEN = "creator_chosen"
    AUTHOR_WORSHIPPERS = "author_worshippers"
    HEROES = "heroes"
    AVATARS = "avatars"


class OuterHunger(StrEnum):
    SOULS = "souls"
    KNOWLEDGE = "knowledge"
    LIGHT = "light"
    NAMES = "names"
    MEMORIES = "memories"


class BargainGain(StrEnum):
    ESSENCE = "essence"
    POWER = "power"
    MIGHT = "might"


class BargainPrice(StrEnum):
    WORLD_SANITY = "world_sanity"
    DOMAIN = "domain"
    TRUE_NAME = "true_name"
