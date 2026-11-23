from enum import StrEnum

from aerona.catalog.incident_kinds.spec import FactSpec, IncidentKindSpec, RoleSpec
from aerona.domain.enums.customs import Intoxicant, IntoxicantUse
from aerona.domain.enums.daily_life import HouseDuty
from aerona.domain.enums.modifier import IncidentRole as R
from aerona.domain.enums.mortal import CrimeKind
from aerona.domain.enums.records import FactUnit, FactValue
from aerona.domain.enums.records import ProcessGroup as G
from aerona.domain.enums.relations import AppealKind, ContestEnd, ContestKind, ContestStake, InteractionKind, PersuasionAim


def chosen(key: str, enum: type[StrEnum]) -> FactSpec:
    return FactSpec(key, FactValue.ENUM, enum=enum)


def number(key: str, unit: FactUnit = FactUnit.COUNT) -> FactSpec:
    return FactSpec(key, FactValue.NUMBER, unit)


PAIR = (RoleSpec(R.ACTOR), RoleSpec(R.TARGET))

KINDS: tuple[IncidentKindSpec, ...] = (
    IncidentKindSpec("relation.betrothed", G.SOCIAL, "{actor} and {target} were promised to each other.", roles=PAIR),
    IncidentKindSpec(
        "relation.betrothal_broken",
        G.SOCIAL,
        "The promise between {actor} and {target} was broken, and their houses hold a grievance of {grievance}.",
        roles=PAIR,
        facts=(number("grievance", FactUnit.STANDING),),
    ),
    IncidentKindSpec("relation.sworn", G.SOCIAL, "{actor} and {target} became sworn kin.", roles=PAIR),
    IncidentKindSpec("relation.fostered", G.SOCIAL, "{actor} and {target} became foster kin.", roles=PAIR),
    IncidentKindSpec("relation.sworn_broken", G.SOCIAL, "{actor} broke the oath of kinship sworn with {target}.", roles=PAIR),
    IncidentKindSpec(
        "relation.sworn_aid",
        G.SOCIAL,
        "{actor} came to the aid of sworn kin {target} with {share} of their wealth.",
        roles=PAIR,
        facts=(number("share", FactUnit.WEALTH_POINTS),),
    ),
    IncidentKindSpec(
        "social.interaction",
        G.SOCIAL,
        "{actor} and {target}: {interaction}.",
        roles=PAIR,
        facts=(chosen("interaction", InteractionKind),),
    ),
    IncidentKindSpec(
        "social.persuaded",
        G.SOCIAL,
        "{actor} brought {target} round by {appeal:an} toward {aim:an}, with a score of {score}.",
        roles=PAIR,
        facts=(chosen("appeal", AppealKind), chosen("aim", PersuasionAim), number("score")),
    ),
    IncidentKindSpec(
        "circle.match",
        G.SOCIAL,
        "{actor} met {opponent} in a match; it ended {outcome}.",
        roles=(RoleSpec(R.ACTOR), RoleSpec(R.OPPONENT)),
        facts=(chosen("outcome", ContestEnd),),
    ),
    IncidentKindSpec(
        "circle.debt",
        G.SOCIAL,
        "At the wagers of {subject}, {actor} fell into a debt of {debt} to {target}.",
        roles=(RoleSpec(R.ACTOR), RoleSpec(R.TARGET), RoleSpec(R.SUBJECT)),
        facts=(number("debt", FactUnit.WEALTH_POINTS),),
    ),
    IncidentKindSpec(
        "contest.held",
        G.SOCIAL,
        "{actor} bested {opponent} in {contest:an} by a margin of {margin}.",
        roles=(RoleSpec(R.ACTOR), RoleSpec(R.OPPONENT)),
        facts=(chosen("contest", ContestKind), number("margin")),
    ),
    IncidentKindSpec(
        "contest.stake_paid",
        G.SOCIAL,
        "{opponent} paid {actor} the stake of the contest: {stake}.",
        roles=(RoleSpec(R.ACTOR), RoleSpec(R.OPPONENT), RoleSpec(R.SUBJECT, required=False)),
        facts=(chosen("stake", ContestStake),),
    ),
    IncidentKindSpec(
        "war.surrendered_by_talk",
        G.BATTLES,
        "Talked round by {actor} through {appeal:an}, {target} yielded with its morale at {morale}.",
        roles=PAIR,
        facts=(chosen("appeal", AppealKind), number("morale", FactUnit.PERCENT)),
    ),
    IncidentKindSpec(
        "justice.confessed",
        G.LAW,
        "Moved by {actor} through {appeal:an}, {accused} confessed to {crime}.",
        roles=(RoleSpec(R.ACCUSED), RoleSpec(R.ACTOR)),
        facts=(chosen("crime", CrimeKind), chosen("appeal", AppealKind)),
    ),
    IncidentKindSpec(
        "household.duty_neglected",
        G.SOCIAL,
        "The household of {target} let {duty} lapse under a load of {load}.",
        roles=(RoleSpec(R.TARGET),),
        facts=(chosen("duty", HouseDuty), number("load", FactUnit.PERCENT)),
    ),
    IncidentKindSpec(
        "daily.tale_told",
        G.SOCIAL,
        "{subject} told its past again in tales, giving {share} of its leisure to listening.",
        roles=(RoleSpec(R.SUBJECT),),
        facts=(number("share", FactUnit.PERCENT),),
    ),
    IncidentKindSpec(
        "custom.intoxicant_adopted",
        G.PEOPLES,
        "{subject} took up {intoxicant} for {use}.",
        roles=(RoleSpec(R.SUBJECT),),
        facts=(chosen("intoxicant", Intoxicant), chosen("use", IntoxicantUse)),
    ),
    IncidentKindSpec(
        "people.budded",
        G.PEOPLES,
        "{subject} grew by budding, {grown} more.",
        roles=(RoleSpec(R.SUBJECT),),
        facts=(number("grown", FactUnit.PEOPLE),),
    ),
    IncidentKindSpec(
        "people.partner_lost",
        G.PEOPLES,
        "{subject} lost {target}, the kind it lives joined to, and {lost} of its own were lost with it.",
        roles=(RoleSpec(R.SUBJECT), RoleSpec(R.TARGET)),
        facts=(number("lost", FactUnit.PEOPLE),),
    ),
)
