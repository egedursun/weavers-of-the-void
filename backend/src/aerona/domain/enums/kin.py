from enum import StrEnum


class KinRole(StrEnum):
    PARENT = "parent"
    CHILD = "child"
    SIBLING = "sibling"
    GRANDPARENT = "grandparent"
    GRANDCHILD = "grandchild"
    PARENT_SIBLING_FIRST_LINE = "parent_sibling_first_line"
    PARENT_SIBLING_SECOND_LINE = "parent_sibling_second_line"
    SIBLING_CHILD = "sibling_child"
    COUSIN_PARALLEL = "cousin_parallel"
    COUSIN_CROSS = "cousin_cross"
    PARENT_IN_LAW = "parent_in_law"
    CHILD_IN_LAW = "child_in_law"
    SIBLING_IN_LAW = "sibling_in_law"
    CO_SPOUSE = "co_spouse"
    CHOSEN_KIN = "chosen_kin"
    GODPARENT = "godparent"
    SWORN_KIN = "sworn_kin"
    FOSTER_KIN = "foster_kin"
    STEP_PARENT = "step_parent"
    STEP_CHILD = "step_child"
    HALF_SIBLING = "half_sibling"


class KinDuty(StrEnum):
    SUPPORT = "support"
    RAISE = "raise"
    TEACH = "teach"
    PROTECT = "protect"
    AVENGE = "avenge"
    MARRY_TO = "marry_to"
    INHERIT_FROM = "inherit_from"
    MOURN = "mourn"
    HOST = "host"
    OBEY = "obey"
    JOKE_WITH = "joke_with"
    AVOID = "avoid"


class KinGroupForm(StrEnum):
    LINEAGE = "lineage"
    CLAN = "clan"
    PHRATRY = "phratry"
    MOIETY = "moiety"
    KINDRED = "kindred"
    RAMAGE = "ramage"
    HOUSE = "house"
    LOCALIZED_GROUP = "localized_group"
    AGE_LINKED_GROUP = "age_linked_group"


class KinMembership(StrEnum):
    DESCENT = "descent"
    RESIDENCE = "residence"
    CHOICE = "choice"


class KinNeed(StrEnum):
    FOOD = "food"
    COIN = "coin"
    CARE = "care"
    SHELTER = "shelter"
    PROTECTION = "protection"


class KinAgenda(StrEnum):
    CHOOSE_HEAD = "choose_head"
    SHARE_LAND = "share_land"
    FEUD = "feud"
    MARRIAGE = "marriage"
    MIGRATE = "migrate"
