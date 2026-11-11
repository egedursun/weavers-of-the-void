from dataclasses import dataclass, field
from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.collective import StoryletEffect, StoryletId, StoryletRole
from aerona.domain.enums.culture import ProphecyPredicate
from aerona.domain.enums.mind import ValueAxis

E = StoryletEffect
R = StoryletRole
P = ProphecyPredicate


@dataclass(frozen=True)
class Effect:
    kind: StoryletEffect
    role: StoryletRole
    amount: int = 0
    other: StoryletRole | None = None


@dataclass(frozen=True)
class Choice:
    text: str
    appeals: MappingProxyType[ValueAxis, int]
    effects: tuple[Effect, ...]
    follow: StoryletId | None = None
    step: int = 0


@dataclass(frozen=True)
class Condition:
    predicate: ProphecyPredicate
    role: StoryletRole
    key: str
    event: str | None = None


@dataclass(frozen=True)
class Step:
    text: str
    choices: tuple[Choice, ...]


@dataclass(frozen=True)
class Storylet:
    title: str
    chooser: StoryletRole
    roles: tuple[StoryletRole, ...]
    steps: tuple[Step, ...]
    weight: int = 10
    conditions: tuple[Condition, ...] = field(default=())


def appeal(**weights: int) -> MappingProxyType[ValueAxis, int]:
    return MappingProxyType({ValueAxis(name): weight for name, weight in weights.items()})


STORYLETS = total(
    StoryletId,
    {
        StoryletId.LOST_HEIR: Storylet(
            "The lost heir",
            R.RULER,
            (R.REALM, R.RULER, R.CLAIMANT),
            (
                Step(
                    "{claimant} comes before {ruler} and claims to be a lost heir of {realm}.",
                    (
                        Choice("Welcome {claimant} as kin", appeal(family=40, mercy=30, truth=-20), (Effect(E.HEIR, R.CLAIMANT, other=R.RULER),)),
                        Choice(
                            "Have the claim of {claimant} tested",
                            appeal(law=40, truth=40),
                            (Effect(E.RENOWN, R.RULER, 3),),
                            follow=StoryletId.LOST_HEIR,
                            step=1,
                        ),
                        Choice(
                            "Turn {claimant} away",
                            appeal(hierarchy=30, mercy=-30),
                            (Effect(E.FRIENDSHIP, R.CLAIMANT, -40, R.RULER), Effect(E.CLAIM, R.CLAIMANT, other=R.REALM)),
                        ),
                    ),
                ),
                Step(
                    "The test of the claim of {claimant} is done, and {ruler} must rule on it.",
                    (
                        Choice("Accept {claimant} into the line", appeal(truth=30, family=30), (Effect(E.HEIR, R.CLAIMANT, other=R.RULER),)),
                        Choice(
                            "Brand {claimant} a pretender",
                            appeal(law=30, mercy=-20),
                            (Effect(E.INFAMY, R.CLAIMANT, 10), Effect(E.LEGITIMACY, R.REALM, 3)),
                        ),
                    ),
                ),
            ),
            conditions=(Condition(P.RULER_OF, R.REALM, "polity"),),
        ),
        StoryletId.HOARDED_STORE: Storylet(
            "The hoarded store",
            R.RULER,
            (R.TOWN, R.RULER, R.REALM),
            (
                Step(
                    "{town} is short of food while its stores are kept under the hand of {ruler}.",
                    (
                        Choice("Open the stores to all", appeal(mercy=40, kinship=20, wealth=-20), (Effect(E.FOOD, R.TOWN, 40), Effect(E.ORDER, R.TOWN, 8))),
                        Choice(
                            "Sell the stores at a high price",
                            appeal(wealth=50, mercy=-30),
                            (Effect(E.COIN, R.RULER, 200), Effect(E.ANGER, R.TOWN, 30), Effect(E.UNREST, R.TOWN, 8)),
                        ),
                        Choice("Guard the stores for the army", appeal(martial=40, hierarchy=20), (Effect(E.UNREST, R.TOWN, 12), Effect(E.ANGER, R.TOWN, 20))),
                    ),
                ),
            ),
        ),
        StoryletId.BEAST_DEMAND: Storylet(
            "The beast's demand",
            R.RULER,
            (R.TOWN, R.BEAST, R.RULER, R.REALM),
            (
                Step(
                    "{beast} preys on {town}, and its folk look to {ruler} for an answer.",
                    (
                        Choice(
                            "Pay {beast} to keep away", appeal(wealth=-20, mercy=20, martial=-30), (Effect(E.FOOD, R.TOWN, -30), Effect(E.ORDER, R.TOWN, 5))
                        ),
                        Choice(
                            "Go out against {beast}",
                            appeal(martial=50, honour=30),
                            (Effect(E.WOUND, R.RULER, 20), Effect(E.WOUND, R.BEAST, 40), Effect(E.RENOWN, R.RULER, 8)),
                        ),
                        Choice("Wait for {beast} to move on", appeal(leisure=20, martial=-20), (Effect(E.ANGER, R.TOWN, 20), Effect(E.UNREST, R.TOWN, 6))),
                    ),
                ),
            ),
        ),
        StoryletId.FORBIDDEN_TEXT: Storylet(
            "The forbidden text",
            R.SCHOLAR,
            (R.SCHOLAR, R.TEXT, R.CULT),
            (
                Step(
                    "{scholar} finds {text}, which teaches what {cult} forbids.",
                    (
                        Choice("Destroy {text}", appeal(piety=40, knowledge=-40, tradition=30), (Effect(E.DESTROY, R.TEXT), Effect(E.PIETY, R.CULT, 5))),
                        Choice(
                            "Hide {text} away", appeal(knowledge=20, loyalty=20), (Effect(E.RENOWN, R.SCHOLAR, 2),), follow=StoryletId.FORBIDDEN_TEXT, step=1
                        ),
                        Choice(
                            "Teach from {text}",
                            appeal(knowledge=50, truth=30, tradition=-30),
                            (Effect(E.RENOWN, R.SCHOLAR, 6), Effect(E.PIETY, R.CULT, -5), Effect(E.FRIENDSHIP, R.CULT, -30, R.SCHOLAR)),
                        ),
                    ),
                ),
                Step(
                    "The hidden {text} has been found out, and {scholar} is questioned.",
                    (
                        Choice("Confess and give up {text}", appeal(truth=30, piety=20), (Effect(E.DESTROY, R.TEXT), Effect(E.INFAMY, R.SCHOLAR, 3))),
                        Choice("Deny everything", appeal(truth=-30, loyalty=20), (Effect(E.INFAMY, R.SCHOLAR, 8),)),
                    ),
                ),
            ),
        ),
        StoryletId.DEFILED_SITE: Storylet(
            "The defiled site",
            R.RULER,
            (R.SITE, R.CULT, R.RULER, R.TOWN),
            (
                Step(
                    "{site}, held holy by {cult}, has been defiled, and {ruler} must answer.",
                    (
                        Choice(
                            "Hunt down those who defiled {site}",
                            appeal(piety=40, martial=20, mercy=-20),
                            (Effect(E.ANGER, R.TOWN, 20), Effect(E.PIETY, R.CULT, 5)),
                        ),
                        Choice(
                            "Pay for {site} to be made holy again", appeal(piety=30, wealth=-20), (Effect(E.COIN, R.RULER, -150), Effect(E.PIETY, R.CULT, 8))
                        ),
                        Choice("Let the matter rest", appeal(piety=-30, leisure=20), (Effect(E.PIETY, R.CULT, -5), Effect(E.FRIENDSHIP, R.CULT, -30, R.RULER))),
                    ),
                ),
            ),
        ),
        StoryletId.WEDDING_CHALLENGE: Storylet(
            "The wedding challenge",
            R.CHALLENGED,
            (R.CHALLENGER, R.CHALLENGED),
            (
                Step(
                    "At a wedding, {challenger} challenges {challenged} before all the guests.",
                    (
                        Choice("Accept the challenge", appeal(honour=50, martial=30, mercy=-10), (Effect(E.DUEL, R.CHALLENGED, other=R.CHALLENGER),)),
                        Choice("Refuse the challenge", appeal(honour=-30, mercy=30, law=20), (Effect(E.INFAMY, R.CHALLENGED, 4),)),
                        Choice(
                            "Make peace with {challenger}",
                            appeal(friendship=40, mercy=30),
                            (Effect(E.FRIENDSHIP, R.CHALLENGER, 30, R.CHALLENGED), Effect(E.FRIENDSHIP, R.CHALLENGED, 30, R.CHALLENGER)),
                        ),
                    ),
                ),
            ),
        ),
        StoryletId.DYING_RULER: Storylet(
            "The dying ruler",
            R.RULER,
            (R.RULER, R.REALM, R.ELDER_HEIR, R.YOUNGER_HEIR),
            (
                Step(
                    "{ruler} of {realm} is near death, and both {elder_heir} and {younger_heir} wait for a word.",
                    (
                        Choice("Name {elder_heir} as heir", appeal(tradition=40, law=30), (Effect(E.HEIR, R.ELDER_HEIR, other=R.RULER),)),
                        Choice(
                            "Name {younger_heir} as heir",
                            appeal(tradition=-30, competition=30),
                            (Effect(E.HEIR, R.YOUNGER_HEIR, other=R.RULER), Effect(E.FRIENDSHIP, R.ELDER_HEIR, -40, R.YOUNGER_HEIR)),
                            follow=StoryletId.DYING_RULER,
                            step=1,
                        ),
                        Choice("Leave the choice to the realm", appeal(hierarchy=-30, law=20), (Effect(E.LEGITIMACY, R.REALM, -6),)),
                    ),
                ),
                Step(
                    "{elder_heir} will not accept that {younger_heir} was named heir of {realm}.",
                    (
                        Choice("Let {elder_heir} press a claim", appeal(honour=30, competition=30), (Effect(E.CLAIM, R.ELDER_HEIR, other=R.REALM),)),
                        Choice(
                            "Reconcile the heirs",
                            appeal(family=40, mercy=30),
                            (Effect(E.FRIENDSHIP, R.ELDER_HEIR, 30, R.YOUNGER_HEIR), Effect(E.LEGITIMACY, R.REALM, 3)),
                        ),
                    ),
                ),
            ),
            conditions=(Condition(P.RULER_OF, R.REALM, "polity"),),
        ),
        StoryletId.INSULTED_ENVOY: Storylet(
            "The insulted envoy",
            R.RULER,
            (R.ENVOY, R.REALM, R.HOST_REALM, R.RULER),
            (
                Step(
                    "{envoy}, sent by {realm}, was insulted at the court of {ruler} of {host_realm}.",
                    (
                        Choice(
                            "Apologise to {realm}",
                            appeal(mercy=30, honour=-20, xenophilia=30),
                            (Effect(E.LEGITIMACY, R.HOST_REALM, -3), Effect(E.FRIENDSHIP, R.ENVOY, 30, R.RULER)),
                        ),
                        Choice("Send {envoy} away in contempt", appeal(honour=40, xenophilia=-30), (Effect(E.WAR, R.REALM, other=R.HOST_REALM),)),
                        Choice(
                            "Say nothing of it",
                            appeal(leisure=20, xenophilia=-20),
                            (Effect(E.FRIENDSHIP, R.ENVOY, -30, R.RULER),),
                            follow=StoryletId.INSULTED_ENVOY,
                            step=1,
                        ),
                    ),
                ),
                Step(
                    "{realm} still waits for an answer to the slight against {envoy}.",
                    (
                        Choice(
                            "Send gifts to {realm}", appeal(wealth=-20, mercy=20), (Effect(E.COIN, R.RULER, -100), Effect(E.FRIENDSHIP, R.ENVOY, 20, R.RULER))
                        ),
                        Choice("Let {realm} take offence", appeal(honour=20, xenophilia=-30), (Effect(E.WAR, R.REALM, other=R.HOST_REALM),)),
                    ),
                ),
            ),
        ),
    },
)
