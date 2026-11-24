from enum import StrEnum


class IntrigueSecret(StrEnum):
    AFFAIR = "affair"
    ILLEGITIMATE_CHILD = "illegitimate_child"
    MURDER = "murder"
    HERESY = "heresy"
    SECRET_CULT_MEMBERSHIP = "secret_cult_membership"
    DEBT = "debt"
    CRIME = "crime"
    COWARDICE_IN_BATTLE = "cowardice_in_battle"
    HIDDEN_CONDITION = "hidden_condition"
    FALSE_IDENTITY = "false_identity"
    DEAL_WITH_OUTER_BEING = "deal_with_outer_being"
    TRUE_PARENTAGE = "true_parentage"
    BROKEN_OATH = "broken_oath"
    ECOSABOTAGE = "ecosabotage"
    BROKEN_CIPHER = "broken_cipher"
    TRUE_HISTORY = "true_history"
    HIDDEN_POWER = "hidden_power"
    FORGERY = "forgery"
    ILLNESS = "illness"


class HookStrength(StrEnum):
    WEAK = "weak"
    STRONG = "strong"


class HookSource(StrEnum):
    SECRET = "secret"
    DEBT = "debt"
    FAVOUR = "favour"
    HOSTAGE = "hostage"
    TRUE_NAME = "true_name"
    DEPENDENCE = "dependence"
    AFFECTION = "affection"


class HookDemand(StrEnum):
    MARRIAGE = "marriage"
    STEP_DOWN = "step_down"
    SUPPORT = "support"
    VOTE = "vote"
    LAW = "law"
    APPOINTMENT = "appointment"
    SILENCE = "silence"
    PAYMENT = "payment"
    RELEASE = "release"
    INFORMATION = "information"


class FavourOrigin(StrEnum):
    GIFT = "gift"
    RESCUE = "rescue"
    WAR_SUPPORT = "war_support"
    SUCCESSION_SUPPORT = "succession_support"
    SCHEME_AID = "scheme_aid"
    VOTE = "vote"
    RELIEF = "relief"
    HOSPITALITY = "hospitality"
    RANSOM = "ransom"
    HEALING = "healing"
    TEACHING = "teaching"


class IdentityReason(StrEnum):
    SPY = "spy"
    BLOOD_CURSE = "blood_curse"
    EXILE = "exile"
    IMPOSTOR = "impostor"
    HIDDEN_POWER = "hidden_power"
    FUGITIVE = "fugitive"
    HIDDEN_FAITH = "hidden_faith"
    PASSING_KIND = "passing_kind"
    PROTECTION = "protection"


class PlotKind(StrEnum):
    MURDER = "murder"
    ABDUCT = "abduct"
    SEDUCE = "seduce"
    SWAY = "sway"
    FABRICATE_CLAIM = "fabricate_claim"
    FABRICATE_HOOK = "fabricate_hook"
    STEAL_RELIC = "steal_relic"
    COUP = "coup"
    POISON_WELL = "poison_well"
    FRAME = "frame"
    ELOPE = "elope"
    CONVERT_SECRETLY = "convert_secretly"
    SABOTAGE_WEDDING = "sabotage_wedding"
    FREE_PRISONER = "free_prisoner"
    ECOSABOTAGE = "ecosabotage"
    LEARN_TRUE_NAME = "learn_true_name"
    FORGE_LETTER = "forge_letter"
    GEAS_TRAP = "geas_trap"
    HIDE_FLEET = "hide_fleet"
    FORGE_WORK = "forge_work"
    FIX_CONTEST = "fix_contest"
    INCITE_CROWD = "incite_crowd"


class SchemePhase(StrEnum):
    RECRUIT = "recruit"
    PREPARE = "prepare"
    EXECUTE = "execute"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    EXPOSED = "exposed"
    ABANDONED = "abandoned"


class BeliefSource(StrEnum):
    OBSERVATION = "observation"
    MESSAGE = "message"
    RUMOUR = "rumour"
    SPY = "spy"
    SCOUT = "scout"
    RECORDS = "records"
    DECEPTION = "deception"
    NETWORK = "network"
    FORESIGHT = "foresight"
    MIND_READING = "mind_reading"
    INTRUSION = "intrusion"
    SURVEILLANCE = "surveillance"
    MADE_MIND_REPORT = "made_mind_report"
    DREAM = "dream"
    OMEN = "omen"


class TrueNameCause(StrEnum):
    REBIRTH = "a_costly_rebirth_of_its_manifestation"
    INITIATION = "an_initiation"
    GOD_WORD = "a_god's_word"
    NAME_FORM = "a_name_given_by_custom"
