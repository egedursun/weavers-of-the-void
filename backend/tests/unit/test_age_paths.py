from aerona.catalog.eras import TECHNIQUE_ERAS
from aerona.catalog.methods import METHOD_RECIPES, METHODS, PROCESS_METHODS
from aerona.catalog.production import RECIPES, ChainStep
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.world import TechnologyEra
from aerona.engine.eras.effects import era_order
from aerona.engine.industry.methods import method_era

MODERN_FROM = TechnologyEra.STEAM
TIMELESS = frozenset({CommodityKind.MOUNTS})


def recipe_era(step: ChainStep) -> TechnologyEra:
    era = TECHNIQUE_ERAS.get(step.technique) if step.technique is not None else None
    return era or TechnologyEra.STONE


def modern(era: TechnologyEra) -> bool:
    return era_order(era) >= era_order(MODERN_FROM)


def fitted_by_a_modern_method(step: ChainStep) -> bool:
    return any(modern(method_era(METHODS[kind])) for kind, recipes in METHOD_RECIPES.items() if step.key in recipes)


def test_every_process_has_a_way_of_working_for_a_modern_world() -> None:
    missing = [process.value for process, methods in PROCESS_METHODS.items() if methods and not any(modern(method_era(spec)) for spec in methods)]
    assert missing == []


def test_every_good_a_recipe_makes_has_a_modern_way_to_make_it() -> None:
    missing = [
        good.value
        for good, steps in RECIPES.items()
        if steps and good not in TIMELESS and not any(modern(recipe_era(step)) or fitted_by_a_modern_method(step) for step in steps)
    ]
    assert missing == []
