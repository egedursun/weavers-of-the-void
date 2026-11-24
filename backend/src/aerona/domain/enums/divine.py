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
    HOLD_THRONES = "hold_thrones"
    PREVENT_MANTLING = "prevent_mantling"
    SPONSOR_MANTLING = "sponsor_mantling"


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
    DRAINED_ESSENCE = "drained_essence"
    LOST_WORSHIPPERS = "lost_worshippers"
    BOUND = "bound"
    SPLIT_ASPECT = "split_aspect"
    FORGOTTEN_NAME = "forgotten_name"
    DESECRATED_SEAT = "desecrated_seat"
    SPLIT_WORSHIP = "split_worship"


class WoundCause(StrEnum):
    DUEL = "duel"
    GOD_WAR = "god_war"
    CREATOR = "creator"
    AVATAR_SLAIN = "avatar_slain"
    OUTER_BARGAIN = "outer_bargain"
    NEGLECT = "neglect"
    BETRAYAL = "betrayal"
    MORTAL_SLAYER = "mortal_slayer"
    SCHISM = "schism"
    OUTER_BEING = "outer_being"


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
    APPOINT_OFFICE = "appoint_office"
    REASSIGN_WORLD = "reassign_world"
    OUTLAW_POWER = "outlaw_power"
    OUTLAW_SOURCE = "outlaw_source"
    ADMIT_MEMBER = "admit_member"
    EXPEL_MEMBER = "expel_member"
    RECOGNISE_GOD = "recognise_god"
    ESSENCE_TITHE = "essence_tithe"
    SET_COUNCIL_RULES = "set_council_rules"
    REGULATE_MADE_MINDS = "regulate_made_minds"
    REGULATE_POWERS = "regulate_powers"
    REGULATE_LIVING_CRAFT = "regulate_living_craft"
    REGULATE_CURSES = "regulate_curses"
    OPEN_INQUIRY = "open_inquiry"
    AMNESTY = "amnesty"


class VotingRule(StrEnum):
    UNANIMITY = "unanimity"
    MAJORITY = "majority"
    WEIGHTED_BY_STANDING = "weighted_by_standing"
    WEIGHTED_BY_RANK = "weighted_by_rank"


class CouncilSeat(StrEnum):
    BY_RIGHT = "by_right"
    INVITED = "invited"
    BY_PACT = "by_pact"
    RECOGNISED = "recognised"


class EscalationStep(StrEnum):
    CENSURE = "censure"
    SANCTION = "sanction"
    EXCLUSION = "exclusion"
    DUEL = "duel"
    DIVINE_WAR = "divine_war"


class SonPunishment(StrEnum):
    CHAIN = "chain"
    EXILE = "exile"
    STRIP_POWER = "strip_power"
    STRIP_DIVINITY = "strip_divinity"
    PENANCE = "penance"
    ESSENCE_FINE = "essence_fine"
    BOUND_TO_WORLD = "bound_to_world"
    REBUKE = "rebuke"


class PenanceDeed(StrEnum):
    RESTORE_WORLD = "restore_world"
    RAISE_HERO = "raise_hero"
    UNDO_CURSE = "undo_curse"


class LawScope(StrEnum):
    COSMOS = "cosmos"
    DIMENSION = "dimension"
    WORLD = "world"
    REGION = "region"
    STRATUM = "stratum"


class LawException(StrEnum):
    NONE = "none"
    CREATOR_CHOSEN = "creator_chosen"
    AUTHOR_WORSHIPPERS = "author_worshippers"
    HEROES = "heroes"
    AVATARS = "avatars"
    NAMED_KIND = "named_kind"
    OFFICE_HOLDERS = "office_holders"
    BARGAINERS = "bargainers"


class OuterHunger(StrEnum):
    SOULS = "souls"
    KNOWLEDGE = "knowledge"
    LIGHT = "light"
    NAMES = "names"
    MEMORIES = "memories"
    DREAMS = "dreams"
    TIME = "time"


class BargainGain(StrEnum):
    ESSENCE = "essence"
    POWER = "power"
    MIGHT = "might"
    KNOWLEDGE = "knowledge"
    LONGEVITY = "longevity"
    RESTORED_LIFE = "restored_life"
    PROTECTION = "protection"


class BargainPrice(StrEnum):
    WORLD_SANITY = "world_sanity"
    DOMAIN = "domain"
    TRUE_NAME = "true_name"
    WORSHIPPERS = "worshippers"
    DESCENDANTS = "descendants"
    MEMORIES = "memories"
    YEARS = "years"


class DivineVerb(StrEnum):
    GRANT = "grant"
    BLESS = "bless"
    CURSE = "curse"
    CREATE = "create"
    DESTROY = "destroy"
    SHAPE = "shape"
    REVEAL = "reveal"
    CONCEAL = "conceal"
    SUMMON = "summon"
    BIND = "bind"
    FREE = "free"
    HEAL = "heal"
    HARM = "harm"
    RAISE = "raise"
    INSPIRE = "inspire"
    TERRIFY = "terrify"
    PROTECT = "protect"
    GUIDE = "guide"
    JUDGE = "judge"
    TRANSFORM = "transform"
    FORESEE = "foresee"
    HASTEN = "hasten"
    SLOW = "slow"
    MULTIPLY = "multiply"
    STILL = "still"
    WAKE = "wake"
    REMEMBER = "remember"
    ERASE = "erase"


class DivineObject(StrEnum):
    STAT = "stat"
    NEED = "need"
    SKILL = "skill"
    VALUE = "value"
    TRAIT = "trait"
    COMMODITY = "commodity"
    SPECIES = "species"
    LINE = "line"
    STRUCTURE = "structure"
    WEATHER = "weather"
    SOURCE = "source"
    POWER = "power"
    MIND = "mind"
    TRUTH = "truth"
    LAW = "law"
    MEMORY = "memory"
    INCIDENT = "incident"


class DivineScope(StrEnum):
    PERSON = "person"
    COMMUNITY = "community"
    REGION = "region"
    WORLD = "world"
    SYSTEM = "system"
    DIMENSION = "dimension"


class DivineMode(StrEnum):
    PASSIVE = "passive"
    TRIGGERED = "triggered"
    ACTIVE = "active"


class DivineCost(StrEnum):
    ESSENCE = "essence"
    ATTENTION = "attention"
    STANDING = "standing"
    DOMAIN = "domain"
    SACRIFICE = "sacrifice"
