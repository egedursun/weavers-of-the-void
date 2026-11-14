from enum import StrEnum


class InstructionBinding(StrEnum):
    NONE = "none"
    ORDER = "order"
    OATH = "oath"
    GEAS = "geas"
    SEAL = "seal"
    OWNERSHIP = "ownership"
    LEASE = "lease"
    SYMBIOSIS = "symbiosis"


class CommandToken(StrEnum):
    NONE = "none"
    ITEM = "item"
    WORD = "word"
    BLOODLINE = "bloodline"
    OFFICE = "office"
    NETWORK_KEY = "network_key"


class OrderKind(StrEnum):
    GUARD = "guard"
    SERVE = "serve"
    OBEY_HOLDER = "obey_holder"
    BUILD = "build"
    GATHER = "gather"
    PROTECT = "protect"
    DESTROY = "destroy"
    REPORT = "report"
    MAINTAIN = "maintain"
    REPLICATE = "replicate"
    HOLD_STILL = "hold_still"
    FOLLOW = "follow"
    FORBID = "forbid"


class OrderCondition(StrEnum):
    ALWAYS = "always"
    WHILE_MAKER_LIVES = "while_maker_lives"
    UNTIL_DATE = "until_date"
    WHEN_ATTACKED = "when_attacked"
    WHEN_TOKEN_SHOWN = "when_token_shown"


class MindWill(StrEnum):
    NONE = "none"
    INSTRUCTED = "instructed"
    EMERGENT = "emergent"
    FULL = "full"
    EXCEEDING = "exceeding"


class ContractStatus(StrEnum):
    POSTED = "posted"
    TAKEN = "taken"
    SLAIN = "slain"
    FAILED = "failed"
    WITHDRAWN = "withdrawn"
