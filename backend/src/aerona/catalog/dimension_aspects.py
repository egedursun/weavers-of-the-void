from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.arcana import SpellForm
from aerona.domain.enums.cosmography import DimensionElement, DimensionKind


@dataclass(frozen=True)
class Pull:
    field: str
    sign: int


ELEMENT_PULLS: Mapping[DimensionElement, Pull] = total(
    DimensionElement,
    {
        DimensionElement.FIRE: Pull("hostility", 1),
        DimensionElement.WATER: Pull("stability", 1),
        DimensionElement.EARTH: Pull("stability", 1),
        DimensionElement.AIR: Pull("veil", -1),
        DimensionElement.VOID: Pull("leak", 1),
        DimensionElement.LIGHT: Pull("veil", 1),
        DimensionElement.SHADOW: Pull("veil", -1),
        DimensionElement.ICE: Pull("time_factor", -1),
        DimensionElement.LIGHTNING: Pull("magic", 1),
        DimensionElement.METAL: Pull("hostility", 1),
        DimensionElement.WOOD: Pull("magic", 1),
    },
)
FORM_PULLS: Mapping[SpellForm, Pull] = total(
    SpellForm,
    {
        SpellForm.FIRE: Pull("hostility", 1),
        SpellForm.WATER: Pull("stability", 1),
        SpellForm.AIR: Pull("veil", -1),
        SpellForm.EARTH: Pull("stability", 1),
        SpellForm.PLANT: Pull("magic", 1),
        SpellForm.ANIMAL: Pull("hostility", 1),
        SpellForm.BODY: Pull("stability", 1),
        SpellForm.MIND: Pull("sanity_drain", 1),
        SpellForm.IMAGE: Pull("veil", -1),
        SpellForm.SPIRIT: Pull("veil", -1),
        SpellForm.TIME: Pull("time_factor", 1),
        SpellForm.VOID: Pull("leak", 1),
        SpellForm.DEATH: Pull("hostility", 1),
        SpellForm.LIGHT: Pull("veil", 1),
        SpellForm.SPACE: Pull("stability", -1),
        SpellForm.FORCE: Pull("hostility", 1),
        SpellForm.SOUND: Pull("sanity_drain", 1),
        SpellForm.EMOTION: Pull("sanity_drain", 1),
        SpellForm.FATE: Pull("stability", 1),
        SpellForm.MACHINE: Pull("stability", 1),
        SpellForm.INFORMATION: Pull("magic", 1),
        SpellForm.DREAM: Pull("veil", -1),
        SpellForm.LAW: Pull("stability", 1),
    },
)
KIND_FORMS: Mapping[DimensionKind, tuple[SpellForm, ...]] = total(
    DimensionKind,
    {
        DimensionKind.PRIME: (),
        DimensionKind.PARALLEL: (SpellForm.FATE,),
        DimensionKind.MIRROR: (SpellForm.IMAGE,),
        DimensionKind.POCKET: (SpellForm.SPACE,),
        DimensionKind.BUBBLE_UNIVERSE: (SpellForm.SPACE,),
        DimensionKind.BRANE: (SpellForm.FORCE,),
        DimensionKind.HIGHER_DIMENSIONAL: (SpellForm.SPACE, SpellForm.INFORMATION),
        DimensionKind.ANTIMATTER: (SpellForm.FORCE,),
        DimensionKind.QUANTUM_BRANCH: (SpellForm.FATE,),
        DimensionKind.TIME_REVERSED: (SpellForm.TIME,),
        DimensionKind.COMPACTIFIED: (SpellForm.SPACE,),
        DimensionKind.ASTRAL: (SpellForm.MIND, SpellForm.SPIRIT),
        DimensionKind.ETHEREAL: (SpellForm.SPIRIT,),
        DimensionKind.DREAM: (SpellForm.MIND, SpellForm.IMAGE),
        DimensionKind.MADE: (SpellForm.INFORMATION, SpellForm.MACHINE),
        DimensionKind.SHADOW: (SpellForm.IMAGE,),
        DimensionKind.SPIRIT: (SpellForm.SPIRIT,),
        DimensionKind.FEY: (SpellForm.EMOTION, SpellForm.PLANT),
        DimensionKind.ELEMENTAL: (),
        DimensionKind.CELESTIAL: (SpellForm.LIGHT,),
        DimensionKind.INFERNAL: (SpellForm.FIRE, SpellForm.EMOTION),
        DimensionKind.ABYSSAL: (SpellForm.VOID,),
        DimensionKind.LIMBO: (SpellForm.TIME,),
        DimensionKind.FAR_REALM: (SpellForm.VOID, SpellForm.MIND),
        DimensionKind.CLOCKWORK: (SpellForm.MACHINE,),
        DimensionKind.CHAOS: (SpellForm.FATE, SpellForm.FORCE),
        DimensionKind.UNDERWORLD: (SpellForm.DEATH,),
        DimensionKind.DIVINE_DOMAIN: (SpellForm.SPIRIT,),
        DimensionKind.VOID_BETWEEN: (SpellForm.VOID,),
    },
)
PERCENT_FIELDS = frozenset({"veil", "stability", "magic", "hostility", "leak"})
