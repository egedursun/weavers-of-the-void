from collections.abc import Callable, Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.belonging import IdentityLayer, SalienceDriver
from aerona.domain.enums.referendums import ReferendumSubject
from aerona.rules.registry import Rules

L = IdentityLayer
D = SalienceDriver


@dataclass(frozen=True)
class LayerSpec:
    label: str
    base: Callable[[Rules], int]


@dataclass(frozen=True)
class DriverSpec:
    label: str
    layers: frozenset[IdentityLayer]
    rise: Callable[[Rules], int]


IDENTITY_LAYERS: Mapping[IdentityLayer, LayerSpec] = total(
    IdentityLayer,
    {
        L.PEOPLE: LayerSpec("People", lambda rules: rules.identity.people_base_weight),
        L.FAITH: LayerSpec("Faith", lambda rules: rules.identity.faith_base_weight),
        L.CLASS: LayerSpec("Class", lambda rules: rules.identity.class_base_weight),
        L.LOCALITY: LayerSpec("Home ground", lambda rules: rules.identity.locality_base_weight),
        L.HOUSE: LayerSpec("House", lambda rules: rules.identity.house_base_weight),
        L.PROFESSION: LayerSpec("Work", lambda rules: rules.identity.profession_base_weight),
        L.GENERATION: LayerSpec("Generation", lambda rules: rules.identity.generation_base_weight),
        L.POLITY: LayerSpec("Realm", lambda rules: rules.identity.polity_base_weight),
        L.CIRCLE: LayerSpec("Circle", lambda rules: rules.identity.circle_base_weight),
        L.LANGUAGE: LayerSpec("Tongue", lambda rules: rules.identity.language_base_weight),
        L.KIND: LayerSpec("Kind of being", lambda rules: rules.identity.kind_base_weight),
        L.CAUSE: LayerSpec("Cause", lambda rules: rules.identity.cause_base_weight),
        L.GIFT: LayerSpec("Gift", lambda rules: rules.identity.gift_base_weight),
        L.CALLING: LayerSpec("Calling", lambda rules: rules.identity.calling_base_weight),
    },
)
SALIENCE_DRIVERS: Mapping[SalienceDriver, DriverSpec] = total(
    SalienceDriver,
    {
        D.BASELINE: DriverSpec("Nothing stirs it", frozenset(), lambda rules: 0),
        D.HOLY_WAR: DriverSpec("A war over faith", frozenset({L.FAITH}), lambda rules: rules.identities.holy_war),
        D.FAMINE: DriverSpec("Hunger", frozenset({L.CLASS}), lambda rules: rules.identities.famine),
        D.INVASION: DriverSpec("An enemy in the land", frozenset({L.PEOPLE, L.POLITY}), lambda rules: rules.identities.invasion),
        D.STRIKE: DriverSpec("A strike", frozenset({L.PROFESSION}), lambda rules: rules.identities.strike),
        D.RHETORIC: DriverSpec(
            "A preacher or agitator", frozenset({L.FAITH, L.PROFESSION, L.CIRCLE, L.CAUSE, L.LANGUAGE}), lambda rules: rules.identities.rhetoric
        ),
        D.SEGREGATION: DriverSpec("Living kept apart", frozenset({L.PEOPLE, L.CLASS, L.KIND}), lambda rules: rules.identities.segregation),
        D.CROSSING: DriverSpec("Living across lines", frozenset({L.PEOPLE, L.FAITH, L.KIND}), lambda rules: rules.identities.crossing),
        D.GOD: DriverSpec("A god's hand", frozenset(IdentityLayer), lambda rules: 0),
        D.PERSECUTION: DriverSpec("Persecution", frozenset({L.FAITH, L.PEOPLE, L.KIND, L.LANGUAGE}), lambda rules: rules.identity.persecution_rise),
        D.COMMEMORATION: DriverSpec("Remembering a shared past", frozenset({L.PEOPLE, L.POLITY}), lambda rules: rules.identity.commemoration_rise),
        D.ELECTION: DriverSpec("A vote", frozenset({L.CIRCLE, L.CLASS, L.POLITY, L.PEOPLE, L.FAITH}), lambda rules: rules.identity.election_rise),
        D.CONTEST: DriverSpec("A match between communities", frozenset({L.LOCALITY, L.CIRCLE}), lambda rules: rules.identity.contest_rise),
        D.DISASTER: DriverSpec("A disaster shared", frozenset({L.LOCALITY, L.PEOPLE}), lambda rules: rules.identity.disaster_rise),
        D.ARRIVALS: DriverSpec("Newcomers arriving", frozenset({L.PEOPLE, L.LANGUAGE, L.FAITH}), lambda rules: rules.identity.arrivals_rise),
    },
)
VOTE_LAYERS: Mapping[ReferendumSubject, IdentityLayer] = total(
    ReferendumSubject,
    {
        ReferendumSubject.LAW: L.CLASS,
        ReferendumSubject.CONSTITUTION: L.CLASS,
        ReferendumSubject.INDEPENDENCE: L.PEOPLE,
        ReferendumSubject.UNION: L.POLITY,
        ReferendumSubject.TREATY: L.POLITY,
        ReferendumSubject.WAR: L.POLITY,
        ReferendumSubject.TRANSITION: L.CIRCLE,
        ReferendumSubject.RECALL: L.CIRCLE,
        ReferendumSubject.FAITH: L.FAITH,
    },
)
NEW_LAYERS = (L.LANGUAGE, L.KIND, L.CAUSE)
POINTED_LAYERS = (L.LANGUAGE, L.CAUSE)
