from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.structure import EffectTarget, StructureEffect, StructureKind

K = StructureKind
E = StructureEffect
T = EffectTarget


@dataclass(frozen=True)
class EffectSpec:
    target: EffectTarget
    sign: int
    weight: int


EFFECTS: Mapping[StructureEffect, EffectSpec] = total(
    StructureEffect,
    {
        E.KNOWLEDGE_SPREAD: EffectSpec(T.LITERACY, 1, 60),
        E.LITERACY: EffectSpec(T.LITERACY, 1, 100),
        E.BOOK_OUTPUT: EffectSpec(T.LITERACY, 1, 80),
        E.RECORD_KEEPING: EffectSpec(T.PRESTIGE, 1, 40),
        E.RESEARCH_SPEED: EffectSpec(T.KNOWLEDGE, 1, 100),
        E.CREDENTIAL_OUTPUT: EffectSpec(T.KNOWLEDGE, 1, 60),
        E.TRAINING: EffectSpec(T.TRAIN, 1, 100),
        E.CLERGY_OUTPUT: EffectSpec(T.PIETY, 1, 80),
        E.ORTHODOXY: EffectSpec(T.PIETY, 1, 60),
        E.DIPLOMATIC_PRESENCE: EffectSpec(T.PRESTIGE, 1, 80),
        E.JUSTICE_THROUGHPUT: EffectSpec(T.PUBLIC_ORDER, 1, 100),
        E.TARIFF_EFFICIENCY: EffectSpec(T.TREASURY, 1, 100),
        E.SMUGGLING_DETECTION: EffectSpec(T.CRIME, -1, 60),
        E.PRICE_DISCOVERY: EffectSpec(T.PROSPERITY, 1, 60),
        E.SPECULATION: EffectSpec(T.SPECULATION, 1, 100),
        E.STORAGE: EffectSpec(T.SIEGE_SUPPLIES, 1, 100),
        E.PROCESSING: EffectSpec(T.PROSPERITY, 1, 80),
        E.ENERGY_OUTPUT: EffectSpec(T.PROSPERITY, 1, 100),
        E.POLLUTION: EffectSpec(T.SANITATION, -1, 80),
        E.LABOUR_CONCENTRATION: EffectSpec(T.UNREST, 1, 40),
        E.CRAFT_DISPLACEMENT: EffectSpec(T.UNREST, 1, 60),
        E.ROUTE_NODE: EffectSpec(T.HAULING_CAPACITY, 1, 100),
        E.ROUTE_SAFETY: EffectSpec(T.CRIME, -1, 40),
        E.ROUTE_SPEED: EffectSpec(T.HAULING_CAPACITY, 1, 60),
        E.CROSSING: EffectSpec(T.HAULING_CAPACITY, 1, 60),
        E.CHOKEPOINT: EffectSpec(T.TREASURY, 1, 60),
        E.TOLL: EffectSpec(T.TREASURY, 1, 80),
        E.GARRISON_RANGE: EffectSpec(T.PUBLIC_ORDER, 1, 60),
        E.UNIT_BASING: EffectSpec(T.MILITIA, 1, 100),
        E.DETERRENCE: EffectSpec(T.PUBLIC_ORDER, 1, 40),
        E.STRIKE_CAPACITY: EffectSpec(T.PRESTIGE, 1, 60),
        E.DEFENCE: EffectSpec(T.MILITIA, 1, 60),
        E.EPIDEMIC_ISOLATION: EffectSpec(T.SANITATION, 1, 80),
        E.WATERBORNE_DISEASE_CUT: EffectSpec(T.SANITATION, 1, 100),
        E.MIND_CARE: EffectSpec(T.CALM, 1, 100),
        E.CONFINEMENT: EffectSpec(T.CRIME, -1, 80),
        E.BURIAL_CAPACITY: EffectSpec(T.SANITATION, 1, 60),
        E.REMEMBRANCE: EffectSpec(T.PRESTIGE, 1, 60),
        E.COLLECTION: EffectSpec(T.PRESTIGE, 1, 80),
        E.SPECTACLE: EffectSpec(T.UNREST, -1, 80),
        E.ELITE_PRESTIGE: EffectSpec(T.PRESTIGE, 1, 100),
        E.ART_MARKET: EffectSpec(T.PROSPERITY, 1, 60),
        E.PERFORMANCE: EffectSpec(T.PRESTIGE, 1, 60),
        E.HOUSING: EffectSpec(T.UNREST, -1, 60),
        E.OVERCROWDING_RELIEF: EffectSpec(T.UNREST, -1, 80),
        E.FIRE_RISK: EffectSpec(T.FIRE_RISK, 1, 80),
        E.EXPLOSION_RISK: EffectSpec(T.FIRE_RISK, 1, 120),
        E.COLLAPSE_RISK: EffectSpec(T.FIRE_RISK, 1, 40),
        E.WATER_STORAGE: EffectSpec(T.SIEGE_WATER, 1, 100),
        E.IRRIGATION: EffectSpec(T.PROSPERITY, 1, 80),
        E.FOOD_OUTPUT_INDEPENDENT_OF_LAND: EffectSpec(T.SIEGE_SUPPLIES, 1, 80),
        E.ORBITAL_TRANSFER: EffectSpec(T.HAULING_CAPACITY, 1, 120),
        E.INTERWORLD_NODE: EffectSpec(T.HAULING_CAPACITY, 1, 100),
        E.INSTANT_TRANSIT: EffectSpec(T.HAULING_CAPACITY, 1, 150),
        E.ENVIRONMENT_SHIFT: EffectSpec(T.PROSPERITY, 1, 40),
        E.SURVEILLANCE_CAPACITY: EffectSpec(T.CRIME, -1, 80),
        E.NETWORK_NODE: EffectSpec(T.UNREST, -1, 30),
        E.MIND_SEAT: EffectSpec(T.KNOWLEDGE, 1, 40),
        E.MAKING: EffectSpec(T.CONSTRUCTION_CAPACITY, 1, 100),
        E.LODGING: EffectSpec(T.PROSPERITY, 1, 40),
        E.RUMOUR_EXCHANGE: EffectSpec(T.UNREST, 1, 20),
        E.HUNTING_YIELD: EffectSpec(T.SIEGE_SUPPLIES, 1, 60),
        E.CRIME_CUT: EffectSpec(T.CRIME, -1, 80),
        E.ATHLETIC_TRAINING: EffectSpec(T.MILITIA, 1, 60),
        E.RETAIL_SATISFACTION: EffectSpec(T.UNREST, -1, 60),
        E.HEADQUARTERS: EffectSpec(T.INVESTMENT_POOL, 1, 100),
        E.HEALING: EffectSpec(T.SANITATION, 1, 100),
        E.WORSHIP: EffectSpec(T.PIETY, 1, 100),
        E.COMMERCE: EffectSpec(T.PROSPERITY, 1, 100),
        E.GOVERNANCE: EffectSpec(T.PUBLIC_ORDER, 1, 100),
        E.WELFARE: EffectSpec(T.UNREST, -1, 100),
    },
)
STRUCTURE_OWN_EFFECTS: Mapping[StructureKind, tuple[StructureEffect, ...]] = total(
    StructureKind,
    {
        K.AI_CORE: (
            E.MIND_SEAT,
            E.RESEARCH_SPEED,
            E.NETWORK_NODE,
        ),
        K.AIRFIELD: (
            E.ROUTE_NODE,
            E.UNIT_BASING,
            E.ROUTE_SPEED,
            E.STRIKE_CAPACITY,
        ),
        K.APARTMENT_BLOCK: (
            E.HOUSING,
            E.OVERCROWDING_RELIEF,
            E.FIRE_RISK,
        ),
        K.ARCHIVE: (
            E.RECORD_KEEPING,
            E.MIND_SEAT,
        ),
        K.ARSENAL: (
            E.STORAGE,
            E.DEFENCE,
            E.EXPLOSION_RISK,
        ),
        K.ASYLUM: (
            E.MIND_CARE,
            E.CONFINEMENT,
        ),
        K.BAKERY: (E.PROCESSING,),
        K.BOTANICAL_GARDEN: (
            E.COLLECTION,
            E.RESEARCH_SPEED,
            E.TRAINING,
            E.ELITE_PRESTIGE,
        ),
        K.BROADCAST_TOWER: (
            E.NETWORK_NODE,
            E.KNOWLEDGE_SPREAD,
        ),
        K.CANAL_LOCK: (
            E.CROSSING,
            E.TOLL,
            E.CHOKEPOINT,
        ),
        K.CEMETERY: (
            E.BURIAL_CAPACITY,
            E.REMEMBRANCE,
        ),
        K.CISTERN: (E.WATER_STORAGE,),
        K.CLONING_FACILITY: (
            E.MAKING,
            E.HEALING,
        ),
        K.CONSERVATORY: (
            E.TRAINING,
            E.PERFORMANCE,
        ),
        K.COURTHOUSE: (E.JUSTICE_THROUGHPUT,),
        K.CUSTOMS_HOUSE: (
            E.TARIFF_EFFICIENCY,
            E.SMUGGLING_DETECTION,
        ),
        K.DAIRY: (E.PROCESSING,),
        K.DATA_CENTRE: (
            E.RECORD_KEEPING,
            E.NETWORK_NODE,
            E.MIND_SEAT,
            E.SURVEILLANCE_CAPACITY,
        ),
        K.DISTILLERY: (
            E.PROCESSING,
            E.TARIFF_EFFICIENCY,
        ),
        K.DRY_DOCK: (E.MAKING,),
        K.DYE_WORKS: (
            E.PROCESSING,
            E.POLLUTION,
        ),
        K.EMBASSY: (E.DIPLOMATIC_PRESENCE,),
        K.EXCHANGE: (
            E.PRICE_DISCOVERY,
            E.SPECULATION,
            E.HEADQUARTERS,
        ),
        K.FACTORY: (
            E.PROCESSING,
            E.LABOUR_CONCENTRATION,
            E.POLLUTION,
            E.CRAFT_DISPLACEMENT,
        ),
        K.FOUNDRY: (
            E.PROCESSING,
            E.MAKING,
        ),
        K.GALLERY: (
            E.ART_MARKET,
            E.COLLECTION,
        ),
        K.GLASSWORKS: (E.PROCESSING,),
        K.GYMNASIUM: (
            E.ATHLETIC_TRAINING,
            E.TRAINING,
        ),
        K.INN: (
            E.LODGING,
            E.RUMOUR_EXCHANGE,
            E.ROUTE_SAFETY,
        ),
        K.KENNEL: (
            E.HUNTING_YIELD,
            E.CRIME_CUT,
        ),
        K.KILN: (
            E.PROCESSING,
            E.MAKING,
        ),
        K.LABORATORY: (
            E.RESEARCH_SPEED,
            E.EXPLOSION_RISK,
        ),
        K.LIGHTHOUSE: (
            E.ROUTE_SAFETY,
            E.ROUTE_NODE,
        ),
        K.MALL: (
            E.RETAIL_SATISFACTION,
            E.COMMERCE,
        ),
        K.MARKET_HALL: (
            E.COMMERCE,
            E.PRICE_DISCOVERY,
        ),
        K.MENAGERIE: (
            E.COLLECTION,
            E.ELITE_PRESTIGE,
        ),
        K.MILITARY_BASE: (
            E.GARRISON_RANGE,
            E.UNIT_BASING,
            E.TRAINING,
        ),
        K.MISSILE_SILO: (
            E.STRIKE_CAPACITY,
            E.DETERRENCE,
        ),
        K.OFFICE_TOWER: (E.HEADQUARTERS,),
        K.OPERA_HOUSE: (
            E.PERFORMANCE,
            E.ELITE_PRESTIGE,
        ),
        K.PAPER_MILL: (
            E.PROCESSING,
            E.LITERACY,
            E.BOOK_OUTPUT,
        ),
        K.POWER_PLANT: (
            E.ENERGY_OUTPUT,
            E.POLLUTION,
        ),
        K.PRINTING_HOUSE: (
            E.BOOK_OUTPUT,
            E.LITERACY,
            E.KNOWLEDGE_SPREAD,
        ),
        K.QUARANTINE_HOUSE: (E.EPIDEMIC_ISOLATION,),
        K.RAIL_STATION: (
            E.ROUTE_NODE,
            E.ROUTE_SPEED,
        ),
        K.RECYCLING_PLANT: (E.PROCESSING,),
        K.REFINERY: (
            E.PROCESSING,
            E.EXPLOSION_RISK,
            E.POLLUTION,
        ),
        K.RESERVOIR: (
            E.WATER_STORAGE,
            E.IRRIGATION,
            E.COLLAPSE_RISK,
        ),
        K.ROBOTICS_WORKS: (
            E.MAKING,
            E.LABOUR_CONCENTRATION,
        ),
        K.SATELLITE_ARRAY: (
            E.SURVEILLANCE_CAPACITY,
            E.RESEARCH_SPEED,
            E.NETWORK_NODE,
        ),
        K.SEMINARY: (
            E.CLERGY_OUTPUT,
            E.ORTHODOXY,
            E.TRAINING,
        ),
        K.SHIELD_GENERATOR: (E.DEFENCE,),
        K.SIGNAL_TOWER: (
            E.NETWORK_NODE,
            E.ROUTE_SPEED,
        ),
        K.SILO: (E.STORAGE,),
        K.SMELTER: (
            E.PROCESSING,
            E.POLLUTION,
        ),
        K.SPACE_ELEVATOR: (
            E.ORBITAL_TRANSFER,
            E.CHOKEPOINT,
            E.COLLAPSE_RISK,
        ),
        K.SPACE_STATION: (
            E.MAKING,
            E.UNIT_BASING,
            E.HOUSING,
        ),
        K.SPACEPORT: (
            E.INTERWORLD_NODE,
            E.TARIFF_EFFICIENCY,
        ),
        K.STADIUM: (E.SPECTACLE,),
        K.TELEPORTER: (E.INSTANT_TRANSIT,),
        K.TERRAFORMER: (E.ENVIRONMENT_SHIFT,),
        K.TEXTILE_MILL: (
            E.PROCESSING,
            E.CRAFT_DISPLACEMENT,
            E.POLLUTION,
        ),
        K.TOLL_GATE: (E.TOLL,),
        K.TUNNEL: (
            E.CROSSING,
            E.CHOKEPOINT,
            E.COLLAPSE_RISK,
        ),
        K.UNIVERSITY: (
            E.CREDENTIAL_OUTPUT,
            E.RESEARCH_SPEED,
        ),
        K.VERTICAL_FARM: (E.FOOD_OUTPUT_INDEPENDENT_OF_LAND,),
        K.WATER_PURIFICATION: (E.WATERBORNE_DISEASE_CUT,),
        K.TEMPLE: (
            E.WORSHIP,
            E.CLERGY_OUTPUT,
        ),
        K.SHRINE: (E.WORSHIP,),
        K.MONASTERY: (
            E.WORSHIP,
            E.BOOK_OUTPUT,
        ),
        K.NECROPOLIS: (
            E.BURIAL_CAPACITY,
            E.REMEMBRANCE,
        ),
        K.LIBRARY: (
            E.LITERACY,
            E.KNOWLEDGE_SPREAD,
        ),
        K.SCHOOL: (
            E.LITERACY,
            E.TRAINING,
        ),
        K.OBSERVATORY: (E.RESEARCH_SPEED,),
        K.ACADEMY: (
            E.RESEARCH_SPEED,
            E.CREDENTIAL_OUTPUT,
        ),
        K.HOSPITAL: (
            E.HEALING,
            E.EPIDEMIC_ISOLATION,
        ),
        K.WALL: (E.DEFENCE,),
        K.GATE: (
            E.DEFENCE,
            E.TOLL,
        ),
        K.TOWER: (
            E.DEFENCE,
            E.SURVEILLANCE_CAPACITY,
        ),
        K.CITADEL: (
            E.DEFENCE,
            E.GARRISON_RANGE,
        ),
        K.WATCHTOWER: (
            E.CRIME_CUT,
            E.SURVEILLANCE_CAPACITY,
        ),
        K.FORT: (
            E.DEFENCE,
            E.GARRISON_RANGE,
        ),
        K.PALACE: (
            E.GOVERNANCE,
            E.ELITE_PRESTIGE,
        ),
        K.COURT: (E.JUSTICE_THROUGHPUT,),
        K.PRISON: (
            E.CONFINEMENT,
            E.CRIME_CUT,
        ),
        K.MARKET: (E.COMMERCE,),
        K.HARBOUR: (
            E.ROUTE_NODE,
            E.TARIFF_EFFICIENCY,
        ),
        K.WAREHOUSE: (E.STORAGE,),
        K.GRANARY: (E.STORAGE,),
        K.CARAVANSERAI: (
            E.LODGING,
            E.ROUTE_NODE,
        ),
        K.BANK: (
            E.HEADQUARTERS,
            E.SPECULATION,
        ),
        K.FORGE: (
            E.PROCESSING,
            E.MAKING,
        ),
        K.MILL: (E.PROCESSING,),
        K.TANNERY: (
            E.PROCESSING,
            E.POLLUTION,
        ),
        K.MINE: (
            E.PROCESSING,
            E.COLLAPSE_RISK,
        ),
        K.QUARRY: (
            E.PROCESSING,
            E.COLLAPSE_RISK,
        ),
        K.SHIPYARD: (E.MAKING,),
        K.WORKSHOP: (
            E.PROCESSING,
            E.MAKING,
        ),
        K.ALCHEMIST_LAB: (
            E.RESEARCH_SPEED,
            E.EXPLOSION_RISK,
        ),
        K.ROAD: (E.ROUTE_SPEED,),
        K.BRIDGE: (E.CROSSING,),
        K.AQUEDUCT: (
            E.WATERBORNE_DISEASE_CUT,
            E.WATER_STORAGE,
        ),
        K.SEWER: (E.WATERBORNE_DISEASE_CUT,),
        K.CANAL: (
            E.ROUTE_NODE,
            E.ROUTE_SPEED,
        ),
        K.IRRIGATION: (E.IRRIGATION,),
        K.DAM: (
            E.WATER_STORAGE,
            E.COLLAPSE_RISK,
            E.ENERGY_OUTPUT,
        ),
        K.MONUMENT: (
            E.REMEMBRANCE,
            E.ELITE_PRESTIGE,
        ),
        K.TOMB: (E.REMEMBRANCE,),
        K.ARENA: (E.SPECTACLE,),
        K.THEATRE: (E.PERFORMANCE,),
        K.WONDER: (
            E.ELITE_PRESTIGE,
            E.REMEMBRANCE,
        ),
        K.COSMIC_GATE: (
            E.INSTANT_TRANSIT,
            E.INTERWORLD_NODE,
        ),
        K.FIREHOUSE: (E.CRIME_CUT,),
        K.BATHHOUSE: (E.HEALING,),
        K.KONTOR: (
            E.COMMERCE,
            E.TARIFF_EFFICIENCY,
        ),
        K.COVENANT: (
            E.TRAINING,
            E.ORTHODOXY,
        ),
        K.FOUNTAIN: (E.WATERBORNE_DISEASE_CUT,),
        K.PARK: (E.OVERCROWDING_RELIEF,),
        K.SLAUGHTERHOUSE: (
            E.PROCESSING,
            E.POLLUTION,
        ),
        K.ALMSHOUSE: (E.WELFARE,),
        K.COSMIC_ARCHIVE: (
            E.RECORD_KEEPING,
            E.RESEARCH_SPEED,
        ),
        K.BREWERY: (E.PROCESSING,),
        K.SAWMILL: (E.PROCESSING,),
        K.FISHERY: (E.HUNTING_YIELD,),
        K.CHARCOAL_KILN: (
            E.ENERGY_OUTPUT,
            E.POLLUTION,
        ),
        K.STABLES: (
            E.ROUTE_SPEED,
            E.UNIT_BASING,
        ),
        K.SIEGE_WORKSHOP: (
            E.MAKING,
            E.DEFENCE,
        ),
        K.MINT: (
            E.TARIFF_EFFICIENCY,
            E.COMMERCE,
        ),
        K.TAVERN: (
            E.RUMOUR_EXCHANGE,
            E.LODGING,
        ),
        K.TOWN_HALL: (E.GOVERNANCE,),
        K.GUILDHALL: (
            E.COMMERCE,
            E.TRAINING,
        ),
        K.BARRACKS: (
            E.UNIT_BASING,
            E.GARRISON_RANGE,
        ),
        K.ORPHANAGE: (E.WELFARE,),
        K.APOTHECARY: (E.HEALING,),
        K.TRAINING_GROUND: (
            E.ATHLETIC_TRAINING,
            E.TRAINING,
        ),
        K.MUSEUM: (
            E.COLLECTION,
            E.REMEMBRANCE,
        ),
        K.PLAZA: (
            E.SPECTACLE,
            E.RUMOUR_EXCHANGE,
        ),
        K.ORBITAL_RING: (
            E.ORBITAL_TRANSFER,
            E.COMMERCE,
        ),
        K.STAR_COLLECTOR: (E.ENERGY_OUTPUT,),
        K.BEACON: (
            E.ROUTE_SAFETY,
            E.NETWORK_NODE,
        ),
        K.PLANETARY_ENGINE: (E.ENVIRONMENT_SHIFT,),
        K.HABITAT_RING: (
            E.HOUSING,
            E.OVERCROWDING_RELIEF,
        ),
    },
)
