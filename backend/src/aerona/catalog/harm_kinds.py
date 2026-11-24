from collections.abc import Callable, Mapping
from dataclasses import dataclass

from aerona.catalog.anatomy import Part
from aerona.catalog.kinds.harm import HARM_CAUSES
from aerona.core.total import total
from aerona.domain.enums.body import BodyFunction, BodyRegion, DamageType, HarmCause, InjuryKind, TreatmentStep
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.records import StepAction
from aerona.rules.registry.body import HealingRules, InjuryRules
from aerona.rules.registry.tissues import TissueRules

D = DamageType
K = InjuryKind
S = TreatmentStep
KindRule = Callable[[InjuryRules, Part, int, HarmCause], InjuryKind]
Healing = Callable[[HealingRules], int]
DRESSED = (S.CLEAN, S.DRESS)
SET = (S.SET_BONE, S.SPLINT)
JOINTED = frozenset({BodyRegion.ARMS, BodyRegion.LEGS, BodyRegion.WINGS})


def sees(part: Part) -> bool:
    return BodyFunction.SIGHT in part.functions


def small(part: Part) -> bool:
    return part.severable and (part.counted > 0 or part.region in {BodyRegion.HEAD, BodyRegion.TAIL})


def cut_wound(rules: InjuryRules, part: Part, severity: int, cause: HarmCause) -> InjuryKind:
    sever_at = rules.cut_sever_small_at if small(part) else rules.cut_sever_at
    if part.severable and severity >= sever_at:
        return K.SEVERED
    return K.DEEP_CUT if severity >= rules.cut_deep_at else K.CUT


def pierce_wound(rules: InjuryRules, part: Part, severity: int, cause: HarmCause) -> InjuryKind:
    if sees(part) and severity >= rules.pierce_gouge_at:
        return K.GOUGED
    if part.vital and severity >= rules.pierce_destroy_at:
        return K.DESTROYED
    return HARM_CAUSES[cause].pierce


def blunt_wound(rules: InjuryRules, part: Part, severity: int, cause: HarmCause) -> InjuryKind:
    if part.internal and severity >= rules.blunt_fracture_at:
        return K.INTERNAL_BLEEDING
    if part.severable and part.region in JOINTED and severity == rules.blunt_fracture_at - 1:
        return K.DISLOCATION
    if severity >= rules.blunt_crush_at:
        return K.CRUSH
    return K.FRACTURE if severity >= rules.blunt_fracture_at else K.BRUISE


def fire_wound(rules: InjuryRules, part: Part, severity: int, cause: HarmCause) -> InjuryKind:
    return K.DESTROYED if sees(part) and severity >= rules.fire_blind_at else K.BURN


def cold_wound(rules: InjuryRules, part: Part, severity: int, cause: HarmCause) -> InjuryKind:
    return K.SEVERED if part.severable and severity >= rules.cold_loss_at else K.FROSTBITE


def magic_wound(rules: InjuryRules, part: Part, severity: int, cause: HarmCause) -> InjuryKind:
    return K.CURSE_WITHER if severity >= rules.magic_wither_at else K.BURN


def ballistic_wound(rules: InjuryRules, part: Part, severity: int, cause: HarmCause) -> InjuryKind:
    if sees(part) and severity >= rules.pierce_gouge_at:
        return K.GOUGED
    if part.vital and severity >= rules.pierce_destroy_at:
        return K.DESTROYED
    return K.GUNSHOT


def blast_wound(rules: InjuryRules, part: Part, severity: int, cause: HarmCause) -> InjuryKind:
    if part.severable and severity >= rules.blast_sever_at:
        return K.SEVERED
    if part.region is BodyRegion.HEAD and severity >= rules.blast_concussion_at:
        return K.CONCUSSION
    return K.SHRAPNEL


def energy_wound(rules: InjuryRules, part: Part, severity: int, cause: HarmCause) -> InjuryKind:
    if (sees(part) and severity >= rules.fire_blind_at) or (part.vital and severity >= rules.pierce_destroy_at):
        return K.DESTROYED
    return K.BURN


def chemical_wound(rules: InjuryRules, part: Part, severity: int, cause: HarmCause) -> InjuryKind:
    return K.DESTROYED if sees(part) and severity >= rules.fire_blind_at else K.CHEMICAL_BURN


def asphyxia_wound(rules: InjuryRules, part: Part, severity: int, cause: HarmCause) -> InjuryKind:
    return K.DESTROYED if part.vital and severity >= rules.blunt_crush_at else K.ASPHYXIA


def always(kind: InjuryKind) -> KindRule:
    return lambda rules, part, severity, cause: kind


@dataclass(frozen=True)
class DamageSpec:
    wound: KindRule
    physical: bool = False
    deep: bool = False
    bodily: bool = False
    edged: bool = False
    striking: bool = False
    breathing: bool = False
    searing: bool = False
    thermal: bool = False
    spared: InjuryKind | None = None
    blow: StepAction | None = None


@dataclass(frozen=True)
class InjurySpec:
    permanent: bool = False
    mark: bool = False
    total_loss: bool = False
    clean_healing: bool = False
    of_the_mind: bool = False
    care: tuple[TreatmentStep, ...] = ()
    broken: bool = False
    cut_away: bool = False
    blinding: bool = False
    lost_word: str | None = None
    infection: Healing | None = None
    lasting: Healing | None = None
    healing: Healing | None = None
    noted: bool = False


@dataclass(frozen=True)
class StepSpec:
    action: StepAction
    supply: CommodityKind | None = None
    level: Callable[[TissueRules], int] | None = None
    stanches: bool = False
    noted: bool = False
    festering: bool = False


DAMAGE: Mapping[DamageType, DamageSpec] = total(
    DamageType,
    {
        D.CUT: DamageSpec(cut_wound, physical=True, bodily=True, edged=True, striking=True, blow=StepAction.CUT),
        D.PIERCE: DamageSpec(pierce_wound, physical=True, deep=True, bodily=True, edged=True, striking=True, spared=K.PUNCTURE, blow=StepAction.THRUST),
        D.BLUNT: DamageSpec(blunt_wound, physical=True, deep=True, bodily=True, striking=True),
        D.FIRE: DamageSpec(fire_wound, physical=True, searing=True, thermal=True, spared=K.BURN),
        D.COLD: DamageSpec(cold_wound, bodily=True, searing=True, thermal=True),
        D.VENOM: DamageSpec(always(K.VENOM), deep=True, bodily=True),
        D.MAGIC: DamageSpec(magic_wound),
        D.VOID: DamageSpec(always(K.VOID_TOUCH)),
        D.HOLY: DamageSpec(always(K.DIVINE_BRAND)),
        D.BALLISTIC: DamageSpec(ballistic_wound, physical=True, deep=True, bodily=True, edged=True, striking=True, spared=K.GUNSHOT),
        D.EXPLOSIVE: DamageSpec(blast_wound, physical=True, deep=True, bodily=True, striking=True, spared=K.SHRAPNEL),
        D.ENERGY: DamageSpec(energy_wound, searing=True, spared=K.BURN),
        D.ELECTRIC: DamageSpec(always(K.ELECTRICAL_BURN), searing=True),
        D.RADIATION: DamageSpec(always(K.RADIATION_SICKNESS)),
        D.CHEMICAL: DamageSpec(chemical_wound, bodily=True, searing=True, spared=K.CHEMICAL_BURN),
        D.SONIC: DamageSpec(always(K.CONCUSSION), striking=True),
        D.PSYCHIC: DamageSpec(always(K.MIND_SCAR)),
        D.ASPHYXIA: DamageSpec(asphyxia_wound, bodily=True, breathing=True),
        D.SOUL: DamageSpec(always(K.MIND_SCAR)),
        D.PRESSURE: DamageSpec(always(K.PRESSURE_INJURY), bodily=True, breathing=True, deep=True),
    },
)

INJURIES: Mapping[InjuryKind, InjurySpec] = total(
    InjuryKind,
    {
        K.BRUISE: InjurySpec(clean_healing=True, healing=lambda rules: rules.heal_bruise_pct),
        K.CUT: InjurySpec(care=DRESSED, infection=lambda rules: rules.infection_cut, healing=lambda rules: rules.heal_cut_pct),
        K.DEEP_CUT: InjurySpec(
            care=DRESSED,
            infection=lambda rules: rules.infection_deep_cut,
            lasting=lambda rules: rules.permanent_deep_cut,
            healing=lambda rules: rules.heal_deep_cut_pct,
        ),
        K.PUNCTURE: InjurySpec(care=DRESSED, infection=lambda rules: rules.infection_puncture, healing=lambda rules: rules.heal_puncture_pct),
        K.FRACTURE: InjurySpec(broken=True, care=SET, lasting=lambda rules: rules.permanent_fracture, healing=lambda rules: rules.heal_fracture_pct),
        K.CRUSH: InjurySpec(
            broken=True,
            care=SET,
            infection=lambda rules: rules.infection_crush,
            lasting=lambda rules: rules.permanent_crush,
            healing=lambda rules: rules.heal_crush_pct,
        ),
        K.BURN: InjurySpec(
            care=DRESSED,
            infection=lambda rules: rules.infection_burn,
            lasting=lambda rules: rules.permanent_burn,
            healing=lambda rules: rules.heal_burn_pct,
        ),
        K.FROSTBITE: InjurySpec(
            infection=lambda rules: rules.infection_frostbite,
            lasting=lambda rules: rules.permanent_frostbite,
            healing=lambda rules: rules.heal_frostbite_pct,
        ),
        K.BITE: InjurySpec(care=DRESSED, infection=lambda rules: rules.infection_bite, healing=lambda rules: rules.heal_bite_pct),
        K.VENOM: InjurySpec(clean_healing=True, lasting=lambda rules: rules.permanent_venom, healing=lambda rules: rules.heal_venom_pct),
        K.SEVERED: InjurySpec(permanent=True, total_loss=True, cut_away=True, lost_word="lost", infection=lambda rules: rules.infection_severed),
        K.GOUGED: InjurySpec(
            permanent=True, total_loss=True, cut_away=True, blinding=True, lost_word="gouged out", infection=lambda rules: rules.infection_gouged
        ),
        K.DESTROYED: InjurySpec(permanent=True, total_loss=True, blinding=True, lost_word="ruined"),
        K.CURSE_WITHER: InjurySpec(lasting=lambda rules: rules.permanent_wither, healing=lambda rules: rules.heal_curse_wither_pct),
        K.VOID_TOUCH: InjurySpec(permanent=True, mark=True, of_the_mind=True),
        K.DIVINE_BRAND: InjurySpec(permanent=True, mark=True),
        K.SICKNESS: InjurySpec(clean_healing=True),
        K.ASPHYXIA: InjurySpec(noted=True, clean_healing=True, of_the_mind=True, healing=lambda rules: rules.heal_bruise_pct),
        K.DISLOCATION: InjurySpec(noted=True, care=SET, healing=lambda rules: rules.heal_cut_pct),
        K.INTERNAL_BLEEDING: InjurySpec(noted=True, care=DRESSED, lasting=lambda rules: rules.permanent_crush, healing=lambda rules: rules.heal_puncture_pct),
        K.GUNSHOT: InjurySpec(
            care=DRESSED,
            infection=lambda rules: rules.infection_gunshot,
            lasting=lambda rules: rules.permanent_gunshot,
            healing=lambda rules: rules.heal_gunshot_pct,
        ),
        K.SHRAPNEL: InjurySpec(
            care=DRESSED,
            infection=lambda rules: rules.infection_shrapnel,
            lasting=lambda rules: rules.permanent_shrapnel,
            healing=lambda rules: rules.heal_shrapnel_pct,
        ),
        K.CONCUSSION: InjurySpec(
            clean_healing=True, of_the_mind=True, lasting=lambda rules: rules.permanent_concussion, healing=lambda rules: rules.heal_concussion_pct
        ),
        K.ELECTRICAL_BURN: InjurySpec(
            care=DRESSED, lasting=lambda rules: rules.permanent_electrical_burn, healing=lambda rules: rules.heal_electrical_burn_pct
        ),
        K.CHEMICAL_BURN: InjurySpec(
            care=DRESSED,
            infection=lambda rules: rules.infection_chemical_burn,
            lasting=lambda rules: rules.permanent_burn,
            healing=lambda rules: rules.heal_chemical_burn_pct,
        ),
        K.RADIATION_SICKNESS: InjurySpec(clean_healing=True, lasting=lambda rules: rules.permanent_radiation, healing=lambda rules: rules.heal_radiation_pct),
        K.MIND_SCAR: InjurySpec(of_the_mind=True, lasting=lambda rules: rules.permanent_mind_scar, healing=lambda rules: rules.heal_mind_scar_pct),
        K.SPRAIN: InjurySpec(clean_healing=True, care=(S.REST, S.SPLINT), healing=lambda rules: rules.heal_cut_pct),
        K.TORN_TENDON: InjurySpec(care=(S.REST, S.SPLINT), lasting=lambda rules: rules.permanent_crush, healing=lambda rules: rules.heal_puncture_pct),
        K.PRESSURE_INJURY: InjurySpec(
            noted=True, care=(S.REST,), lasting=lambda rules: rules.permanent_concussion, healing=lambda rules: rules.heal_concussion_pct
        ),
    },
)

STEPS: Mapping[TreatmentStep, StepSpec] = total(
    TreatmentStep,
    {
        S.DIAGNOSE: StepSpec(StepAction.EXAMINE),
        S.CLEAN: StepSpec(StepAction.TREAT, supply=CommodityKind.MEDICINE),
        S.SUTURE: StepSpec(StepAction.SUTURE, supply=CommodityKind.CLOTH, level=lambda rules: rules.suture_level, stanches=True),
        S.SET_BONE: StepSpec(StepAction.SET_BONE, level=lambda rules: rules.set_bone_level),
        S.SPLINT: StepSpec(StepAction.TREAT, supply=CommodityKind.TIMBER, level=lambda rules: rules.set_bone_level),
        S.DRESS: StepSpec(StepAction.TREAT, supply=CommodityKind.CLOTH),
        S.AMPUTATE: StepSpec(StepAction.AMPUTATE, level=lambda rules: rules.amputate_level),
        S.CAUTERISE: StepSpec(StepAction.TREAT, level=lambda rules: rules.cauterise_level, stanches=True),
        S.CRUTCH: StepSpec(StepAction.TREAT, supply=CommodityKind.TIMBER),
        S.TRACTION: StepSpec(StepAction.TREAT, level=lambda rules: rules.traction_level),
        S.DRAIN: StepSpec(StepAction.TREAT, supply=CommodityKind.CLOTH, level=lambda rules: rules.cauterise_level, noted=True, festering=True),
        S.BLEED: StepSpec(StepAction.TREAT, noted=True),
        S.MEDICATE: StepSpec(StepAction.TREAT, supply=CommodityKind.MEDICINE, noted=True, festering=True),
        S.TRANSFUSE: StepSpec(StepAction.TREAT, level=lambda rules: rules.transfuse_level, stanches=True, noted=True),
        S.REST: StepSpec(StepAction.TREAT),
    },
)


def damage_where(test: Callable[[DamageSpec], bool]) -> frozenset[DamageType]:
    return frozenset(kind for kind, spec in DAMAGE.items() if test(spec))


def injuries_where(test: Callable[[InjurySpec], bool]) -> frozenset[InjuryKind]:
    return frozenset(kind for kind, spec in INJURIES.items() if test(spec))


FESTERING_STEPS = tuple(step for step, spec in STEPS.items() if spec.festering)
