from collections.abc import Mapping

from aerona.catalog.mythic import OFFICE_DOMAINS, OFFICE_FORMS
from aerona.core.grammar import spoken
from aerona.core.total import total
from aerona.db.kind_concepts.spec import ConceptSpec, KindProperty
from aerona.db.tables.nature_kinds import DivineOfficeKindRow, ProductionMethodKindRow, RealmKindRow, TraitKindRow
from aerona.domain.enums.arcana import SpellForm
from aerona.domain.enums.demography import NaturalTrait
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.ecology import PlantYield, YieldProduct
from aerona.domain.enums.industry import ProcessKind
from aerona.domain.enums.kinds import KindConcept
from aerona.domain.enums.mythic import CosmicOffice, MythicRealm
from aerona.domain.enums.nature_kinds import MaterialSource, OfficeDuty, ProductPart, RealmFunction, TraitFunction
from aerona.domain.enums.node import NodeKind
from aerona.domain.enums.polity import HouseTrait
from aerona.domain.enums.society import CreatureTrait

D = OfficeDuty
R = RealmFunction
F = TraitFunction

OFFICE_DUTY: Mapping[CosmicOffice, OfficeDuty] = total(
    CosmicOffice,
    {
        CosmicOffice.DEAD: D.THE_DEAD,
        CosmicOffice.GATES: D.THRESHOLDS,
        CosmicOffice.STARS: D.THE_SKY,
        CosmicOffice.OATHS: D.OATHS,
        CosmicOffice.HERALD: D.MESSAGES,
        CosmicOffice.HUNT: D.THE_HUNT,
    },
)
REALM_FUNCTION: Mapping[MythicRealm, RealmFunction] = total(
    MythicRealm,
    {MythicRealm.PALACE: R.SEAT_OF_GODS, MythicRealm.DEAD: R.ABODE_OF_DEAD, MythicRealm.DREAM: R.DREAM, MythicRealm.SACRED_SITE: R.SACRED_SITE},
)
FUNCTION_STEPS: Mapping[RealmFunction, int] = total(
    RealmFunction,
    {R.SEAT_OF_GODS: 1, R.ABODE_OF_DEAD: 2, R.DREAM: 0, R.SACRED_SITE: 0, R.PRISON: 3, R.GARDEN: 0},
)
FUNCTION_DANGER: Mapping[RealmFunction, int] = total(
    RealmFunction,
    {R.SEAT_OF_GODS: 30, R.ABODE_OF_DEAD: 50, R.DREAM: 20, R.SACRED_SITE: 10, R.PRISON: 70, R.GARDEN: 5},
)
NATURAL_TRAITS: Mapping[NaturalTrait, tuple[TraitFunction, int]] = total(
    NaturalTrait,
    {
        NaturalTrait.DARK_SIGHT: (F.AGILITY, 15),
        NaturalTrait.COLD_BLOODED: (F.RESILIENCE, -10),
        NaturalTrait.WINGED: (F.AGILITY, 30),
        NaturalTrait.AMPHIBIOUS: (F.RESILIENCE, 15),
        NaturalTrait.THICK_HIDE: (F.RESILIENCE, 30),
        NaturalTrait.KEEN_SENSES: (F.AGILITY, 20),
        NaturalTrait.VENOMOUS: (F.DANGER, 30),
        NaturalTrait.REGENERATING: (F.LONGEVITY, 30),
        NaturalTrait.BURROWING: (F.RESILIENCE, 10),
        NaturalTrait.HIVE_MINDED: (F.MIND, 20),
    },
)
HOUSE_TRAITS: Mapping[HouseTrait, tuple[TraitFunction, int]] = total(
    HouseTrait,
    {
        HouseTrait.LONG_LIVED: (F.LONGEVITY, 30),
        HouseTrait.GIANT_BLOODED: (F.STRENGTH, 40),
        HouseTrait.GOD_BLOODED: (F.DIVINITY, 40),
        HouseTrait.CURSED: (F.CHARM, -30),
        HouseTrait.FERTILE: (F.FERTILITY, 30),
        HouseTrait.SEER_GIFT: (F.MAGIC, 30),
        HouseTrait.STRONG_BLOODED: (F.STRENGTH, 25),
        HouseTrait.SWIFT: (F.AGILITY, 25),
        HouseTrait.QUICK_HEALING: (F.RESILIENCE, 25),
        HouseTrait.SHARP_SENSED: (F.AGILITY, 15),
        HouseTrait.STEADY: (F.RESILIENCE, 15),
        HouseTrait.QUICK_MINDED: (F.MIND, 25),
    },
)
CREATURE_TRAITS: Mapping[CreatureTrait, tuple[TraitFunction, int]] = total(
    CreatureTrait,
    {
        CreatureTrait.FLYING: (F.AGILITY, 30),
        CreatureTrait.VENOMOUS: (F.DANGER, 30),
        CreatureTrait.SOUL_EATER: (F.DANGER, 50),
        CreatureTrait.RADIANT: (F.DIVINITY, 25),
        CreatureTrait.FISSIPAROUS: (F.FERTILITY, 40),
        CreatureTrait.HIVE_MIND: (F.MIND, 25),
        CreatureTrait.STONESKIN: (F.RESILIENCE, 40),
        CreatureTrait.TIME_REWINDER: (F.MAGIC, 40),
        CreatureTrait.SHAPESHIFTER: (F.MAGIC, 30),
        CreatureTrait.MIND_READER: (F.MIND, 35),
        CreatureTrait.ARMOURED: (F.RESILIENCE, 30),
        CreatureTrait.BURROWING: (F.RESILIENCE, 10),
        CreatureTrait.AQUATIC: (F.AGILITY, 10),
        CreatureTrait.AMPHIBIOUS: (F.RESILIENCE, 15),
        CreatureTrait.PACK_HUNTER: (F.DANGER, 20),
        CreatureTrait.AMBUSH_PREDATOR: (F.DANGER, 25),
        CreatureTrait.REGENERATING: (F.LONGEVITY, 30),
        CreatureTrait.POISONOUS_FLESH: (F.RESILIENCE, 10),
        CreatureTrait.FIRE_BREATHING: (F.DANGER, 40),
        CreatureTrait.COLD_BREATHING: (F.DANGER, 35),
        CreatureTrait.ECHOLOCATION: (F.AGILITY, 15),
        CreatureTrait.CAMOUFLAGE: (F.AGILITY, 20),
        CreatureTrait.SWARM_BREEDER: (F.FERTILITY, 45),
        CreatureTrait.LONG_LIVED: (F.LONGEVITY, 30),
        CreatureTrait.MIMIC: (F.CHARM, 15),
        CreatureTrait.SPIRIT_SIGHT: (F.MAGIC, 20),
        CreatureTrait.IRON_EATING: (F.DANGER, 15),
        CreatureTrait.CROP_PEST: (F.FERTILITY, 20),
        CreatureTrait.PLAGUE_BEARER: (F.DANGER, 30),
        CreatureTrait.SACRED_ANIMAL: (F.DIVINITY, 30),
        CreatureTrait.HORNED: (F.STRENGTH, 15),
        CreatureTrait.TAILED: (F.AGILITY, 5),
    },
)
LEGACY_TRAITS: tuple[tuple[str, str, TraitFunction, int], ...] = (
    *((f"natural.{trait.value}", spoken(trait).capitalize(), function, strength) for trait, (function, strength) in NATURAL_TRAITS.items()),
    *((f"house.{trait.value}", spoken(trait).capitalize(), function, strength) for trait, (function, strength) in HOUSE_TRAITS.items()),
    *((f"creature.{trait.value}", spoken(trait).capitalize(), function, strength) for trait, (function, strength) in CREATURE_TRAITS.items()),
)
TRAIT_STATS: Mapping[TraitFunction, tuple[str | None, str | None, str | None]] = total(
    TraitFunction,
    {
        F.STRENGTH: ("strength", "martiality", "prestige"),
        F.AGILITY: ("agility", "martiality", None),
        F.MIND: ("intelligence", "craft", "prestige"),
        F.RESILIENCE: ("abundance", "prosperity", None),
        F.FERTILITY: ("abundance", "prosperity", None),
        F.DANGER: ("danger", "martiality", None),
        F.MAGIC: ("might", "magic", "prestige"),
        F.CHARM: (None, "prosperity", "prestige"),
        F.DIVINITY: ("might", "piety", "prestige"),
        F.LONGEVITY: ("abundance", "prosperity", "wealth"),
    },
)

METHOD_SPEC = ConceptSpec(
    concept=KindConcept.PRODUCTION_METHOD,
    label="Production method",
    plural="Production methods",
    hint="Ways a community works a process: what it yields, the hands and energy it needs, and how it wears its tools",
    table=ProductionMethodKindRow,
    category=ProcessKind,
    category_labels={process.value: spoken(process).capitalize() for process in ProcessKind},
    properties=(
        KindProperty("output_pct", "Output", "Share of the process's yield this method brings in (%)", 0, 500),
        KindProperty("quality_bonus", "Quality", "Quality it adds to or takes from what it makes", -50, 50),
        KindProperty("labour_pct", "Hands", "Hands it needs against the plainest way (%)", 0, 500),
        KindProperty("energy_need", "Energy", "Energy it draws for each lot it makes", 0, 100),
        KindProperty("tool_wear", "Tool wear", "How fast it wears the tools it uses", 0, 20),
    ),
    readers=("industry", "production"),
)
OFFICE_SPEC = ConceptSpec(
    concept=KindConcept.DIVINE_OFFICE,
    label="Divine office",
    plural="Divine offices",
    hint="Offices a god can hold in the cosmos, each with a duty; a neglected office lets its duty go undone",
    table=DivineOfficeKindRow,
    category=OfficeDuty,
    category_labels={duty.value: spoken(duty).capitalize() for duty in OfficeDuty},
    properties=(KindProperty("income_pct", "Income", "Share of the essence of its domains the holder takes (%)", 0, 500),),
    readers=("cosmic_offices",),
)
REALM_SPEC = ConceptSpec(
    concept=KindConcept.REALM,
    label="Realm",
    plural="Realms",
    hint="Realms beyond the world where heroquests go, each with the function it serves",
    table=RealmKindRow,
    category=RealmFunction,
    category_labels={function.value: spoken(function).capitalize() for function in RealmFunction},
    properties=(
        KindProperty("steps", "Extra trials", "Trials a heroquest into it faces on top of the usual", 0, 10),
        KindProperty("danger", "Danger", "How likely a quester is to fall in each trial"),
    ),
    readers=("heroquests",),
)
TRAIT_SPEC = ConceptSpec(
    concept=KindConcept.TRAIT,
    label="Trait",
    plural="Traits",
    hint="Traits of the body or a gift a species, people or house carries; each strengthens or weakens one capacity",
    table=TraitKindRow,
    category=TraitFunction,
    category_labels={function.value: spoken(function).capitalize() for function in TraitFunction},
    properties=(KindProperty("strength", "Strength", "How far it raises the capacity, or lowers it when below 0", -100, 100),),
    readers=("ways_of_life",),
)
SPECS = (METHOD_SPEC, OFFICE_SPEC, REALM_SPEC, TRAIT_SPEC)

DUTY_DOMAINS: Mapping[OfficeDuty, frozenset[Domain]] = total(
    OfficeDuty,
    {
        **{OFFICE_DUTY[office]: domains for office, domains in OFFICE_DOMAINS.items()},
        D.JUDGEMENT: frozenset({Domain.OATH, Domain.BORDER, Domain.KNOWLEDGE}),
        D.MEMORY: frozenset({Domain.MEMORY, Domain.TIME, Domain.DREAM}),
        D.MAKING: frozenset({Domain.CRAFT, Domain.STONE, Domain.TECHNOLOGY, Domain.MACHINES}),
        D.HEALING: frozenset({Domain.LIFE, Domain.PLANTS, Domain.HARVEST}),
        D.TRADE: frozenset({Domain.TRADE, Domain.ROAD}),
        D.LEARNING: frozenset({Domain.KNOWLEDGE, Domain.SCIENCE, Domain.INFORMATION}),
    },
)
DUTY_FORMS: Mapping[OfficeDuty, frozenset[SpellForm]] = total(
    OfficeDuty,
    {
        **{OFFICE_DUTY[office]: forms for office, forms in OFFICE_FORMS.items()},
        D.JUDGEMENT: frozenset({SpellForm.MIND, SpellForm.FATE}),
        D.MEMORY: frozenset({SpellForm.TIME, SpellForm.INFORMATION}),
        D.MAKING: frozenset({SpellForm.EARTH, SpellForm.MACHINE}),
        D.HEALING: frozenset({SpellForm.BODY, SpellForm.PLANT}),
        D.TRADE: frozenset({SpellForm.FATE, SpellForm.INFORMATION}),
        D.LEARNING: frozenset({SpellForm.MIND, SpellForm.INFORMATION}),
    },
)

P = ProductPart
YIELD_PARTS: Mapping[YieldProduct, ProductPart] = total(
    YieldProduct,
    {
        YieldProduct.MEAT: P.FLESH,
        YieldProduct.HIDE: P.HIDE,
        YieldProduct.CALCIFIED_TISSUE: P.BONE,
        YieldProduct.IVORY: P.TUSK,
        YieldProduct.CHITIN: P.SHELL,
        YieldProduct.VENOM: P.VENOM,
        YieldProduct.SILK: P.FIBRE,
        YieldProduct.WOOL: P.FIBRE,
        YieldProduct.MILK: P.MILK,
        YieldProduct.FEATHERS: P.FEATHERS,
        YieldProduct.MAGIC_REAGENTS: P.REAGENT,
        YieldProduct.GREAT_BEAST_TISSUE: P.BONE,
        YieldProduct.EGGS: P.EGGS,
        YieldProduct.BLOOD: P.FLESH,
        YieldProduct.ORGANS: P.FLESH,
        YieldProduct.FAT: P.OIL,
        YieldProduct.SCENT: P.REAGENT,
        YieldProduct.HONEY: P.SUGAR,
        YieldProduct.WAX: P.RESIN,
        YieldProduct.SHELL: P.SHELL,
        YieldProduct.SCALES: P.HIDE,
    },
)
PLANT_PARTS: Mapping[PlantYield, ProductPart] = total(
    PlantYield,
    {
        PlantYield.GRAIN: P.SEED,
        PlantYield.TUBER: P.ROOT,
        PlantYield.FIBRE: P.FIBRE,
        PlantYield.DYE: P.DYE,
        PlantYield.TIMBER: P.WOOD,
        PlantYield.FRUIT: P.FRUIT,
        PlantYield.HERB: P.LEAF,
        PlantYield.BREW_BASE: P.SEED,
        PlantYield.REAGENT: P.REAGENT,
        PlantYield.POISON: P.TOXIN,
        PlantYield.OIL: P.OIL,
        PlantYield.SUGAR: P.SUGAR,
        PlantYield.SPICE: P.SPICE,
        PlantYield.RESIN: P.RESIN,
        PlantYield.STIMULANT: P.STIMULANT,
        PlantYield.FODDER: P.FODDER,
        PlantYield.MEDICINE: P.LEAF,
        PlantYield.BUILDING: P.WOOD,
        PlantYield.FUEL: P.WOOD,
    },
)
PRODUCT_PARTS: Mapping[str, ProductPart] = {
    **{product.value: part for product, part in YIELD_PARTS.items()},
    **{product.value: part for product, part in PLANT_PARTS.items()},
}

SOURCE_NODES: Mapping[MaterialSource, frozenset[NodeKind]] = total(
    MaterialSource,
    {
        MaterialSource.WORLD: frozenset({NodeKind.WORLD}),
        MaterialSource.GOD: frozenset({NodeKind.SON, NodeKind.FOREIGN_GOD, NodeKind.CREATOR, NodeKind.ENTITY}),
        MaterialSource.STAR: frozenset({NodeKind.STAR}),
        MaterialSource.CREATURE: frozenset({NodeKind.ENTITY}),
        MaterialSource.RIFT: frozenset({NodeKind.ENTITY, NodeKind.DIMENSION}),
        MaterialSource.MAKERS: frozenset({NodeKind.ENTITY}),
    },
)
