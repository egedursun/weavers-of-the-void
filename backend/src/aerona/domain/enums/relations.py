from enum import StrEnum


class RelationType(StrEnum):
    ACQUAINTANCE = "acquaintance"
    FRIEND = "friend"
    CLOSE_FRIEND = "close_friend"
    BEST_FRIEND = "best_friend"
    CONFIDANT = "confidant"
    CRUSH = "crush"
    LOVER = "lover"
    EX_LOVER = "ex_lover"
    SPOUSE = "spouse"
    RIVAL = "rival"
    NEMESIS = "nemesis"
    ENEMY = "enemy"
    MENTOR = "mentor"
    PROTEGE = "protege"
    COMRADE_IN_ARMS = "comrade_in_arms"
    DRINKING_COMPANION = "drinking_companion"
    PATRON = "patron"
    CLIENT = "client"
    BETROTHED = "betrothed"
    SWORN_KIN = "sworn_kin"
    FOSTER = "foster"
    NEIGHBOUR = "neighbour"
    GUEST_FRIEND = "guest_friend"
    ESTRANGED = "estranged"


class InteractionKind(StrEnum):
    CONVERSE = "converse"
    BEFRIEND = "befriend"
    GOSSIP = "gossip"
    JOKE = "joke"
    COMFORT = "comfort"
    FLATTER = "flatter"
    BOAST = "boast"
    INSULT = "insult"
    ARGUE = "argue"
    FLIRT = "flirt"
    COURT = "court"
    PROPOSE = "propose"
    SEDUCE = "seduce"
    QUARREL = "quarrel"
    RECONCILE = "reconcile"
    TEACH = "teach"
    GIFT = "gift"
    ASK_FAVOUR = "ask_favour"
    CONFIDE_SECRET = "confide_secret"
    THREATEN = "threaten"
    BRAWL = "brawl"
    APOLOGISE = "apologise"
    SHARE_MEAL = "share_meal"
    ASK_COUNSEL = "ask_counsel"
    PRAISE = "praise"
    WARN = "warn"
    PLEAD = "plead"
    SHARE_NEWS = "share_news"


class CircleKind(StrEnum):
    DRINKING_CIRCLE = "drinking_circle"
    POETS_CIRCLE = "poets_circle"
    HUNTING_CIRCLE = "hunting_circle"
    SECRET_SOCIETY = "secret_society"
    STUDY_CIRCLE = "study_circle"
    PRAYER_CIRCLE = "prayer_circle"
    MUSIC_CIRCLE = "music_circle"
    CRAFT_CIRCLE = "craft_circle"
    SPORT_CLUB = "sport_club"
    GAMING_CIRCLE = "gaming_circle"
    READING_CIRCLE = "reading_circle"
    MUTUAL_AID = "mutual_aid"


class PassionKind(StrEnum):
    LOVE = "love"
    LOYALTY = "loyalty"
    HATRED = "hatred"
    DEVOTION = "devotion"
    AMBITION = "ambition"
    ENVY = "envy"
    GRIEF = "grief"
    CURIOSITY = "curiosity"
    FEAR = "fear"
    SHAME = "shame"
    PRIDE = "pride"
    JEALOUSY = "jealousy"
    ADMIRATION = "admiration"
    OBSESSION = "obsession"
    VENGEANCE = "vengeance"
    COMPASSION = "compassion"


class PassionSource(StrEnum):
    RELATIONSHIP = "relationship"
    OATH = "oath"
    MEMORY = "memory"
    UPBRINGING = "upbringing"
    DIVINE = "divine"


class AppealKind(StrEnum):
    BELIEF = "belief"
    SELF_INTEREST = "self_interest"
    AUTHORITY = "authority"
    EVIDENCE = "evidence"
    FEAR = "fear"
    FEELING = "feeling"
    BOND = "bond"
    TRADITION = "tradition"


class PersuasionAim(StrEnum):
    BELIEF = "belief"
    DECISION = "decision"
    FAITH = "faith"
    VOTE = "vote"
    TREATY = "treaty"
    SURRENDER = "surrender"
    CONFESSION = "confession"
    ALLIANCE = "alliance"
    RELEASE = "release"


class GroupKind(StrEnum):
    HOUSEHOLD = "household"
    COURT = "court"
    CIRCLE = "circle"
    WARBAND = "warband"
    CREW = "crew"
    CELL = "cell"
    BAND = "band"
    TEAM = "team"
    CONGREGATION = "congregation"
    SCHOOL = "school"


class ContestKind(StrEnum):
    RIDDLE_GAME = "riddle_game"
    INSULT_CONTEST = "insult_contest"
    DEBATE = "debate"
    GAME_OF_SKILL = "game_of_skill"
    TRIAL_OF_WISDOM = "trial_of_wisdom"
    SONG_CONTEST = "song_contest"
    STORYTELLING = "storytelling"
    RACE = "race"
    CRAFT_CONTEST = "craft_contest"
    WRESTLING = "wrestling"
    HUNT = "hunt"


class ContestStake(StrEnum):
    HONOUR = "honour"
    UNION = "union"
    WAGER = "wager"
    OFFICE = "office"
    CAPTIVE = "captive"
    DIVINE_FAVOUR = "divine_favour"
    LAND = "land"
    FREEDOM = "freedom"
    KNOWLEDGE = "knowledge"
    TITLE = "title"
    RIGHTS = "rights"


class ContestEnd(StrEnum):
    CHALLENGER = "challenger"
    DEFENDER = "defender"
    DRAWN = "drawn"
