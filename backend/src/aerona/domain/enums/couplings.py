from enum import StrEnum


class RiteComponent(StrEnum):
    SPOKEN = "spoken"
    GESTURED = "gestured"
    INSCRIBED = "inscribed"
    SUNG = "sung"
    DANCED = "danced"
    MATERIAL = "material"
    MENTAL = "mental"
    OFFERED = "offered"
    COMMUNAL = "communal"


class RestraintKind(StrEnum):
    GAG = "gag"
    BOUND_HANDS = "bound_hands"
    BLINDFOLD = "blindfold"


class SociolectKind(StrEnum):
    CLASS = "class"
    CASTE = "caste"
    GUILD = "guild"
    COURT = "court"
    CANT = "cant"
    SAILORS = "sailors"
    YOUTH = "youth"
    SOLDIERS = "soldiers"
    CLERGY = "clergy"
    SCHOLARS = "scholars"


class SignCause(StrEnum):
    DEAFNESS = "deafness"
    SILENCE_VOW = "silence_vow"
    HUNTING_SILENCE = "hunting_silence"
    MUTILATION = "mutilation"
    TRADE = "trade"
    NOISE = "noise"


class TeachingState(StrEnum):
    TAUGHT = "taught"
    BLOCKED = "blocked"
    SOLD = "sold"


class FieldAgreementKind(StrEnum):
    PARLEY = "parley"
    TRUCE = "truce"
    SURRENDER = "surrender"
    EXCHANGE = "exchange"
    SAFE_CONDUCT = "safe_conduct"
    FRATERNISATION = "fraternisation"
    BURIAL_TRUCE = "burial_truce"


class FieldAgreementState(StrEnum):
    KEPT = "kept"
    ENDED = "ended"
    BROKEN = "broken"
    REPUDIATED = "repudiated"


class SealKind(StrEnum):
    STRUCTURE = "structure"
    RITE = "rite"
    DIVINE = "divine"
    POWER = "power"
    LIVING = "living"
    PACT = "pact"
    MADE = "made"


class SealLink(StrEnum):
    OATH = "oath"
    POWER = "power"
    LINE = "line"
    MIND = "mind"


class CarrionRest(StrEnum):
    ROTTING = "rotting"
    MUMMIFIED = "mummified"
    FROZEN = "frozen"
    DRIFTING = "drifting"
    FLOATING = "floating"
    BURIED = "buried"
    BURNED = "burned"
    SUNK = "sunk"
    SCAVENGED = "scavenged"
