from dataclasses import dataclass
from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.facets import FacetChannel, FacetKind
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.structure import StructureKind

T = Technique
G = CommodityKind
C = FacetChannel
K = FacetKind
B = KnowledgeBranch
S = StructureKind


@dataclass(frozen=True)
class RowSource:
    table: str
    column: str
    field: str | None = None
    values: tuple[str, ...] = ()


@dataclass(frozen=True)
class FacetEffect:
    channel: C
    amount: int
    branch: B | None = None


@dataclass(frozen=True)
class FacetSpec:
    ocm: int
    label: str
    techniques: tuple[T, ...] = ()
    goods: tuple[G, ...] = ()
    structures: tuple[S, ...] = ()
    rows: tuple[RowSource, ...] = ()
    effects: tuple[FacetEffect, ...] = ()

    @property
    def groups(self) -> int:
        return sum(1 for group in (self.techniques, self.goods, self.structures, self.rows) if group)


FACETS: MappingProxyType[K, FacetSpec] = total(
    K,
    {
        K.PREHISTORY: FacetSpec(
            172, "Prehistory", structures=(S.MUSEUM, S.ARCHIVE), effects=(FacetEffect(C.PRESTIGE, 2), FacetEffect(C.RESEARCH, 1, B.WRITING))
        ),
        K.MARINE_INDUSTRIES: FacetSpec(228, "Marine industries", goods=(G.FISH,), structures=(S.FISHERY, S.HARBOUR), effects=(FacetEffect(C.PROSPERITY, 2),)),
        K.ANIMAL_BY_PRODUCTS: FacetSpec(
            237, "Animal by-products", goods=(G.LIVESTOCK, G.WOOL), structures=(S.SLAUGHTERHOUSE, S.TANNERY), effects=(FacetEffect(C.CRAFT, 2),)
        ),
        K.AGRICULTURAL_SCIENCE: FacetSpec(
            242,
            "Agricultural science",
            techniques=(T.CROP_ROTATION, T.SELECTIVE_BREEDING, T.IRRIGATION, T.TERRACING, T.DRAINAGE, T.GREEN_REVOLUTION),
            effects=(FacetEffect(C.PROSPERITY, 3), FacetEffect(C.RESEARCH, 1, B.AGRICULTURE)),
        ),
        K.FLORICULTURE: FacetSpec(247, "Floriculture", structures=(S.BOTANICAL_GARDEN, S.PARK), effects=(FacetEffect(C.PRESTIGE, 2), FacetEffect(C.PIETY, 1))),
        K.MEAT_PACKING: FacetSpec(
            253,
            "Meat packing",
            goods=(G.MEAT, G.LIVESTOCK),
            structures=(S.SLAUGHTERHOUSE,),
            effects=(FacetEffect(C.PROSPERITY, 1), FacetEffect(C.SANITATION, -2), FacetEffect(C.DISEASE, 1)),
        ),
        K.CONFECTIONERY: FacetSpec(
            257, "Confectionery", goods=(G.LUXURIES, G.FRUIT), structures=(S.BAKERY,), effects=(FacetEffect(C.PRESTIGE, 1), FacetEffect(C.PROSPERITY, 1))
        ),
        K.CANNIBALISM: FacetSpec(
            266,
            "Cannibalism",
            rows=(RowSource("people_culture", "people_entity_id", "remains_treatment", ("consumption",)),),
            effects=(FacetEffect(C.DISEASE, 1), FacetEffect(C.PIETY, 1)),
        ),
        K.NON_ALCOHOLIC_BEVERAGES: FacetSpec(
            272, "Non-alcoholic beverages", techniques=(T.REFRIGERATION,), goods=(G.HERBS,), effects=(FacetEffect(C.SANITATION, 2), FacetEffect(C.DISEASE, -1))
        ),
        K.BEVERAGE_INDUSTRIES: FacetSpec(
            274,
            "Beverage industries",
            goods=(G.BREW_BASE,),
            structures=(S.BREWERY, S.DISTILLERY, S.TAVERN),
            effects=(FacetEffect(C.PROSPERITY, 1), FacetEffect(C.PUBLIC_ORDER, -1)),
        ),
        K.STIMULANT_LEAVES: FacetSpec(
            277, "Smoking and stimulant leaves", goods=(G.HERBS,), structures=(S.APOTHECARY,), effects=(FacetEffect(C.UNREST, -1), FacetEffect(C.DISEASE, 1))
        ),
        K.LEATHER_INDUSTRY: FacetSpec(
            282, "Leather industry", goods=(G.LIVESTOCK,), structures=(S.TANNERY,), effects=(FacetEffect(C.CRAFT, 2), FacetEffect(C.SANITATION, -2))
        ),
        K.CORDAGE: FacetSpec(283, "Cordage", goods=(G.FIBRE,), structures=(S.SHIPYARD,), effects=(FacetEffect(C.HAULING, 2), FacetEffect(C.CONSTRUCTION, 1))),
        K.KNOTS_AND_LASHINGS: FacetSpec(284, "Knots and lashings", goods=(G.FIBRE,), effects=(FacetEffect(C.CONSTRUCTION, 1),)),
        K.FELTED_FABRICS: FacetSpec(287, "Felted fabrics", goods=(G.WOOL,), effects=(FacetEffect(C.PROSPERITY, 1),)),
        K.PAPER_INDUSTRY: FacetSpec(
            289,
            "Paper industry",
            techniques=(T.PAPER, T.PRINTING),
            structures=(S.PAPER_MILL, S.PRINTING_HOUSE),
            effects=(FacetEffect(C.RESEARCH, 2, B.WRITING),),
        ),
        K.CLOTHING: FacetSpec(290, "Clothing", goods=(G.CLOTH,), effects=(FacetEffect(C.PRESTIGE, 1), FacetEffect(C.PROSPERITY, 1))),
        K.NORMAL_GARB: FacetSpec(291, "Normal garb", goods=(G.CLOTH, G.WOOL, G.FIBRE), effects=(FacetEffect(C.PROSPERITY, 1),)),
        K.CLOTHING_MANUFACTURE: FacetSpec(
            294,
            "Clothing manufacture",
            goods=(G.CLOTH,),
            structures=(S.TEXTILE_MILL, S.WORKSHOP),
            effects=(FacetEffect(C.CRAFT, 2), FacetEffect(C.PROSPERITY, 1)),
        ),
        K.ORNAMENT: FacetSpec(301, "Ornament", goods=(G.LUXURIES,), effects=(FacetEffect(C.PRESTIGE, 2),)),
        K.JEWELLERY_MANUFACTURE: FacetSpec(
            306, "Jewellery manufacture", goods=(G.LUXURIES, G.ORE), structures=(S.WORKSHOP,), effects=(FacetEffect(C.WEALTH, 1), FacetEffect(C.PRESTIGE, 1))
        ),
        K.WOODWORKING: FacetSpec(
            322, "Woodworking", goods=(G.TIMBER,), structures=(S.SAWMILL, S.WORKSHOP), effects=(FacetEffect(C.CONSTRUCTION, 2), FacetEffect(C.CRAFT, 1))
        ),
        K.CERAMICS: FacetSpec(323, "Ceramics", goods=(G.STONE,), structures=(S.KILN,), effects=(FacetEffect(C.SANITATION, 1), FacetEffect(C.CRAFT, 1))),
        K.STONE_TOOLS: FacetSpec(324, "Stone tools", goods=(G.STONE,), effects=(FacetEffect(C.CRAFT, 1),)),
        K.MASONRY: FacetSpec(
            333,
            "Masonry",
            techniques=(T.ARCH, T.DOME),
            goods=(G.STONE,),
            structures=(S.QUARRY,),
            effects=(FacetEffect(C.CONSTRUCTION, 2), FacetEffect(C.FIRE_RISK, -1)),
        ),
        K.TALL_FRAME_BUILDING: FacetSpec(
            334,
            "Tall frame building",
            techniques=(T.STEEL, T.MACHINE_TOOLS),
            structures=(S.OFFICE_TOWER, S.APARTMENT_BLOCK),
            effects=(FacetEffect(C.CONSTRUCTION, 1), FacetEffect(C.FIRE_RISK, 1)),
        ),
        K.CARPENTRY: FacetSpec(
            335, "Carpentry", goods=(G.TIMBER,), structures=(S.SAWMILL,), effects=(FacetEffect(C.CONSTRUCTION, 2), FacetEffect(C.FIRE_RISK, 1))
        ),
        K.ELECTRICAL_INSTALLATION: FacetSpec(
            337,
            "Electrical installation",
            techniques=(T.ELECTRICITY,),
            structures=(S.POWER_PLANT,),
            effects=(FacetEffect(C.PROSPERITY, 2), FacetEffect(C.FIRE_RISK, 1)),
        ),
        K.OTHER_BUILDING_TRADES: FacetSpec(
            338,
            "Other building trades",
            techniques=(T.DRAINAGE,),
            structures=(S.GLASSWORKS, S.KILN),
            effects=(FacetEffect(C.SANITATION, 1), FacetEffect(C.CONSTRUCTION, 1)),
        ),
        K.HEATING_AND_LIGHTING: FacetSpec(
            354,
            "Heating and lighting equipment",
            techniques=(T.ELECTRIC_LIGHT,),
            goods=(G.FUEL, G.COAL),
            effects=(FacetEffect(C.PROSPERITY, 1), FacetEffect(C.FIRE_RISK, 1)),
        ),
        K.LIFTS_AND_BUILDING_MACHINES: FacetSpec(
            355,
            "Lifts and building machines",
            techniques=(T.ELECTRICITY, T.STEAM_POWER),
            structures=(S.OFFICE_TOWER,),
            effects=(FacetEffect(C.CONSTRUCTION, 2),),
        ),
        K.PUBLIC_UTILITIES: FacetSpec(
            365,
            "Public utilities",
            techniques=(T.AQUEDUCT, T.DRAINAGE),
            structures=(S.AQUEDUCT, S.SEWER, S.WATER_PURIFICATION, S.RESERVOIR, S.CISTERN),
            effects=(FacetEffect(C.SANITATION, 3), FacetEffect(C.DISEASE, -2)),
        ),
        K.PARKS: FacetSpec(367, "Parks", structures=(S.PARK, S.PLAZA, S.BOTANICAL_GARDEN), effects=(FacetEffect(C.UNREST, -1), FacetEffect(C.SANITATION, 1))),
        K.OTHER_FACILITIES: FacetSpec(
            368, "Other facilities", structures=(S.BATHHOUSE, S.FIREHOUSE, S.ALMSHOUSE), effects=(FacetEffect(C.SANITATION, 1), FacetEffect(C.FIRE_RISK, -1))
        ),
        K.ELECTRIC_POWER: FacetSpec(
            377,
            "Electric power",
            techniques=(T.ELECTRICITY,),
            structures=(S.POWER_PLANT,),
            effects=(FacetEffect(C.PROSPERITY, 3), FacetEffect(C.RESEARCH, 1, B.METALLURGY)),
        ),
        K.FISSION_AND_FUSION: FacetSpec(
            378,
            "Fission and fusion power",
            techniques=(T.NUCLEAR_POWER,),
            structures=(S.POWER_PLANT,),
            effects=(FacetEffect(C.PROSPERITY, 3), FacetEffect(C.DISEASE, 1)),
        ),
        K.ELASTIC_MATERIALS: FacetSpec(383, "Rubber and elastic materials", techniques=(T.INDUSTRIAL_CHEMISTRY,), effects=(FacetEffect(C.HAULING, 1),)),
        K.SYNTHETIC_MATERIALS: FacetSpec(
            384,
            "Synthetic materials",
            techniques=(T.INDUSTRIAL_CHEMISTRY,),
            structures=(S.REFINERY, S.FACTORY),
            effects=(FacetEffect(C.CRAFT, 2), FacetEffect(C.SANITATION, -1)),
        ),
        K.PAINTS_AND_DYES: FacetSpec(
            386, "Paints and dyes", goods=(G.DYE,), structures=(S.DYE_WORKS,), effects=(FacetEffect(C.PRESTIGE, 1), FacetEffect(C.SANITATION, -1))
        ),
        K.FERTILIZERS: FacetSpec(
            387,
            "Fertilizers",
            techniques=(T.GREEN_REVOLUTION, T.INDUSTRIAL_CHEMISTRY),
            goods=(G.DUNG,),
            effects=(FacetEffect(C.PROSPERITY, 2), FacetEffect(C.SANITATION, -1)),
        ),
        K.SOAP_AND_CLEANERS: FacetSpec(
            388,
            "Soap and cleaners",
            techniques=(T.INDUSTRIAL_CHEMISTRY,),
            goods=(G.LIVESTOCK,),
            effects=(FacetEffect(C.SANITATION, 2), FacetEffect(C.DISEASE, -1)),
        ),
        K.EXPLOSIVES: FacetSpec(
            389, "Explosives", techniques=(T.GUNPOWDER,), structures=(S.ARSENAL, S.MINE), effects=(FacetEffect(C.CONSTRUCTION, 1), FacetEffect(C.FIRE_RISK, 2))
        ),
        K.CAPITAL_GOODS: FacetSpec(
            390, "Capital goods", techniques=(T.MACHINE_TOOLS,), goods=(G.TOOLS,), structures=(S.FOUNDRY, S.FACTORY), effects=(FacetEffect(C.CRAFT, 2),)
        ),
        K.HARDWARE: FacetSpec(391, "Hardware", goods=(G.TOOLS, G.ORE), structures=(S.FORGE,), effects=(FacetEffect(C.CONSTRUCTION, 1),)),
        K.MACHINE_INDUSTRIES: FacetSpec(
            392,
            "Machine industries",
            techniques=(T.MACHINE_TOOLS, T.FACTORY_PRODUCTION),
            structures=(S.FACTORY, S.ROBOTICS_WORKS),
            effects=(FacetEffect(C.CRAFT, 3),),
        ),
        K.ELECTRICAL_SUPPLIES: FacetSpec(
            393, "Electrical supplies", techniques=(T.ELECTRICITY,), structures=(S.FACTORY,), effects=(FacetEffect(C.RESEARCH, 1, B.METALLURGY),)
        ),
        K.MAKING_HEATING_AND_LIGHTING: FacetSpec(
            394, "Making heating and lighting equipment", techniques=(T.ELECTRIC_LIGHT,), structures=(S.FOUNDRY,), effects=(FacetEffect(C.PROSPERITY, 1),)
        ),
        K.OPTICS: FacetSpec(
            395, "Optics", techniques=(T.ASTRONOMY_INSTRUMENTS,), structures=(S.GLASSWORKS, S.OBSERVATORY), effects=(FacetEffect(C.RESEARCH, 2, B.ASTRONOMY),)
        ),
        K.RAIL_EQUIPMENT: FacetSpec(
            397, "Rail equipment", techniques=(T.RAILWAYS,), structures=(S.RAIL_STATION, S.FOUNDRY), effects=(FacetEffect(C.HAULING, 3),)
        ),
        K.AIRCRAFT_INDUSTRY: FacetSpec(
            399,
            "Aircraft industry",
            techniques=(T.AVIATION,),
            structures=(S.AIRFIELD, S.FACTORY),
            effects=(FacetEffect(C.HAULING, 2), FacetEffect(C.DEFENSE, 1)),
        ),
        K.MACHINES: FacetSpec(400, "Machines", techniques=(T.STEAM_POWER, T.MACHINE_TOOLS), effects=(FacetEffect(C.CRAFT, 2),)),
        K.ELECTRICAL_MACHINES: FacetSpec(403, "Electrical machines", techniques=(T.ELECTRICITY, T.MACHINE_TOOLS), effects=(FacetEffect(C.CRAFT, 2),)),
        K.HOUSEHOLD_MACHINES: FacetSpec(
            404, "Household machines", techniques=(T.ELECTRICITY, T.REFRIGERATION), effects=(FacetEffect(C.PROSPERITY, 1), FacetEffect(C.UNREST, -1))
        ),
        K.WEIGHT_MOVING_MACHINES: FacetSpec(
            406,
            "Weight-moving machines",
            techniques=(T.STEAM_POWER,),
            structures=(S.HARBOUR, S.DRY_DOCK),
            effects=(FacetEffect(C.HAULING, 2), FacetEffect(C.CONSTRUCTION, 1)),
        ),
        K.COMPUTING: FacetSpec(
            408, "Computing", techniques=(T.COMPUTATION,), structures=(S.DATA_CENTRE, S.AI_CORE), effects=(FacetEffect(C.RESEARCH, 3, B.WRITING),)
        ),
        K.OTHER_HARDWARE: FacetSpec(414, "Other hardware", goods=(G.TOOLS,), effects=(FacetEffect(C.CRAFT, 1),)),
        K.APPLIANCES: FacetSpec(416, "Appliances", techniques=(T.REFRIGERATION, T.ELECTRICITY), effects=(FacetEffect(C.PROSPERITY, 1),)),
        K.APPARATUS: FacetSpec(
            417,
            "Apparatus",
            techniques=(T.ASTRONOMY_INSTRUMENTS,),
            structures=(S.LABORATORY, S.OBSERVATORY),
            effects=(FacetEffect(C.RESEARCH, 2, B.ASTRONOMY),),
        ),
        K.DIVISION_OF_LABOUR: FacetSpec(
            462,
            "Division of labour",
            techniques=(T.GUILDS,),
            structures=(S.GUILDHALL,),
            rows=(RowSource("kin_role_duties", "people_entity_id"),),
            effects=(FacetEffect(C.CRAFT, 1), FacetEffect(C.PROSPERITY, 1)),
        ),
        K.RAILWAYS: FacetSpec(
            496, "Railways", techniques=(T.RAILWAYS,), structures=(S.RAIL_STATION,), effects=(FacetEffect(C.HAULING, 3), FacetEffect(C.PROSPERITY, 1))
        ),
        K.NAVIGATION: FacetSpec(
            502,
            "Navigation",
            techniques=(T.NAVIGATION_STARS, T.CARTOGRAPHY, T.SAILING),
            structures=(S.LIGHTHOUSE,),
            effects=(FacetEffect(C.HAULING, 1), FacetEffect(C.RESEARCH, 1, B.SEAFARING)),
        ),
        K.AIRCRAFT: FacetSpec(506, "Aircraft", techniques=(T.AVIATION,), effects=(FacetEffect(C.HAULING, 1), FacetEffect(C.DEFENSE, 1))),
        K.AVIATION: FacetSpec(507, "Aviation", techniques=(T.AVIATION,), structures=(S.AIRFIELD,), effects=(FacetEffect(C.HAULING, 2),)),
        K.AIRFIELDS: FacetSpec(508, "Airfields", structures=(S.AIRFIELD,), effects=(FacetEffect(C.HAULING, 1),)),
        K.MUSIC: FacetSpec(
            533,
            "Music",
            structures=(S.THEATRE, S.OPERA_HOUSE, S.CONSERVATORY),
            rows=(RowSource("music_traditions", "origin_node_id"),),
            effects=(FacetEffect(C.PRESTIGE, 1), FacetEffect(C.UNREST, -1)),
        ),
        K.MUSICAL_INSTRUMENTS: FacetSpec(
            534,
            "Musical instruments",
            structures=(S.CONSERVATORY, S.WORKSHOP),
            rows=(RowSource("instrument_kinds", "origin_node_id"),),
            effects=(FacetEffect(C.CRAFT, 1),),
        ),
        K.SPECTACLES: FacetSpec(
            541,
            "Spectacles",
            structures=(S.ARENA, S.STADIUM, S.THEATRE),
            rows=(RowSource("gatherings", "host_node_id", "kind", ("games", "tournament", "procession", "sport_match", "performance")),),
            effects=(FacetEffect(C.UNREST, -2), FacetEffect(C.CRIME, 1)),
        ),
        K.STATUS_BY_SEX: FacetSpec(562, "Status by sex", rows=(RowSource("kin_role_duties", "people_entity_id"),), effects=(FacetEffect(C.CRAFT, -1),)),
        K.UNION_PAYMENTS: FacetSpec(
            583, "Union payments", structures=(S.MARKET,), rows=(RowSource("union_customs", "people_entity_id"),), effects=(FacetEffect(C.WEALTH, 1),)
        ),
        K.NUPTIALS: FacetSpec(
            585,
            "Nuptials",
            rows=(RowSource("gatherings", "host_node_id", "kind", ("wedding",)), RowSource("union_customs", "people_entity_id")),
            effects=(FacetEffect(C.PRESTIGE, 1), FacetEffect(C.UNREST, -1)),
        ),
        K.CELIBACY: FacetSpec(
            589, "Celibacy", structures=(S.MONASTERY,), rows=(RowSource("restraint_customs", "people_entity_id"),), effects=(FacetEffect(C.PIETY, 2),)
        ),
        K.PLURAL_UNIONS: FacetSpec(
            595, "Plural unions", rows=(RowSource("union_customs", "people_entity_id", "form", ("plural", "group")),), effects=(FacetEffect(C.PRESTIGE, 1),)
        ),
        K.CLANS: FacetSpec(
            614,
            "Clans",
            rows=(RowSource("kin_groups", "people_entity_id", "form", ("clan",)),),
            effects=(FacetEffect(C.PUBLIC_ORDER, 1), FacetEffect(C.CRIME, -1)),
        ),
        K.MOIETIES: FacetSpec(
            616, "Moieties", rows=(RowSource("kin_groups", "people_entity_id", "form", ("moiety",)),), effects=(FacetEffect(C.PUBLIC_ORDER, 1),)
        ),
        K.FORMS_OF_GOVERNMENT: FacetSpec(
            642,
            "Forms of government",
            techniques=(T.WRITTEN_LAW, T.BUREAUCRACY),
            rows=(RowSource("polity_profiles", "capital_entity_id"),),
            effects=(FacetEffect(C.PUBLIC_ORDER, 2),),
        ),
        K.OFFENCES_AGAINST_PERSONS: FacetSpec(
            683,
            "Offences against persons",
            rows=(RowSource("crime_cases", "settlement_entity_id", "crime", ("assault", "kidnapping", "threats", "murder", "manslaughter")),),
            effects=(FacetEffect(C.UNREST, 1), FacetEffect(C.PUBLIC_ORDER, -1)),
        ),
        K.UNION_OFFENCES: FacetSpec(
            684, "Union offences", rows=(RowSource("crime_cases", "settlement_entity_id", "crime", ("union_offence",)),), effects=(FacetEffect(C.UNREST, 1),)
        ),
        K.PROPERTY_OFFENCES: FacetSpec(
            685,
            "Property offences",
            rows=(RowSource("crime_cases", "settlement_entity_id", "crime", ("theft", "burglary", "robbery", "fraud", "trespass", "vandalism")),),
            effects=(FacetEffect(C.CRIME, 1), FacetEffect(C.PROSPERITY, -1)),
        ),
        K.OFFENCES_AGAINST_THE_STATE: FacetSpec(
            687,
            "Offences against the state",
            rows=(RowSource("crime_cases", "settlement_entity_id", "crime", ("treason", "sedition", "desertion", "tax_evasion")),),
            effects=(FacetEffect(C.UNREST, 2),),
        ),
        K.MILITARY_ENGINEERING: FacetSpec(
            711,
            "Military engineering",
            techniques=(T.FORTIFICATION, T.SIEGECRAFT, T.STAR_FORTS),
            structures=(S.SIEGE_WORKSHOP, S.FORT),
            effects=(FacetEffect(C.DEFENSE, 2),),
        ),
        K.ORDNANCE: FacetSpec(713, "Ordnance", techniques=(T.CANNON,), structures=(S.ARSENAL, S.FOUNDRY), effects=(FacetEffect(C.DEFENSE, 2),)),
        K.MILITARY_VEHICLES: FacetSpec(
            715, "Military vehicles", techniques=(T.COMBUSTION_ENGINE,), structures=(S.ARSENAL,), effects=(FacetEffect(C.DEFENSE, 1),)
        ),
        K.MILITARY_AIRCRAFT: FacetSpec(
            717, "Military aircraft", techniques=(T.AVIATION,), structures=(S.AIRFIELD, S.MILITARY_BASE), effects=(FacetEffect(C.DEFENSE, 2),)
        ),
        K.SPECIAL_MILITARY_EQUIPMENT: FacetSpec(
            718,
            "Special military equipment",
            techniques=(T.RADIO, T.COMPUTATION),
            structures=(S.MILITARY_BASE, S.SATELLITE_ARRAY),
            effects=(FacetEffect(C.DEFENSE, 1),),
        ),
        K.HEALING_RITES: FacetSpec(
            755, "Healing rites", techniques=(T.HERBALISM,), structures=(S.SHRINE, S.TEMPLE), effects=(FacetEffect(C.DISEASE, -1), FacetEffect(C.PIETY, 1))
        ),
        K.SPIRITUAL_HEALERS: FacetSpec(
            756, "Spiritual healers", techniques=(T.HERBALISM,), structures=(S.SHRINE, S.TEMPLE, S.MONASTERY), effects=(FacetEffect(C.DISEASE, -1),)
        ),
        K.MEDICAL_PERSONNEL: FacetSpec(
            759,
            "Medical personnel",
            techniques=(T.SURGERY, T.HOSPITALS),
            structures=(S.HOSPITAL, S.APOTHECARY),
            effects=(FacetEffect(C.DISEASE, -2), FacetEffect(C.RESEARCH, 1, B.MEDICINE)),
        ),
        K.SUICIDE: FacetSpec(
            762, "Suicide", structures=(S.ASYLUM,), rows=(RowSource("restraint_customs", "people_entity_id"),), effects=(FacetEffect(C.PUBLIC_ORDER, -1),)
        ),
        K.DYING: FacetSpec(763, "Dying", structures=(S.CEMETERY, S.NECROPOLIS), effects=(FacetEffect(C.PIETY, 1),)),
        K.CULT_OF_THE_DEAD: FacetSpec(
            769,
            "Cult of the dead",
            structures=(S.TOMB, S.NECROPOLIS, S.SHRINE),
            rows=(RowSource("death_work", "people_entity_id"),),
            effects=(FacetEffect(C.PIETY, 2),),
        ),
        K.ASCETICISM: FacetSpec(
            785,
            "Asceticism",
            structures=(S.MONASTERY,),
            rows=(RowSource("restraint_customs", "people_entity_id"),),
            effects=(FacetEffect(C.PIETY, 2), FacetEffect(C.PROSPERITY, -1)),
        ),
        K.LOGIC: FacetSpec(811, "Logic", techniques=(T.LOGIC,), effects=(FacetEffect(C.RESEARCH, 2, B.CIVICS),)),
        K.PHILOSOPHY: FacetSpec(
            812, "Philosophy", techniques=(T.NATURAL_PHILOSOPHY, T.HUMANIST_IDEALS), effects=(FacetEffect(C.RESEARCH, 1, B.CIVICS), FacetEffect(C.PRESTIGE, 1))
        ),
        K.SCIENTIFIC_METHOD: FacetSpec(813, "Scientific method", techniques=(T.EMPIRICISM,), effects=(FacetEffect(C.RESEARCH, 2, B.ASTRONOMY),)),
        K.HUMANISTIC_STUDY: FacetSpec(
            814, "Humanistic study", techniques=(T.HUMANIST_IDEALS,), structures=(S.LIBRARY, S.ARCHIVE), effects=(FacetEffect(C.RESEARCH, 2, B.WRITING),)
        ),
        K.VOCATIONAL_EDUCATION: FacetSpec(
            874, "Vocational education", techniques=(T.GUILDS,), structures=(S.GUILDHALL, S.SCHOOL), effects=(FacetEffect(C.CRAFT, 2),)
        ),
        K.TEACHERS: FacetSpec(
            875, "Teachers", structures=(S.SCHOOL, S.ACADEMY, S.UNIVERSITY), effects=(FacetEffect(C.RESEARCH, 1, B.WRITING), FacetEffect(C.CRAFT, 1))
        ),
        K.LIFE_STAGES: FacetSpec(
            880,
            "Life stages",
            rows=(RowSource("youth_standing", "people_entity_id"), RowSource("child_standing", "people_entity_id")),
            effects=(FacetEffect(C.PUBLIC_ORDER, 1),),
        ),
        K.COMING_OF_AGE: FacetSpec(
            884,
            "Coming of age",
            rows=(RowSource("tradition_profiles", "origin_entity_id", "stage", ("coming_of_age",)),),
            effects=(FacetEffect(C.PUBLIC_ORDER, 1), FacetEffect(C.UNREST, -1)),
        ),
        K.ROLES_BY_SEX: FacetSpec(890, "Roles by sex", rows=(RowSource("kin_role_duties", "people_entity_id"),), effects=(FacetEffect(C.CRAFT, -1),)),
    },
)
TOWN_FIELDS: MappingProxyType[C, str] = MappingProxyType(
    {
        C.SANITATION: "sanitation",
        C.FIRE_RISK: "fire_risk",
        C.CRIME: "crime",
        C.UNREST: "unrest",
        C.PUBLIC_ORDER: "public_order",
        C.PRESTIGE: "prestige",
        C.CONSTRUCTION: "construction_capacity",
        C.HAULING: "hauling_capacity",
    }
)
CAPACITY_FIELDS = frozenset({"construction_capacity", "hauling_capacity"})
STAT_CHANNELS = frozenset({C.PROSPERITY, C.PIETY, C.WEALTH, C.DEFENSE, C.CRAFT})
