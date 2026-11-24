from aerona.domain.enums.prehistory import PrehistoryKind
from aerona.domain.enums.world import WorldType

SIMULATED_KINDS = frozenset({PrehistoryKind.FULL, PrehistoryKind.LIVING, PrehistoryKind.CORPSE, PrehistoryKind.RUINED})
SPECIAL_KINDS: dict[WorldType, PrehistoryKind] = {
    WorldType.LIVING: PrehistoryKind.LIVING,
    WorldType.DEAD: PrehistoryKind.SOULS,
    WorldType.DREAM: PrehistoryKind.DREAMT,
    WorldType.MIRROR: PrehistoryKind.MIRRORED,
    WorldType.GODS_PALACE: PrehistoryKind.PALACE,
    WorldType.GENERATION_SHIP: PrehistoryKind.VOYAGE,
    WorldType.VOID_POCKET: PrehistoryKind.PHENOMENON,
    WorldType.CORPSE_WORLD: PrehistoryKind.CORPSE,
    WorldType.MEGASTRUCTURE: PrehistoryKind.RUINED,
}
WORLD_PREHISTORY: dict[WorldType, PrehistoryKind] = {world_type: SPECIAL_KINDS.get(world_type, PrehistoryKind.FULL) for world_type in WorldType}
PREHISTORY_PHASES = frozenset(
    {
        "environment_survey",
        "planetary_climate",
        "long_seasons",
        "natural_disasters",
        "disaster_casualties",
        "ecology",
        "trait_evolution",
        "fossils",
        "structural_demography",
        "demography_depth",
        "death_engine",
        "mortal_aging",
        "famine_migration",
        "nomadism",
        "creature_migration",
        "people_cycles",
        "people_customs",
        "sound_changes",
        "dialect_divergence",
        "language_cycles",
        "language_death",
        "language_contact",
        "settlement_life",
        "settlement_cycles",
        "civilization",
        "ruins",
        "polity_cycles",
        "titles",
        "diplomacy",
        "campaigns",
        "war_upkeep",
        "war_casualties",
        "religion_spread",
        "faith_cycles",
        "native_faith",
        "knowledge_diffusion",
        "knowledge_levels",
        "legend_cycles",
        "historiography",
    }
)
PREHISTORY_GROWTH = frozenset({"population_baseline", "population_growth", "cohort_upkeep"})
COARSE_PHASES = frozenset({"diplomacy", "campaigns", "war_upkeep", "war_casualties", "knowledge_diffusion", "historiography", "legend_cycles"})
