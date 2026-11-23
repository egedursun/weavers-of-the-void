from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.biology import BiologyVariant
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.demography import NaturalTrait
from aerona.domain.enums.ecology import Biochemistry, Diet, Sociality, SpeciesClass, TissueMaterial
from aerona.domain.enums.folkways import DecisionBias

V = BiologyVariant
B = DecisionBias


@dataclass(frozen=True)
class BiologySpec:
    food_need_pct: int = 100
    fertility_pct: int = 100
    death_pct: int = 100
    disease_pct: int = 100
    morale_loss_pct: int = 100
    fire_harm_pct: int = 100
    storm_harm_pct: int = 100
    breathes: bool = True
    drinks: bool = True
    ages: bool = True
    sleeps: bool = True
    bleeds: bool = True
    heals: bool = True
    infects: bool = True
    material: bool = True
    tissue: TissueMaterial | None = None
    shifts: Mapping[DecisionBias, int] = field(default_factory=dict)
    damped: frozenset[DecisionBias] = frozenset()
    skyless: bool = False
    burns: bool = False
    buds: bool = False
    needs_source: bool = False
    needs_partner: bool = False


BIOLOGY_VARIANTS: Mapping[BiologyVariant, BiologySpec] = total(
    V,
    {
        V.INCORPOREAL: BiologySpec(
            food_need_pct=0,
            fertility_pct=40,
            death_pct=60,
            disease_pct=0,
            fire_harm_pct=50,
            breathes=False,
            drinks=False,
            ages=False,
            sleeps=False,
            bleeds=False,
            infects=False,
            material=False,
        ),
        V.AQUATIC: BiologySpec(fertility_pct=140, death_pct=110, disease_pct=120, storm_harm_pct=80, drinks=False, skyless=True),
        V.AERIAL: BiologySpec(food_need_pct=130, fertility_pct=90, storm_harm_pct=150),
        V.SUBTERRANEAN: BiologySpec(food_need_pct=80, disease_pct=110, storm_harm_pct=40, skyless=True),
        V.HIVE: BiologySpec(
            fertility_pct=160,
            death_pct=120,
            disease_pct=130,
            morale_loss_pct=50,
            shifts={B.GROUPTHINK: 50, B.COLONY_RISK_AVERSION: 40},
            damped=frozenset({B.OVERCONFIDENCE}),
        ),
        V.PLANT_LIKE: BiologySpec(food_need_pct=40, death_pct=70, disease_pct=110, fire_harm_pct=200, bleeds=False, tissue=TissueMaterial.FIBROUS),
        V.CONSTRUCT: BiologySpec(
            food_need_pct=0,
            fertility_pct=30,
            death_pct=50,
            disease_pct=0,
            morale_loss_pct=0,
            breathes=False,
            drinks=False,
            ages=False,
            sleeps=False,
            bleeds=False,
            heals=False,
            infects=False,
            shifts={B.LITERALISM: 40},
            damped=frozenset({B.LOSS_AVERSION, B.HOSTILE_ATTRIBUTION, B.OPTIMISM, B.FATALISM, B.SCARCITY_PANIC}),
        ),
        V.AGELESS: BiologySpec(fertility_pct=25, death_pct=30, ages=False, shifts={B.SUNK_COST: 20, B.HOSTILE_ATTRIBUTION: 15, B.RECENCY: -20}),
        V.SHAPESHIFTING: BiologySpec(disease_pct=90),
        V.GASEOUS: BiologySpec(
            food_need_pct=30,
            fertility_pct=80,
            disease_pct=60,
            fire_harm_pct=120,
            storm_harm_pct=200,
            drinks=False,
            bleeds=False,
            material=False,
        ),
        V.CRYSTALLINE: BiologySpec(
            food_need_pct=60,
            fertility_pct=60,
            death_pct=60,
            disease_pct=50,
            fire_harm_pct=70,
            storm_harm_pct=120,
            breathes=False,
            drinks=False,
            bleeds=False,
            infects=False,
            tissue=TissueMaterial.CRYSTALLINE,
        ),
        V.UNDEAD: BiologySpec(
            food_need_pct=0,
            fertility_pct=0,
            death_pct=40,
            disease_pct=0,
            morale_loss_pct=0,
            fire_harm_pct=150,
            breathes=False,
            drinks=False,
            ages=False,
            sleeps=False,
            bleeds=False,
            heals=False,
            infects=False,
            shifts={B.LITERALISM: 20, B.AUTHORITY_DEFERENCE: 20},
        ),
        V.FUNGAL: BiologySpec(food_need_pct=60, fertility_pct=150, death_pct=90, disease_pct=80, storm_harm_pct=60, skyless=True, burns=True),
        V.COLONIAL: BiologySpec(fertility_pct=60, death_pct=70, morale_loss_pct=60, buds=True, shifts={B.GROUPTHINK: 40}),
        V.ENERGY: BiologySpec(
            food_need_pct=0,
            fertility_pct=50,
            death_pct=60,
            disease_pct=0,
            fire_harm_pct=0,
            breathes=False,
            drinks=False,
            bleeds=False,
            infects=False,
            material=False,
            needs_source=True,
        ),
        V.SYMBIOTIC: BiologySpec(food_need_pct=80, fertility_pct=90, disease_pct=110, needs_partner=True, shifts={B.LOSS_AVERSION: 20}),
    },
)
SKYLESS_VARIANTS = frozenset(variant for variant, spec in BIOLOGY_VARIANTS.items() if spec.skyless)
BURNING_VARIANTS = frozenset(variant for variant, spec in BIOLOGY_VARIANTS.items() if spec.burns)

PLAN_VARIANTS: MappingProxyType[BodyPlan, BiologyVariant] = MappingProxyType(
    {
        BodyPlan.INCORPOREAL: V.INCORPOREAL,
        BodyPlan.CONSTRUCT: V.CONSTRUCT,
        BodyPlan.AQUATIC: V.AQUATIC,
        BodyPlan.AVIAN: V.AERIAL,
        BodyPlan.COLONIAL: V.COLONIAL,
    }
)
CHEMISTRY_VARIANTS: MappingProxyType[Biochemistry, BiologyVariant] = MappingProxyType(
    {
        Biochemistry.CRYSTAL: V.CRYSTALLINE,
        Biochemistry.SPIRIT: V.INCORPOREAL,
        Biochemistry.PLASMA: V.ENERGY,
    }
)
TRAIT_VARIANTS: MappingProxyType[NaturalTrait, BiologyVariant] = MappingProxyType(
    {
        NaturalTrait.WINGED: V.AERIAL,
        NaturalTrait.BURROWING: V.SUBTERRANEAN,
        NaturalTrait.HIVE_MINDED: V.HIVE,
    }
)
FOLK_DIET_VARIANTS: MappingProxyType[Diet, BiologyVariant] = MappingProxyType(
    {Diet.PHOTOSYNTHETIC: V.PLANT_LIKE, Diet.DECOMPOSER: V.FUNGAL, Diet.ENERGY: V.ENERGY}
)
SPECIES_DIET_VARIANTS: MappingProxyType[Diet, BiologyVariant] = MappingProxyType(
    {Diet.PHOTOSYNTHETIC: V.PLANT_LIKE, Diet.DECOMPOSER: V.FUNGAL, Diet.ENERGY: V.ENERGY}
)
SOCIALITY_VARIANTS: MappingProxyType[Sociality, BiologyVariant] = MappingProxyType({Sociality.HIVE: V.HIVE})
CLASS_VARIANTS: MappingProxyType[SpeciesClass, BiologyVariant] = MappingProxyType(
    {SpeciesClass.FUNGUS: V.FUNGAL, SpeciesClass.COLONIAL: V.COLONIAL, SpeciesClass.ENERGY: V.ENERGY}
)
