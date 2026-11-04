from enum import StrEnum

from aerona.engine.context import TickContext

LEDGER_PREFIX = "ledger"


class LedgerKey(StrEnum):
    TOTAL_FAITH = "total_faith"
    STOLEN_ESSENCE = "stolen_essence"
    POPULATION_START = "population_start"
    POPULATION_PREVIOUS = "population_previous"
    POPULATION_BEFORE_GROWTH = "population_before_growth"
    POPULATION_GROWTH = "population_growth"
    POPULATION_TO_CULTS = "population_to_cults"
    DOOM_CLOCK = "doom_clock"
    GODLESS = "godless"
    CULT_ESSENCE = "cult_essence"


class DoomItem(StrEnum):
    GODLESS = "godless communities"
    CURSED = "cursed"
    RESTLESS_SPIRITS = "restless spirits"
    WARS = "wars"
    REBEL_SONS = "rebel sons"
    MIRACLES = "miracles"
    FAITH = "faith"
    PEACE = "age of peace"
    WONDERS = "wonders"
    TEMPLES = "temples"
    GOLDEN_AGE = "golden age"
    WORLD_AGE = "age turning and world age"
    CREATOR_CULT = "creator's cult"
    ENLIGHTENMENT = "spread of learning"
    SPEED = "apocalypse speed (world rules)"
    RESET = "post-apocalypse reset"


class EssenceItem(StrEnum):
    REGEN = "creator's own regeneration"
    FAITH = "sons' faith"
    HALVED = "income shrunk above the cap"
    OVERFLOW = "overflowing essence"
    TO_SONS = "overflow to the poorest sons"
    STOLEN = "stolen by rebel sons"
    GNAWED = "gnawed by the godless"
    CULT = "creator's cult"


def _key(prefix: str, name: str) -> str:
    return f"{LEDGER_PREFIX}.{prefix}.{name}"


def record(ctx: TickContext, key: LedgerKey, amount: int) -> None:
    ctx.environment.stats.count(_key("value", key.value), amount)


def read(ctx: TickContext, key: LedgerKey) -> int:
    return ctx.environment.stats.counters.get(_key("value", key.value), 0)


def has(ctx: TickContext, key: LedgerKey) -> bool:
    return _key("value", key.value) in ctx.environment.stats.counters


def record_doom(ctx: TickContext, item: DoomItem, amount: int) -> None:
    ctx.environment.stats.count(_key("doom", item.value), amount)


def doom_items(ctx: TickContext) -> dict[DoomItem, int]:
    return {item: ctx.environment.stats.counters.get(_key("doom", item.value), 0) for item in DoomItem}


def record_essence(ctx: TickContext, item: EssenceItem, amount: int) -> None:
    ctx.environment.stats.count(_key("essence", item.value), amount)


def essence_items(ctx: TickContext) -> dict[EssenceItem, int]:
    return {item: ctx.environment.stats.counters.get(_key("essence", item.value), 0) for item in EssenceItem}
