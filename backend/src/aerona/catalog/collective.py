from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.collective import CollectiveActKind, CollectiveTrigger, CrowdFeeling, FormativeKind, MobTarget, Tincture
from aerona.domain.enums.gathering import CollectionKind
from aerona.domain.enums.life_traits import EmotionTrait
from aerona.domain.enums.mind import ValueAxis
from aerona.rules.registry import Rules

A = CollectiveActKind
T = CollectiveTrigger
C = CrowdFeeling


@dataclass(frozen=True)
class FeelingSpec:
    label: str
    trait: EmotionTrait
    cut: Callable[[Rules], int]
    decay: Callable[[Rules], int]


@dataclass(frozen=True)
class TriggerSpec:
    act: CollectiveActKind
    feelings: tuple[CrowdFeeling, ...]
    target: MobTarget
    text: str
    push: Callable[[Rules], int]

    @property
    def mood(self) -> CrowdFeeling:
        return self.feelings[0]


@dataclass(frozen=True)
class ActSpec:
    text: str
    feeling: CrowdFeeling
    collection: CollectionKind
    threshold: Callable[[Rules], int]
    angry: bool = False
    faith: bool = False
    harmless: bool = False
    instead_of: frozenset[CollectiveActKind] = frozenset()
    turns_on: tuple[CrowdFeeling, ...] = ()
    daunted: bool = False
    leaves: bool = False
    refuses_trade: bool = False
    rejoices: bool = False


CROWD_FEELINGS: Mapping[CrowdFeeling, FeelingSpec] = total(
    CrowdFeeling,
    {
        C.ANGER: FeelingSpec("Anger", EmotionTrait.ANGRY, lambda rules: rules.collective_behaviour.anger_cut, lambda rules: rules.collective.anger_decay),
        C.FEAR: FeelingSpec("Fear", EmotionTrait.AFRAID, lambda rules: rules.collective_behaviour.anxiety_cut, lambda rules: rules.collective.fear_decay),
        C.FERVOUR: FeelingSpec(
            "Fervour", EmotionTrait.STIRRED, lambda rules: rules.collective_behaviour.fervour_cut, lambda rules: rules.collective.fervour_decay
        ),
        C.GRIEF: FeelingSpec("Grief", EmotionTrait.GRIEVING, lambda rules: rules.collective.grief_cut, lambda rules: rules.collective.grief_decay),
        C.HOPE: FeelingSpec("Hope", EmotionTrait.HOPEFUL, lambda rules: rules.collective.hope_cut, lambda rules: rules.collective.hope_decay),
        C.JOY: FeelingSpec("Joy", EmotionTrait.STIRRED, lambda rules: rules.collective.joy_cut, lambda rules: rules.collective.joy_decay),
        C.SOLIDARITY: FeelingSpec(
            "Solidarity", EmotionTrait.HOPEFUL, lambda rules: rules.collective.solidarity_cut, lambda rules: rules.collective.solidarity_decay
        ),
    },
)
TRIGGERS: Mapping[CollectiveTrigger, TriggerSpec] = total(
    CollectiveTrigger,
    {
        T.PRICE_SPIKE: TriggerSpec(A.RIOT, (C.ANGER,), MobTarget.GRANARY, "the price of food", lambda rules: rules.collective.price_spike_push),
        T.EXECUTION: TriggerSpec(A.RIOT, (C.ANGER, C.FEAR), MobTarget.PALACE, "an execution", lambda rules: rules.collective.execution_push),
        T.SERMON: TriggerSpec(A.REVIVAL, (C.FERVOUR, C.HOPE), MobTarget.TEMPLE, "a preacher's call", lambda rules: rules.collective.sermon_push),
        T.OMEN: TriggerSpec(A.PANIC, (C.FEAR, C.HOPE), MobTarget.GATE, "an omen", lambda rules: rules.collective.omen_push),
        T.RUMOUR: TriggerSpec(A.PANIC, (C.FEAR,), MobTarget.SCAPEGOAT, "a rumour", lambda rules: rules.collective.rumour_push),
        T.FIRE: TriggerSpec(A.PANIC, (C.FEAR, C.GRIEF), MobTarget.GATE, "a fire", lambda rules: rules.collective.fire_push),
        T.PLAGUE: TriggerSpec(A.PROCESSION, (C.FERVOUR, C.GRIEF, C.FEAR), MobTarget.SCAPEGOAT, "a plague", lambda rules: rules.collective.plague_push),
        T.BEAST: TriggerSpec(A.PANIC, (C.FEAR,), MobTarget.GATE, "a beast at hand", lambda rules: rules.collective.beast_push),
        T.ECLIPSE: TriggerSpec(A.PANIC, (C.FEAR,), MobTarget.TEMPLE, "an eclipse", lambda rules: rules.collective.eclipse_push),
        T.MIRACLE: TriggerSpec(A.CONVERSION, (C.FERVOUR, C.HOPE), MobTarget.TEMPLE, "a miracle", lambda rules: rules.collective.miracle_push),
        T.FAMINE: TriggerSpec(A.RIOT, (C.ANGER, C.GRIEF), MobTarget.GRANARY, "hunger", lambda rules: rules.collective.famine_push),
        T.UNPAID_WAGES: TriggerSpec(A.STRIKE, (C.ANGER,), MobTarget.WORKSHOP, "unpaid wages", lambda rules: rules.collective.unpaid_wages_push),
        T.LOST_MATCH: TriggerSpec(A.RIOT, (C.ANGER,), MobTarget.DISTRICT, "a lost match", lambda rules: rules.collective.lost_match_push),
        T.VICTORY: TriggerSpec(A.JUBILATION, (C.FERVOUR, C.HOPE), MobTarget.PALACE, "a victory", lambda rules: rules.collective.victory_push),
        T.GREAT_FUNERAL: TriggerSpec(A.PROCESSION, (C.GRIEF,), MobTarget.TEMPLE, "a great funeral", lambda rules: rules.collective.great_funeral_push),
        T.ELECTION: TriggerSpec(A.DEMONSTRATION, (C.ANGER, C.FERVOUR), MobTarget.PALACE, "an election", lambda rules: rules.collective.election_push),
        T.PRICE_RISE: TriggerSpec(A.PETITION, (C.ANGER, C.SOLIDARITY), MobTarget.PALACE, "rising prices", lambda rules: rules.collective.price_rise_push),
        T.ARREST: TriggerSpec(A.VIGIL, (C.ANGER, C.SOLIDARITY), MobTarget.PALACE, "an arrest", lambda rules: rules.collective.arrest_push),
    },
)
ACTS: Mapping[CollectiveActKind, ActSpec] = total(
    CollectiveActKind,
    {
        A.RIOT: ActSpec("rioted", C.ANGER, CollectionKind.RIOT, lambda rules: rules.collective.riot_threshold, angry=True),
        A.PANIC: ActSpec("fled in panic", C.FEAR, CollectionKind.PANIC, lambda rules: rules.collective.panic_threshold),
        A.LYNCHING: ActSpec("lynched a scapegoat", C.ANGER, CollectionKind.RIOT, lambda rules: rules.collective.lynching_threshold, angry=True),
        A.CONVERSION: ActSpec(
            "turned to a new faith", C.FERVOUR, CollectionKind.CONVERSION_WAVE, lambda rules: rules.collective.conversion_threshold, faith=True
        ),
        A.REVOLT: ActSpec("rose in revolt", C.ANGER, CollectionKind.INSURRECTION, lambda rules: rules.collective.revolt_threshold, angry=True),
        A.STRIKE: ActSpec("laid down their work", C.ANGER, CollectionKind.RIOT, lambda rules: rules.collective.strike_threshold, angry=True),
        A.PROCESSION: ActSpec("marched in procession", C.GRIEF, CollectionKind.PROCESSION, lambda rules: rules.collective.procession_threshold, faith=True),
        A.REVIVAL: ActSpec("rose in a revival", C.FERVOUR, CollectionKind.MOVEMENT, lambda rules: rules.collective.revival_threshold, faith=True),
        A.JUBILATION: ActSpec(
            "rejoiced in the streets", C.HOPE, CollectionKind.FEAST, lambda rules: rules.collective.jubilation_threshold, harmless=True, rejoices=True
        ),
        A.DEMONSTRATION: ActSpec(
            "marched to press a demand",
            C.HOPE,
            CollectionKind.PROCESSION,
            lambda rules: rules.collective.demonstration_threshold,
            harmless=True,
            instead_of=frozenset({A.RIOT}),
            turns_on=(C.HOPE,),
        ),
        A.BOYCOTT: ActSpec(
            "refused to trade with those it blames",
            C.ANGER,
            CollectionKind.MOVEMENT,
            lambda rules: rules.collective.boycott_threshold,
            harmless=True,
            instead_of=frozenset({A.RIOT, A.STRIKE}),
            daunted=True,
            refuses_trade=True,
        ),
        A.EXODUS: ActSpec(
            "left together",
            C.GRIEF,
            CollectionKind.MIGRATION,
            lambda rules: rules.collective.exodus_threshold,
            harmless=True,
            instead_of=frozenset({A.PANIC, A.PROCESSION}),
            turns_on=(C.GRIEF, C.FEAR),
            leaves=True,
        ),
        A.VIGIL: ActSpec(
            "kept a vigil",
            C.SOLIDARITY,
            CollectionKind.PROCESSION,
            lambda rules: rules.collective.vigil_threshold,
            harmless=True,
            instead_of=frozenset({A.RIOT, A.LYNCHING}),
            turns_on=(C.GRIEF, C.SOLIDARITY),
        ),
        A.OCCUPATION: ActSpec(
            "held a place and would not leave it",
            C.SOLIDARITY,
            CollectionKind.MOVEMENT,
            lambda rules: rules.collective.occupation_threshold,
            instead_of=frozenset({A.STRIKE, A.REVOLT}),
            turns_on=(C.ANGER, C.SOLIDARITY),
            refuses_trade=True,
        ),
        A.PETITION: ActSpec(
            "brought a petition to those who rule",
            C.HOPE,
            CollectionKind.PROCESSION,
            lambda rules: rules.collective.petition_threshold,
            harmless=True,
            instead_of=frozenset({A.DEMONSTRATION, A.RIOT}),
            turns_on=(C.HOPE, C.SOLIDARITY),
        ),
    },
)
ACT_TEXT: Mapping[CollectiveActKind, str] = MappingProxyType({act: spec.text for act, spec in ACTS.items()})
ANGRY_ACTS = frozenset(act for act, spec in ACTS.items() if spec.angry)
FAITH_ACTS = frozenset(act for act, spec in ACTS.items() if spec.faith)
ACT_COLLECTION: Mapping[CollectiveActKind, CollectionKind] = MappingProxyType({act: spec.collection for act, spec in ACTS.items()})

F = FormativeKind
V = ValueAxis
FORMATIVE_SHIFTS = total(
    FormativeKind,
    {
        F.GREAT_WAR: ((V.MARTIAL, 1), (V.MERCY, 1)),
        F.VICTORY: ((V.HONOUR, 1), (V.COMPETITION, 1)),
        F.DEFEAT: ((V.LOYALTY, -1), (V.TRADITION, -1)),
        F.PLAGUE: ((V.PIETY, 1), (V.SUPERSTITION, 1)),
        F.FAMINE: ((V.WEALTH, 1), (V.KINSHIP, 1)),
        F.GOLDEN_AGE: ((V.LEISURE, 1), (V.XENOPHILIA, 1)),
        F.CONQUEST: ((V.HIERARCHY, -1), (V.LOYALTY, 1)),
        F.REVOLUTION: ((V.HIERARCHY, -1), (V.TRADITION, -1)),
        F.MIGRATION: ((V.XENOPHILIA, 1), (V.KINSHIP, 1)),
        F.FOUNDING: ((V.TRADITION, 1), (V.LOYALTY, 1)),
        F.REVELATION: ((V.TRUTH, 1), (V.PIETY, 1)),
        F.COLLAPSE: ((V.PERSEVERANCE, 1), (V.HIERARCHY, -1)),
        F.CONTACT: ((V.XENOPHILIA, 1), (V.KNOWLEDGE, 1)),
        F.DISASTER: ((V.PERSEVERANCE, 1), (V.NATURE, 1)),
        F.LIBERATION: ((V.LAW, 1), (V.HIERARCHY, -1)),
        F.SCHISM: ((V.PIETY, 1), (V.LOYALTY, -1)),
        F.LONG_SEASON: ((V.PERSEVERANCE, 1), (V.PIETY, 1)),
        F.PEACE: ((V.LEISURE, 1), (V.MARTIAL, -1)),
        F.PERSECUTION: ((V.KINSHIP, 1), (V.TRADITION, 1)),
    },
)
COLLECTION_FORMATIVE = MappingProxyType(
    {
        CollectionKind.WAR: F.GREAT_WAR,
        CollectionKind.SIEGE: F.GREAT_WAR,
        CollectionKind.PLAGUE: F.PLAGUE,
        CollectionKind.FAMINE: F.FAMINE,
        CollectionKind.OCCUPATION: F.CONQUEST,
        CollectionKind.INSURRECTION: F.REVOLUTION,
        CollectionKind.COUP: F.REVOLUTION,
        CollectionKind.MIGRATION: F.MIGRATION,
        CollectionKind.FOUNDING: F.FOUNDING,
        CollectionKind.EXCAVATION: F.REVELATION,
        CollectionKind.SUCCESSION_CRISIS: F.COLLAPSE,
        CollectionKind.JOURNEY: F.CONTACT,
        CollectionKind.BEAST_ATTACK: F.DISASTER,
        CollectionKind.SCHISM: F.SCHISM,
        CollectionKind.MOVEMENT: F.LIBERATION,
    }
)
LEGACY_TINCTURES = MappingProxyType(
    {
        "or": Tincture.GOLD,
        "argent": Tincture.SILVER,
        "gules": Tincture.RED,
        "azure": Tincture.BLUE,
        "vert": Tincture.GREEN,
        "sable": Tincture.BLACK,
        "purpure": Tincture.PURPLE,
        "tenne": Tincture.ORANGE,
        "celeste": Tincture.CELESTE,
        "murrey": Tincture.MURREY,
        "rose": Tincture.ROSE,
        "brunatre": Tincture.BROWN,
        "cendree": Tincture.GREY,
        "ermine": Tincture.ERMINE,
        "ermines": Tincture.ERMINES,
        "vair": Tincture.VAIR,
    }
)
HERALDIC_NAMES = total(
    Tincture,
    {
        Tincture.GOLD: "or",
        Tincture.SILVER: "argent",
        Tincture.RED: "gules",
        Tincture.BLUE: "azure",
        Tincture.GREEN: "vert",
        Tincture.BLACK: "sable",
        Tincture.PURPLE: "purpure",
        Tincture.ORANGE: "tenne",
        Tincture.CELESTE: "celeste",
        Tincture.MURREY: "murrey",
        Tincture.ROSE: "rose",
        Tincture.BROWN: "brunatre",
        Tincture.GREY: "cendree",
        Tincture.ERMINE: "ermine",
        Tincture.ERMINES: "ermines",
        Tincture.VAIR: "vair",
    },
)
