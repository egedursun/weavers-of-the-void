from aerona.catalog.eras import TECHNIQUE_ERAS
from aerona.catalog.methods import METHOD_RECIPES, METHODS, PROCESS_METHODS, STEP_PROCESS, MethodSpec
from aerona.catalog.production import CHAIN_STEPS, STEPS, ChainStep
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.industry import EnergyKind, MethodKind, ProcessKind
from aerona.domain.enums.world import TechnologyEra
from aerona.engine.eras.effects import era_order
from aerona.engine.industry.methods import fits, method_era

MODERN_FROM = TechnologyEra.STEAM
UNBOUND = frozenset({EnergyKind.MAGIC, EnergyKind.DIVINE, EnergyKind.VOID, EnergyKind.SOURCE, EnergyKind.BELIEF, EnergyKind.FEED})


def recipe_modern(step: ChainStep) -> bool:
    era = TECHNIQUE_ERAS.get(step.technique) if step.technique is not None else None
    return era is not None and era_order(era) >= era_order(MODERN_FROM)


def method_modern(spec: MethodSpec) -> bool:
    return era_order(method_era(spec)) >= era_order(MODERN_FROM)


def recipes_in(process: ProcessKind) -> list[ChainStep]:
    return [step for step in CHAIN_STEPS if STEP_PROCESS.get(step.key) is process]


def applied() -> list[tuple[MethodSpec, ChainStep]]:
    return [(spec, step) for spec in METHODS.values() for step in recipes_in(spec.process) if fits(spec, step.key)]


def test_every_method_names_only_recipes_of_its_own_process() -> None:
    assert set(STEP_PROCESS) <= set(STEPS)
    assert set(METHOD_RECIPES) == set(METHODS)
    for kind, keys in METHOD_RECIPES.items():
        assert all(STEP_PROCESS[key] is METHODS[kind].process for key in keys), kind


def test_a_method_multiplies_only_recipes_of_its_own_age() -> None:
    for spec, step in applied():
        if spec.energy in UNBOUND:
            continue
        ages = {recipe_modern(other) for other in recipes_in(spec.process)}
        assert len(ages) == 1 or method_modern(spec) == recipe_modern(step), f"{spec.kind.value} on {step.key}"


def test_a_method_works_only_on_inputs_it_can_take() -> None:
    for spec, step in applied():
        inputs = {commodity for commodity, _ in step.inputs}
        mixed = len({recipe_modern(other) for other in recipes_in(spec.process)}) > 1
        if mixed and method_modern(spec) and spec.energy not in UNBOUND:
            assert not inputs & {CommodityKind.TIMBER, CommodityKind.LIVESTOCK}, f"{spec.kind.value} on {step.key}"
        if step.technique is not None and spec.technique is None and spec.energy not in UNBOUND:
            assert not recipe_modern(step), f"{spec.kind.value} on {step.key}"


def test_every_recipe_with_a_process_has_a_method_of_its_age_and_every_method_a_recipe() -> None:
    fitted = {(spec.kind, step.key) for spec, step in applied()}
    for process in {STEP_PROCESS[key] for key in STEP_PROCESS}:
        for step in recipes_in(process):
            assert any((spec.kind, step.key) in fitted for spec in PROCESS_METHODS[process] if spec.energy not in UNBOUND), step.key
        assert all(METHOD_RECIPES[spec.kind] for spec in PROCESS_METHODS[process]), process


def test_oil_refining_makes_fuel_from_coal_and_crops_never_from_timber() -> None:
    oil = METHODS[MethodKind.OIL_REFINING]
    assert {key for key in STEPS if fits(oil, key)} == {"coke_fuel", "coal_fuel", "crop_fuel"}
    assert {key for key in STEPS if fits(METHODS[MethodKind.CLAMP_KILN], key)} == {"charcoal"}
    assert not fits(METHODS[MethodKind.HAND_LOOM], "synthetic_cloth") and fits(METHODS[MethodKind.ELECTRIC_LOOM], "synthetic_cloth")
    assert not fits(METHODS[MethodKind.BLOOMERY], "electric_tools") and not fits(METHODS[MethodKind.ELECTRIC_ARC], "forge_tools")
    assert not fits(METHODS[MethodKind.ROLLER_MILL], "mill") and not fits(METHODS[MethodKind.HERBAL_STILL], "pharmacy")
