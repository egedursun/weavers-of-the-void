from collections.abc import Callable, Mapping
from dataclasses import dataclass

from aerona.catalog.modifier_effects import StatEffect, add, scale
from aerona.core.total import total
from aerona.domain.enums.body import BodyFunction, BodyPart, Capacity, ConditionKind, InjuryKind, InjuryState, MaimedKind
from aerona.domain.enums.crafts import AssistiveAid
from aerona.rules.registry.body import CapacityRules, ConditionRules, MaimedRules

C = Capacity
K = ConditionKind
M = MaimedKind
Penalty = Callable[[CapacityRules], dict[Capacity, int]]


@dataclass(frozen=True)
class ConditionSpec:
    text: str
    penalty: Penalty
    visible: bool = False
    madness: Callable[[ConditionRules], int] | None = None
    sense_loss: bool = False
    of_age: bool = False
    curable: bool = False
    aid: AssistiveAid | None = None
    effects: tuple[StatEffect, ...] = ()


@dataclass(frozen=True)
class CapacitySpec:
    text: str
    alert: bool
    bedridden: bool


@dataclass(frozen=True)
class MaimedSpec:
    text: str
    weight: Callable[[MaimedRules], int]
    function: BodyFunction
    injury: InjuryKind
    eyes: bool = False
    both_sides: bool = False
    part: BodyPart | None = None
    loss: Callable[[MaimedRules], int] = lambda rules: rules.labour_loss_pct


@dataclass(frozen=True)
class StateSpec:
    open: bool
    rank: int
    fresh: bool = False
    festering: bool = False


CONDITIONS: Mapping[ConditionKind, ConditionSpec] = total(
    ConditionKind,
    {
        K.CHRONIC_ILLNESS: ConditionSpec(
            "a lingering illness",
            lambda rules: {C.MOBILITY: rules.illness_mobility, C.MELEE: rules.illness_melee, C.FERTILITY: rules.illness_fertility},
            of_age=True,
            curable=True,
            effects=(
                scale("strength", lambda rules: rules.modifiers.illness_strength_pct / 100),
                scale("agility", lambda rules: rules.modifiers.illness_strength_pct / 100),
            ),
        ),
        K.PARANOIA: ConditionSpec(
            "paranoia",
            lambda rules: {C.COMMAND: rules.paranoia_command, C.PRESENCE: rules.paranoia_presence},
            madness=lambda rules: rules.paranoia_weight,
            curable=True,
            effects=(add("charisma", lambda rules: -rules.modifiers.paranoia_charisma),),
        ),
        K.VISIONS: ConditionSpec(
            "visions", lambda rules: {C.SCHOLARSHIP: rules.visions_scholarship, C.PRESENCE: -rules.visions_presence}, madness=lambda rules: rules.visions_weight
        ),
        K.RAGE: ConditionSpec(
            "fits of rage",
            lambda rules: {C.MELEE: -rules.rage_melee, C.COMMAND: rules.rage_command, C.CRAFT: rules.rage_craft},
            madness=lambda rules: rules.rage_weight,
            effects=(add("strength", lambda rules: rules.modifiers.rage_strength), add("intellect", lambda rules: -rules.modifiers.rage_intellect)),
        ),
        K.MELANCHOLY: ConditionSpec(
            "melancholy",
            lambda rules: {C.COMMAND: rules.melancholy_command, C.CRAFT: rules.melancholy_craft, C.PRESENCE: rules.melancholy_presence},
            madness=lambda rules: rules.melancholy_weight,
            curable=True,
            effects=(add("intellect", lambda rules: -rules.modifiers.melancholy_intellect),),
        ),
        K.ADDICTION: ConditionSpec(
            "an addiction",
            lambda rules: {C.CRAFT: rules.addiction_craft, C.SCHOLARSHIP: rules.addiction_scholarship, C.PRESENCE: rules.addiction_presence},
        ),
        K.AGE_BLINDNESS: ConditionSpec(
            "blindness of age",
            lambda rules: {C.MISSILE: rules.blindness_missile, C.SCHOLARSHIP: rules.blindness_scholarship, C.CRAFT: rules.blindness_craft},
            sense_loss=True,
            of_age=True,
            curable=True,
            aid=AssistiveAid.SPECTACLES,
        ),
        K.AGE_DEAFNESS: ConditionSpec(
            "deafness of age", lambda rules: {C.COMMAND: rules.deafness_command}, sense_loss=True, of_age=True, aid=AssistiveAid.HEARING_HORN
        ),
        K.WITHERED_LIMB: ConditionSpec(
            "a withered limb",
            lambda rules: {C.MELEE: rules.withered_melee, C.CRAFT: rules.withered_craft},
            visible=True,
            curable=True,
            aid=AssistiveAid.CANE,
            effects=(scale("strength", lambda rules: rules.modifiers.withered_strength_pct / 100),),
        ),
        K.ENDLESS_HUNGER: ConditionSpec(
            "an endless hunger",
            lambda rules: {C.MOBILITY: rules.hunger_mobility, C.PRESENCE: rules.hunger_presence},
            effects=(add("charisma", lambda rules: -rules.modifiers.hunger_charisma),),
        ),
        K.POSSESSION: ConditionSpec(
            "a possessing spirit",
            lambda rules: {C.COMMAND: rules.possession_command, C.PRESENCE: rules.possession_presence, C.MELEE: -rules.possession_melee},
            visible=True,
        ),
        K.VOID_TAINT: ConditionSpec(
            "the taint of the void",
            lambda rules: {C.SCHOLARSHIP: rules.void_scholarship, C.PRESENCE: rules.void_presence},
            visible=True,
            effects=(add("charisma", lambda rules: -rules.modifiers.void_taint_charisma),),
        ),
        K.CHOSEN_MARK: ConditionSpec(
            "the mark of the chosen",
            lambda rules: {C.PRESENCE: -rules.chosen_presence, C.MELEE: -rules.chosen_melee},
            visible=True,
            effects=(add("charisma", lambda rules: rules.modifiers.chosen_charisma),),
        ),
        K.DIVINE_BRAND: ConditionSpec(
            "a god's brand",
            lambda rules: {C.PRESENCE: -rules.brand_presence},
            visible=True,
            effects=(add("charisma", lambda rules: rules.modifiers.brand_charisma),),
        ),
        K.NIGHTMARES: ConditionSpec(
            "recurring nightmares",
            lambda rules: {C.COMMAND: rules.nightmares_command, C.CRAFT: rules.nightmares_craft},
            curable=True,
            effects=(add("willpower", lambda rules: -rules.modifiers.nightmares_willpower),),
        ),
        K.COMATOSE: ConditionSpec(
            "a sleep no one can wake them from",
            lambda rules: {capacity: rules.comatose_lost for capacity in C if capacity is not C.FERTILITY},
            visible=True,
        ),
        K.COGNITIVE_DECLINE: ConditionSpec(
            "a failing memory and reckoning",
            lambda rules: {C.SCHOLARSHIP: rules.decline_scholarship, C.COMMAND: rules.decline_command, C.CRAFT: rules.decline_craft},
            visible=True,
        ),
        K.MALNUTRITION: ConditionSpec(
            "a body wasted by a poor diet",
            lambda rules: {C.MELEE: rules.malnutrition_melee, C.CRAFT: rules.malnutrition_craft, C.FERTILITY: rules.malnutrition_fertility},
        ),
        K.PARALYSIS: ConditionSpec(
            "paralysis below a wound",
            lambda rules: {C.MOBILITY: rules.paralysis_mobility, C.MELEE: rules.paralysis_melee},
            visible=True,
            aid=AssistiveAid.CANE,
        ),
        K.INFERTILITY: ConditionSpec("infertility", lambda rules: {C.FERTILITY: rules.infertility_fertility}, of_age=True, curable=True),
        K.CHRONIC_PAIN: ConditionSpec(
            "a lasting pain",
            lambda rules: {
                C.MELEE: rules.chronic_pain_capacity_cut,
                C.CRAFT: rules.chronic_pain_capacity_cut,
                C.SCHOLARSHIP: rules.chronic_pain_capacity_cut,
                C.COMMAND: rules.chronic_pain_capacity_cut,
            },
            curable=True,
        ),
        K.SEIZURES: ConditionSpec("seizures", lambda rules: {C.COMMAND: rules.seizure_capacity_cut, C.CRAFT: rules.seizure_capacity_cut}, visible=True),
        K.LASTING_FEAR: ConditionSpec("a lasting fear", lambda rules: {C.MELEE: rules.lasting_fear_melee, C.COMMAND: rules.lasting_fear_melee}, curable=True),
        K.BREATHLESSNESS: ConditionSpec("breathlessness", lambda rules: {C.ENDURANCE: rules.breathless_endurance, C.LABOUR: rules.breathless_endurance}),
    },
)

CAPACITIES: Mapping[Capacity, CapacitySpec] = total(
    Capacity,
    {
        C.MELEE: CapacitySpec("fighting hand to hand", alert=True, bedridden=True),
        C.MISSILE: CapacitySpec("shooting and throwing", alert=True, bedridden=True),
        C.COMMAND: CapacitySpec("giving orders", alert=True, bedridden=True),
        C.CRAFT: CapacitySpec("making things", alert=True, bedridden=True),
        C.SCHOLARSHIP: CapacitySpec("reading and study", alert=True, bedridden=False),
        C.PRESENCE: CapacitySpec("how others see them", alert=False, bedridden=False),
        C.MOBILITY: CapacitySpec("getting about", alert=False, bedridden=True),
        C.FERTILITY: CapacitySpec("bearing children", alert=False, bedridden=False),
        C.ENDURANCE: CapacitySpec("hard work and long journeys", alert=False, bedridden=True),
        C.PERCEPTION: CapacitySpec("keeping watch and noticing", alert=True, bedridden=False),
        C.STEALTH: CapacitySpec("going unseen", alert=True, bedridden=True),
        C.LABOUR: CapacitySpec("work by strength", alert=False, bedridden=True),
    },
)

MAIMS: Mapping[MaimedKind, MaimedSpec] = total(
    MaimedKind,
    {
        M.ONE_ARMED: MaimedSpec("one-armed", lambda rules: rules.one_armed, BodyFunction.GRASP, InjuryKind.SEVERED),
        M.ONE_LEGGED: MaimedSpec("one-legged", lambda rules: rules.one_legged, BodyFunction.LOCOMOTION, InjuryKind.SEVERED),
        M.ONE_EYED: MaimedSpec("one-eyed", lambda rules: rules.one_eyed, BodyFunction.SIGHT, InjuryKind.GOUGED, eyes=True),
        M.BLIND: MaimedSpec("blind", lambda rules: rules.blind, BodyFunction.SIGHT, InjuryKind.GOUGED, eyes=True, both_sides=True),
        M.DEAF: MaimedSpec("deaf", lambda rules: rules.deaf, BodyFunction.HEARING, InjuryKind.DESTROYED, both_sides=True),
        M.MUTE: MaimedSpec("mute", lambda rules: rules.mute, BodyFunction.SPEECH, InjuryKind.DESTROYED),
        M.LAME: MaimedSpec("lame", lambda rules: rules.lame, BodyFunction.LOCOMOTION, InjuryKind.CRUSH),
        M.SCARRED: MaimedSpec("disfigured", lambda rules: rules.scarred, BodyFunction.PRESENCE, InjuryKind.BURN),
        M.BROKEN_MINDED: MaimedSpec("broken in mind", lambda rules: rules.broken_minded, BodyFunction.COGNITION, InjuryKind.CRUSH),
        M.PARALYSED: MaimedSpec(
            "paralysed",
            lambda rules: rules.paralysed,
            BodyFunction.LOCOMOTION,
            InjuryKind.DESTROYED,
            part=BodyPart.SPINE,
            loss=lambda rules: rules.paralysed_loss_pct,
        ),
        M.LOST_FINGERS: MaimedSpec(
            "missing fingers",
            lambda rules: rules.lost_fingers,
            BodyFunction.FINE_MANIPULATION,
            InjuryKind.SEVERED,
            part=BodyPart.FINGERS,
            loss=lambda rules: rules.lost_fingers_craft_cut,
        ),
        M.LOST_TAIL: MaimedSpec("tailless", lambda rules: rules.lost_tail, BodyFunction.TAIL, InjuryKind.SEVERED, part=BodyPart.TAIL),
        M.LOST_WING: MaimedSpec("wing lost", lambda rules: rules.lost_wing, BodyFunction.FLIGHT, InjuryKind.SEVERED),
    },
)

STATES: Mapping[InjuryState, StateSpec] = total(
    InjuryState,
    {
        InjuryState.FRESH: StateSpec(open=True, rank=2, fresh=True),
        InjuryState.INFECTED: StateSpec(open=True, rank=4, festering=True),
        InjuryState.HEALING: StateSpec(open=True, rank=1),
        InjuryState.HEALED_SCAR: StateSpec(open=False, rank=0),
        InjuryState.PERMANENT: StateSpec(open=False, rank=3),
        InjuryState.LETHAL: StateSpec(open=False, rank=6),
        InjuryState.GANGRENOUS: StateSpec(open=True, rank=5, festering=True),
        InjuryState.REOPENED: StateSpec(open=True, rank=2, fresh=True),
        InjuryState.CHRONIC: StateSpec(open=False, rank=3),
    },
)

OPEN_INJURY_STATES = frozenset(state for state, spec in STATES.items() if spec.open)
FRESH_STATES = frozenset(state for state, spec in STATES.items() if spec.fresh)
FESTERING = frozenset(state for state, spec in STATES.items() if spec.festering)
MADNESS_CONDITIONS = tuple(kind for kind, spec in CONDITIONS.items() if spec.madness is not None)
SENSE_CONDITIONS = (*(kind for kind, spec in CONDITIONS.items() if spec.sense_loss), *MADNESS_CONDITIONS)
AGE_CONDITIONS = tuple(kind for kind, spec in CONDITIONS.items() if spec.of_age)
CURABLE_CONDITIONS = frozenset(kind for kind, spec in CONDITIONS.items() if spec.curable)
VISIBLE_CONDITIONS = frozenset(kind for kind, spec in CONDITIONS.items() if spec.visible)
AIDED_CONDITIONS = {kind: spec.aid for kind, spec in CONDITIONS.items() if spec.aid is not None}
ALERT_CAPACITIES = tuple(capacity for capacity, spec in CAPACITIES.items() if spec.alert)
BEDRIDDEN_LOSSES = tuple(capacity for capacity, spec in CAPACITIES.items() if spec.bedridden)
