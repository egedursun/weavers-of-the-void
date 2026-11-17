from collections.abc import Mapping
from dataclasses import dataclass

from aerona.catalog.aspirations import FEARS, GOALS
from aerona.catalog.mind_split import IDEAS, IDEOLOGY_IDEAS, TENET_IDEAS
from aerona.catalog.thoughts import READING_LABELS, READINGS
from aerona.db.kind_concepts.spec import ConceptSpec, KindProperty
from aerona.db.tables.culture_kinds import AimKindRow, FearKindRow, ReadingKindRow, TenetKindRow
from aerona.domain.enums.culture import IdeologyTenet
from aerona.domain.enums.culture_kinds import TenetScope
from aerona.domain.enums.faith import TenetKind
from aerona.domain.enums.kinds import KindConcept
from aerona.domain.enums.mind import DreamReading, Facet, FearKind, IdeaKind, LifeGoal, NeedKind, ThoughtKind, ValueAxis

BAD_THOUGHTS = frozenset({ThoughtKind.HAD_NIGHTMARE})


def words(value: str) -> str:
    return value.replace("_", " ").capitalize()


def options(values: type[ValueAxis] | type[Facet] | type[NeedKind]) -> Mapping[str, str]:
    return {item.value: words(item.value) for item in values}


@dataclass(frozen=True)
class BuiltIn:
    key: str
    name: str
    category: str
    values: Mapping[str, object]


def strongest(weights: Mapping[ValueAxis, int], rank: int) -> tuple[ValueAxis | None, int]:
    ordered = sorted(weights.items(), key=lambda item: (-abs(item[1]), item[0].value))
    return ordered[rank] if len(ordered) > rank else (None, 0)


def tenet_row(key: str, name: str, scope: TenetScope, idea: IdeaKind | None) -> BuiltIn:
    beliefs = IDEAS[idea].beliefs if idea is not None else {}
    first, second = strongest(beliefs, 0), strongest(beliefs, 1)
    values = {"value_axis": first[0], "value_delta": first[1], "second_axis": second[0], "second_delta": second[1]}
    return BuiltIn(key, name, scope.value, values)


def built_in_tenets() -> list[BuiltIn]:
    rows = [tenet_row(f"idea.{idea.value}", spec.label, TenetScope.IDEA, idea) for idea, spec in IDEAS.items()]
    rows += [tenet_row(f"ideology.{tenet.value}", words(tenet.value), TenetScope.IDEOLOGY, IDEOLOGY_IDEAS.get(tenet)) for tenet in IdeologyTenet]
    rows += [tenet_row(f"doctrine.{tenet.value}", words(tenet.value), TenetScope.DOCTRINE, TENET_IDEAS.get(tenet)) for tenet in TenetKind]
    return rows


def built_in_fears() -> list[BuiltIn]:
    rows = []
    for fear, spec in FEARS.items():
        facet, weight = max(spec.facets.items(), key=lambda item: (abs(item[1]), item[0].value))
        rows.append(BuiltIn(f"fear.{fear.value}", spec.label, fear.value, {"grip": 50, "facet": facet, "facet_weight": abs(weight)}))
    return rows


def built_in_readings() -> list[BuiltIn]:
    rows = []
    for reading in DreamReading:
        spec = READINGS.get(reading)
        axis, lean = strongest(spec.beliefs, 0) if spec is not None else (None, 0)
        valence = 0 if spec is None else -50 if spec.thought in BAD_THOUGHTS else 50
        rows.append(BuiltIn(f"reading.{reading.value}", READING_LABELS[reading], reading.value, {"valence": valence, "value_axis": axis, "lean": lean}))
    return rows


def built_in_aims() -> list[BuiltIn]:
    rows = []
    for goal, spec in GOALS.items():
        axis, weight = strongest(spec.beliefs, 0)
        rows.append(BuiltIn(f"aim.{goal.value}", spec.label, goal.value, {"pull": 0, "need": None, "value_axis": axis, "value_weight": weight}))
    return rows


TENET_SPEC = ConceptSpec(
    concept=KindConcept.TENET,
    label="Tenet",
    plural="Tenets",
    hint="What a doctrine, an ideology or an idea holds; its holders' values move by its deltas",
    table=TenetKindRow,
    category=TenetScope,
    category_labels={scope.value: words(scope.value) for scope in TenetScope},
    properties=(
        KindProperty("value_axis", "First value", "The value its holders come to weigh more or less", options=options(ValueAxis)),
        KindProperty("value_delta", "Pull on the first value", "How far it moves that value each epoch, at full strength", -50, 50),
        KindProperty("second_axis", "Second value", "A second value it moves", options=options(ValueAxis)),
        KindProperty("second_delta", "Pull on the second value", "How far it moves the second value each epoch, at full strength", -50, 50),
    ),
    readers=("culture_kinds",),
)
FEAR_SPEC = ConceptSpec(
    concept=KindConcept.FEAR,
    label="Fear",
    plural="Fears",
    hint="What a people fears; its category names what sets the fear off near a mortal",
    table=FearKindRow,
    category=FearKind,
    category_labels={fear.value: spec.label for fear, spec in FEARS.items()},
    properties=(
        KindProperty("grip", "Grip", "How hard the fear strikes when it is near (50 is the plain measure)"),
        KindProperty("facet", "Leaning", "The side of a mortal's nature that draws the fear to them", options=options(Facet)),
        KindProperty("facet_weight", "Draw", "How strongly that leaning draws the fear"),
    ),
    readers=("aspirations",),
)
READING_SPEC = ConceptSpec(
    concept=KindConcept.DREAM_READING,
    label="Dream reading",
    plural="Dream readings",
    hint="How a culture reads a dream; the reading moves the dreamer's values",
    table=ReadingKindRow,
    category=DreamReading,
    category_labels={reading.value: label for reading, label in READING_LABELS.items()},
    properties=(
        KindProperty("valence", "Valence", "Whether the reading is welcome (above 0) or dreaded (below 0)", -100, 100),
        KindProperty("value_axis", "Value moved", "The value the dreamer leans toward after the reading", options=options(ValueAxis)),
        KindProperty("lean", "Lean", "How far that value moves", -20, 20),
    ),
    readers=("dreams",),
)
AIM_SPEC = ConceptSpec(
    concept=KindConcept.AIM,
    label="Aim",
    plural="Aims",
    hint="A life's aim a people holds up; it pulls its mortals toward the goal of its category",
    table=AimKindRow,
    category=LifeGoal,
    category_labels={goal.value: spec.label for goal, spec in GOALS.items()},
    properties=(
        KindProperty("pull", "Pull", "How strongly the aim draws a mortal of its people when a life's goal is chosen"),
        KindProperty("need", "Need it answers", "The need of a mortal that makes the aim weigh more", options=options(NeedKind)),
        KindProperty("value_axis", "Value it speaks to", "The value that makes the aim weigh more", options=options(ValueAxis)),
        KindProperty("value_weight", "Weight of that value", "How much that value counts toward the aim", -100, 100),
    ),
    readers=("aspirations",),
)
SPECS = (TENET_SPEC, FEAR_SPEC, READING_SPEC, AIM_SPEC)
BUILT_INS: tuple[tuple[type[TenetKindRow | FearKindRow | ReadingKindRow | AimKindRow], list[BuiltIn]], ...] = (
    (TenetKindRow, built_in_tenets()),
    (FearKindRow, built_in_fears()),
    (ReadingKindRow, built_in_readings()),
    (AimKindRow, built_in_aims()),
)
