from types import MappingProxyType

from aerona.domain.enums.culture import Technique
from aerona.domain.enums.eras import EraChannel
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.world import TechnologyEra

T = Technique
C = EraChannel
B = KnowledgeBranch
E = TechnologyEra

ERA_EFFECTS: MappingProxyType[Technique, tuple[tuple[EraChannel, str], ...]] = MappingProxyType(
    {
        T.GUNPOWDER: ((C.FIREPOWER, "gunpowder_pct"), (C.MINING, "blasting_pct")),
        T.FIREARMS: ((C.FIREPOWER, "firearms_pct"),),
        T.CANNON: ((C.FIREPOWER, "cannon_pct"),),
        T.STAR_FORTS: ((C.FORTIFICATION, "star_forts_pct"),),
        T.VOLLEY_DRILL: ((C.FIREPOWER, "drill_pct"),),
        T.STEAM_POWER: ((C.INDUSTRY, "steam_pct"), (C.POLLUTION, "steam_pollution_pct")),
        T.COKE_SMELTING: ((C.MINING, "coke_pct"), (C.POLLUTION, "coke_pollution_pct")),
        T.MACHINE_TOOLS: ((C.INDUSTRY, "machine_tools_pct"),),
        T.RAILWAYS: ((C.MARCH, "railway_regions"),),
        T.STEAMSHIPS: ((C.SEA_ROUTES, "steamships_pct"),),
        T.FACTORY_PRODUCTION: ((C.INDUSTRY, "factory_pct"), (C.POLLUTION, "factory_pollution_pct")),
        T.INDUSTRIAL_CHEMISTRY: ((C.FARMING, "fertiliser_pct"), (C.POLLUTION, "chemistry_pollution_pct")),
        T.CANNED_FOOD: ((C.SPOILAGE, "canning_pct"),),
        T.VACCINES: ((C.DISEASE, "vaccines_pct"),),
        T.ELECTRICITY: ((C.INDUSTRY, "electricity_pct"), (C.RITES, "electricity_rite_pct")),
        T.TELEGRAPH: ((C.MESSAGES, "telegraph_hops"),),
        T.TELEPHONE: ((C.MESSAGES, "telephone_hops"),),
        T.ELECTRIC_LIGHT: ((C.RESEARCH, "light_pct"),),
        T.REFRIGERATION: ((C.SPOILAGE, "refrigeration_pct"),),
        T.COMBUSTION_ENGINE: ((C.MARCH, "engine_regions"), (C.POLLUTION, "engine_pollution_pct")),
        T.AVIATION: ((C.MARCH, "aviation_regions"),),
        T.COMPUTATION: ((C.RESEARCH, "computation_pct"), (C.SECULARISATION, "computation_secular_pct")),
        T.RADIO: ((C.OPINION, "radio_pct"), (C.MESSAGES, "radio_hops")),
        T.MASS_MEDIA: ((C.OPINION, "media_pct"), (C.SECULARISATION, "media_secular_pct")),
        T.ANTIBIOTICS: ((C.DISEASE, "antibiotics_pct"),),
        T.GREEN_REVOLUTION: ((C.FARMING, "green_pct"),),
        T.NUCLEAR_POWER: ((C.INDUSTRY, "nuclear_power_pct"), (C.DOOM, "nuclear_power_doom")),
        T.NUCLEAR_WEAPONS: ((C.FIREPOWER, "nuclear_pct"), (C.DOOM, "nuclear_doom")),
        T.ROCKETRY: ((C.WORLD_ROUTES, "rocketry_pct"),),
        T.GENETIC_ENGINEERING: ((C.FARMING, "genetic_farm_pct"), (C.DISEASE, "genetic_disease_pct")),
        T.ARTIFICIAL_MINDS: ((C.RESEARCH, "minds_pct"), (C.DOOM, "minds_doom")),
    }
)
ERA_MARKERS: tuple[tuple[TechnologyEra, Technique], ...] = (
    (E.BRONZE, T.BRONZE),
    (E.IRON, T.IRON),
    (E.MEDIEVAL, T.STEEL),
    (E.GUNPOWDER, T.GUNPOWDER),
    (E.RENAISSANCE, T.PRINTING_PRESS),
    (E.STEAM, T.STEAM_POWER),
    (E.ELECTRICAL, T.ELECTRICITY),
    (E.INFORMATION, T.COMPUTATION),
    (E.ADVANCED, T.NUCLEAR_POWER),
)
ERA_FLOORS: MappingProxyType[TechnologyEra, dict[KnowledgeBranch, int]] = MappingProxyType(
    {
        E.STONE: {},
        E.BRONZE: {B.AGRICULTURE: 1, B.METALLURGY: 1},
        E.IRON: {B.AGRICULTURE: 2, B.METALLURGY: 2, B.WRITING: 1, B.WARFARE: 1},
        E.MEDIEVAL: {B.AGRICULTURE: 3, B.METALLURGY: 3, B.WRITING: 2, B.WARFARE: 2, B.ARCHITECTURE: 2, B.TRADE: 2},
        E.GUNPOWDER: {B.AGRICULTURE: 3, B.METALLURGY: 4, B.WRITING: 3, B.WARFARE: 3, B.ARCHITECTURE: 3, B.TRADE: 3},
        E.RENAISSANCE: {B.AGRICULTURE: 4, B.METALLURGY: 4, B.WRITING: 4, B.WARFARE: 4, B.ARCHITECTURE: 3, B.TRADE: 3, B.ASTRONOMY: 3},
        E.STEAM: {B.AGRICULTURE: 5, B.METALLURGY: 6, B.WRITING: 5, B.WARFARE: 6, B.ARCHITECTURE: 4, B.TRADE: 4, B.ASTRONOMY: 4},
        E.ELECTRICAL: {B.AGRICULTURE: 6, B.METALLURGY: 8, B.WRITING: 7, B.WARFARE: 7, B.ARCHITECTURE: 7, B.TRADE: 6, B.ASTRONOMY: 5},
        E.INFORMATION: {B.AGRICULTURE: 8, B.METALLURGY: 9, B.WRITING: 9, B.WARFARE: 8, B.ARCHITECTURE: 8, B.TRADE: 7, B.ASTRONOMY: 7, B.MEDICINE: 8},
        E.ADVANCED: {B.AGRICULTURE: 9, B.METALLURGY: 10, B.WRITING: 10, B.WARFARE: 9, B.ARCHITECTURE: 9, B.TRADE: 8, B.ASTRONOMY: 8, B.MEDICINE: 9},
        E.INTERSTELLAR: {B.AGRICULTURE: 10, B.METALLURGY: 10, B.WRITING: 10, B.WARFARE: 10, B.ARCHITECTURE: 10, B.TRADE: 9, B.ASTRONOMY: 10, B.MEDICINE: 10},
        E.BEYOND: {
            B.AGRICULTURE: 10,
            B.METALLURGY: 10,
            B.WRITING: 10,
            B.WARFARE: 10,
            B.ARCHITECTURE: 10,
            B.TRADE: 10,
            B.ASTRONOMY: 10,
            B.MEDICINE: 10,
            B.CIVICS: 10,
        },
    }
)
POWDER = frozenset({T.GUNPOWDER, T.FIREARMS, T.CANNON, T.STAR_FORTS, T.VOLLEY_DRILL})
TECHNIQUE_ERAS: MappingProxyType[Technique, TechnologyEra] = MappingProxyType(
    {
        **dict.fromkeys((T.GUNPOWDER, T.FIREARMS, T.CANNON, T.STAR_FORTS, T.VOLLEY_DRILL), E.GUNPOWDER),
        **dict.fromkeys(
            (
                T.STEAM_POWER,
                T.COKE_SMELTING,
                T.MACHINE_TOOLS,
                T.RAILWAYS,
                T.STEAMSHIPS,
                T.FACTORY_PRODUCTION,
                T.INDUSTRIAL_CHEMISTRY,
                T.CANNED_FOOD,
                T.VACCINES,
            ),
            E.STEAM,
        ),
        **dict.fromkeys((T.ELECTRICITY, T.TELEGRAPH, T.TELEPHONE, T.ELECTRIC_LIGHT, T.REFRIGERATION, T.COMBUSTION_ENGINE, T.AVIATION), E.ELECTRICAL),
        **dict.fromkeys((T.COMPUTATION, T.RADIO, T.MASS_MEDIA, T.ANTIBIOTICS, T.GREEN_REVOLUTION), E.INFORMATION),
        **dict.fromkeys((T.NUCLEAR_POWER, T.NUCLEAR_WEAPONS, T.ROCKETRY, T.GENETIC_ENGINEERING, T.ARTIFICIAL_MINDS), E.ADVANCED),
    }
)
