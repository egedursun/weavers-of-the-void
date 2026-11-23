from enum import StrEnum


class RiteComponent(StrEnum):
    SPOKEN = "spoken"
    GESTURED = "gestured"
    INSCRIBED = "inscribed"
    SUNG = "sung"
    DANCED = "danced"
    MATERIAL = "material"
    MENTAL = "mental"


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


class SignCause(StrEnum):
    DEAFNESS = "deafness"
    SILENCE_VOW = "silence_vow"
    HUNTING_SILENCE = "hunting_silence"
    MUTILATION = "mutilation"


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


class SealLink(StrEnum):
    OATH = "oath"
    POWER = "power"
    LINE = "line"


class CarrionRest(StrEnum):
    ROTTING = "rotting"
    MUMMIFIED = "mummified"
    FROZEN = "frozen"
    DRIFTING = "drifting"
    FLOATING = "floating"
    BURIED = "buried"
    BURNED = "burned"
    SUNK = "sunk"
