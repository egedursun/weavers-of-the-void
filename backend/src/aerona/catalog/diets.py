from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.ecology import Diet
from aerona.domain.enums.folkways import Nutrient

N = Nutrient


@dataclass(frozen=True)
class DietSpec:
    hunts: bool
    grazes: bool
    eats_meat: bool
    seeks_flesh: bool
    edible: bool
    yields_meat: bool
    forages: bool
    produces: bool
    needs: tuple[Nutrient, ...]
    text: str


DIETS: Mapping[Diet, DietSpec] = total(
    Diet,
    {
        Diet.HERBIVORE: DietSpec(False, True, False, False, True, True, True, False, (N.ENERGY, N.FRESH, N.MINERAL), "grazes on forest and soil"),
        Diet.CARNIVORE: DietSpec(True, False, True, True, True, True, False, False, (N.ENERGY, N.PROTEIN, N.FAT, N.MINERAL), "lives on the prey of its land"),
        Diet.OMNIVORE: DietSpec(True, True, True, True, True, True, False, False, (N.ENERGY, N.PROTEIN, N.FAT, N.FRESH, N.MINERAL), "grazes and hunts alike"),
        Diet.SCAVENGER: DietSpec(False, False, False, True, True, True, False, False, (N.ENERGY, N.PROTEIN, N.MINERAL), "lives on what others leave"),
        Diet.FILTER: DietSpec(False, True, False, False, True, True, True, False, (N.ENERGY, N.PROTEIN, N.MINERAL), "sifts the waters for its food"),
        Diet.PHOTOSYNTHETIC: DietSpec(
            False, False, False, False, True, False, False, True, (N.ENERGY, N.LIGHT, N.MINERAL), "lives on light and yields no meat"
        ),
        Diet.MINERAL: DietSpec(False, False, False, False, False, False, False, True, (N.ENERGY, N.MINERAL), "eats stone and ore and cannot be eaten"),
        Diet.SOUL: DietSpec(True, False, False, False, True, True, False, False, (N.ENERGY, N.ESSENCE), "feeds on souls"),
        Diet.VOID: DietSpec(False, False, False, False, False, False, False, False, (N.ENERGY, N.ESSENCE), "feeds on the void and cannot be eaten"),
        Diet.PISCIVORE: DietSpec(
            False, False, False, False, True, True, False, False, (N.ENERGY, N.PROTEIN, N.FAT, N.MINERAL), "lives on the fish of its waters"
        ),
        Diet.SANGUIVORE: DietSpec(False, False, False, False, True, True, False, False, (N.ENERGY, N.PROTEIN), "lives on the blood of other creatures"),
    },
)

HUNTERS = frozenset(diet for diet, spec in DIETS.items() if spec.hunts)
GRAZERS = frozenset(diet for diet, spec in DIETS.items() if spec.grazes)
MEAT_EATERS = frozenset(diet for diet, spec in DIETS.items() if spec.eats_meat)
FLESH_SEEKERS = frozenset(diet for diet, spec in DIETS.items() if spec.seeks_flesh)
INEDIBLE = frozenset(diet for diet, spec in DIETS.items() if not spec.edible)
MEATLESS = frozenset(diet for diet, spec in DIETS.items() if not spec.yields_meat)
FORAGERS = frozenset(diet for diet, spec in DIETS.items() if spec.forages)
PRODUCERS = frozenset(diet for diet, spec in DIETS.items() if spec.produces)
