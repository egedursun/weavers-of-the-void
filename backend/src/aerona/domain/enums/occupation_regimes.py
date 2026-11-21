from enum import StrEnum


class OccupationRule(StrEnum):
    MILITARY = "military"
    CIVIL_BY_OCCUPIER = "civil_by_occupier"
    LOCAL_PUPPET = "local_puppet"
    ANNEXATION = "annexation"
    PROTECTORATE = "protectorate"


class CollaborationKind(StrEnum):
    ADMINISTRATION = "administration"
    POLICE = "police"
    INFORMING = "informing"
    TRADE = "trade"
    MILITIA = "militia"
    PROPAGANDA = "propaganda"


class CollaborationFate(StrEnum):
    SERVING = "serving"
    KILLED = "killed"
    ENDED = "ended"


class OccupationMeasure(StrEnum):
    CURFEW = "curfew"
    HOSTAGES = "hostages"
    COLLECTIVE_PUNISHMENT = "collective_punishment"
    DEPORTATION = "deportation"
    REQUISITION = "requisition"
    BAN_ON_GATHERING = "ban_on_gathering"
    AMNESTY_OFFER = "amnesty_offer"


class OccupationEnding(StrEnum):
    LIBERATED = "liberated"
    ANNEXED = "annexed"
    WITHDRAWN = "withdrawn"
