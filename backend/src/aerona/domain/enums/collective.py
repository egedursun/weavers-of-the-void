from enum import StrEnum


class CollectiveActKind(StrEnum):
    RIOT = "riot"
    PANIC = "panic"
    LYNCHING = "lynching"
    CONVERSION = "conversion"
    REVOLT = "revolt"
    STRIKE = "strike"
    PROCESSION = "procession"
    REVIVAL = "revival"


class CollectiveTrigger(StrEnum):
    PRICE_SPIKE = "price_spike"
    EXECUTION = "execution"
    SERMON = "sermon"
    OMEN = "omen"
    RUMOUR = "rumour"
    FIRE = "fire"
    PLAGUE = "plague"
    BEAST = "beast"
    ECLIPSE = "eclipse"
    MIRACLE = "miracle"
    FAMINE = "famine"
    UNPAID_WAGES = "unpaid_wages"


class CascadeOutcome(StrEnum):
    FIZZLED = "fizzled"
    MOB = "mob"
    PANIC = "panic"
    MOVEMENT = "movement"


class MobTarget(StrEnum):
    DISTRICT = "district"
    GRANARY = "granary"
    SCAPEGOAT = "scapegoat"
    GATE = "gate"
    TEMPLE = "temple"
    PALACE = "palace"
    WORKSHOP = "workshop"


class MobStatus(StrEnum):
    GATHERING = "gathering"
    RAMPAGING = "rampaging"
    DISPERSED = "dispersed"


class MobEnd(StrEnum):
    FATIGUE = "fatigue"
    FORCE = "force"
    CONCESSION = "concession"


class AccountKind(StrEnum):
    OFFICIAL_CHRONICLE = "official_chronicle"
    FOLK_MEMORY = "folk_memory"
    FOREIGN_ACCOUNT = "foreign_account"
    GOSPEL = "gospel"
    EPIC = "epic"
    INSCRIPTION = "inscription"
    FOUNDING_MYTH = "founding_myth"


class AccountStance(StrEnum):
    GLORIFY = "glorify"
    VILIFY = "vilify"
    OMIT = "omit"
    NEUTRAL = "neutral"


class AccountMedium(StrEnum):
    ARTWORK = "artwork"
    BOOK = "book"
    ORAL = "oral"
    INSCRIPTION = "inscription"


class StoryletId(StrEnum):
    LOST_HEIR = "lost_heir"
    HOARDED_STORE = "hoarded_store"
    BEAST_DEMAND = "beast_demand"
    FORBIDDEN_TEXT = "forbidden_text"
    DEFILED_SITE = "defiled_site"
    WEDDING_CHALLENGE = "wedding_challenge"
    DYING_RULER = "dying_ruler"
    INSULTED_ENVOY = "insulted_envoy"


class StoryletRole(StrEnum):
    RULER = "ruler"
    CLAIMANT = "claimant"
    REALM = "realm"
    TOWN = "town"
    BEAST = "beast"
    SCHOLAR = "scholar"
    TEXT = "text"
    CULT = "cult"
    SITE = "site"
    CHALLENGER = "challenger"
    CHALLENGED = "challenged"
    ELDER_HEIR = "elder_heir"
    YOUNGER_HEIR = "younger_heir"
    ENVOY = "envoy"
    HOST_REALM = "host_realm"


class StoryletEffect(StrEnum):
    UNREST = "unrest"
    ORDER = "order"
    LEGITIMACY = "legitimacy"
    COIN = "coin"
    FOOD = "food"
    RENOWN = "renown"
    INFAMY = "infamy"
    FRIENDSHIP = "friendship"
    WAR = "war"
    DUEL = "duel"
    HEIR = "heir"
    CLAIM = "claim"
    WOUND = "wound"
    PIETY = "piety"
    DESTROY = "destroy"
    ANGER = "anger"


class StoryletStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"
    EXPIRED = "expired"


class NormSituation(StrEnum):
    FUNERAL = "funeral"
    FEAST = "feast"
    WEDDING = "wedding"
    COURT = "court"
    TEMPLE = "temple"
    MARKET = "market"
    BATTLE = "battle"
    DUEL = "duel"
    HOSPITALITY = "hospitality"
    MOURNING = "mourning"
    SACRED_DAY = "sacred_day"
    STRANGER = "stranger"
    SUPERIOR = "superior"


class NormBehaviour(StrEnum):
    JEST = "jest"
    BOAST = "boast"
    INSULT = "insult"
    FLATTERY = "flattery"
    FLIRTING = "flirting"
    GIFTS = "gifts"
    QUARRELS = "quarrels"
    BLOWS = "blows"
    WEAPONS_CARRIED = "weapons_carried"
    FINE_DRESS = "fine_dress"
    PLAIN_SPEECH = "plain_speech"
    FORBIDDEN_FOOD = "forbidden_food"
    SECRETS = "secrets"


class SocialBias(StrEnum):
    PRESTIGE = "prestige"
    CONFORMITY = "conformity"
    CONTENT = "content"


class FormativeKind(StrEnum):
    GREAT_WAR = "great_war"
    VICTORY = "victory"
    DEFEAT = "defeat"
    PLAGUE = "plague"
    FAMINE = "famine"
    GOLDEN_AGE = "golden_age"
    CONQUEST = "conquest"


class RoleKind(StrEnum):
    OFFICE = "office"
    PROFESSION = "profession"
    COMBAT = "combat"
    PRIESTHOOD = "priesthood"
    INHERITANCE = "inheritance"


class RoleEligibility(StrEnum):
    ANY = "any"
    FEMALE_ONLY = "female_only"
    MALE_ONLY = "male_only"
    FEMALE_PREFERRED = "female_preferred"
    MALE_PREFERRED = "male_preferred"


class DatingSystemKind(StrEnum):
    REGNAL = "regnal"
    FOUNDING = "founding"
    RELIGIOUS = "religious"
    CELESTIAL_CYCLE = "celestial_cycle"


class Tincture(StrEnum):
    GOLD = "gold"
    SILVER = "silver"
    RED = "red"
    BLUE = "blue"
    GREEN = "green"
    BLACK = "black"
    PURPLE = "purple"
    ORANGE = "orange"


class HeraldicDivision(StrEnum):
    PLAIN = "plain"
    PER_PALE = "per_pale"
    PER_FESS = "per_fess"
    PER_BEND = "per_bend"
    QUARTERLY = "quarterly"
    CHEVRON = "chevron"
    BORDURE = "bordure"


class HeraldicCharge(StrEnum):
    NONE = "none"
    BEAST = "beast"
    BIRD = "bird"
    TREE = "tree"
    TOWER = "tower"
    SWORD = "sword"
    CROWN = "crown"
    STAR = "star"
    SUN = "sun"
    MOON = "moon"
    EYE = "eye"
    HAND = "hand"
    WHEEL = "wheel"
    WAVE = "wave"
    FLAME = "flame"
    KEY = "key"


class HeraldryHolderKind(StrEnum):
    HOUSE = "house"
    POLITY = "polity"
    TITLE = "title"
    ARMY = "army"
    GUILD = "guild"


class DesignKind(StrEnum):
    VESSEL = "vessel"
    SKYSHIP = "skyship"
    SIEGE_ENGINE = "siege_engine"


class DesignComponentKind(StrEnum):
    HULL = "hull"
    PROPULSION = "propulsion"
    HOLD = "hold"
    QUARTERS = "quarters"
    ARMOUR = "armour"
    WEAPON = "weapon"
    WARD = "ward"
    NAVIGATION = "navigation"
    FRAME = "frame"
    COUNTERWEIGHT = "counterweight"
