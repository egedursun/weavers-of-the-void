from enum import StrEnum

from aerona.catalog.incident_kinds.spec import FactSpec, IncidentKindSpec, RoleSpec
from aerona.domain.enums.chronicle import WritingSystem
from aerona.domain.enums.collective import AccountKind, AccountMedium, AccountStance
from aerona.domain.enums.crafts import InsuranceCover
from aerona.domain.enums.customs import Intoxicant, IntoxicantUse
from aerona.domain.enums.daily_life import HouseDuty
from aerona.domain.enums.economy import CommodityKind, TradeLoss, WorkshopKind
from aerona.domain.enums.industry import Pollutant
from aerona.domain.enums.means import WritingMedium
from aerona.domain.enums.modifier import IncidentRole as R
from aerona.domain.enums.mortal import CrimeKind
from aerona.domain.enums.records import FactUnit, FactValue
from aerona.domain.enums.records import ProcessGroup as G
from aerona.domain.enums.relations import AppealKind, ContestEnd, ContestKind, ContestStake, InteractionKind, PersuasionAim
from aerona.domain.enums.tongues import LanguagePolicy, NumeralBase, WordRegister
from aerona.domain.enums.urban import MarketPlay


def chosen(key: str, enum: type[StrEnum]) -> FactSpec:
    return FactSpec(key, FactValue.ENUM, enum=enum)


def number(key: str, unit: FactUnit = FactUnit.COUNT) -> FactSpec:
    return FactSpec(key, FactValue.NUMBER, unit)


PAIR = (RoleSpec(R.ACTOR), RoleSpec(R.TARGET))
PAIR_SUBJECT = (RoleSpec(R.ACTOR), RoleSpec(R.SUBJECT))

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
    IncidentKindSpec(
        "language.base_changed",
        G.KNOWLEDGE,
        "{subject} began to count in {new} instead of {old}.",
        roles=(RoleSpec(R.SUBJECT), RoleSpec(R.TEACHER, required=False)),
        facts=(chosen("old", NumeralBase), chosen("new", NumeralBase)),
    ),
    IncidentKindSpec(
        "language.constructed",
        G.KNOWLEDGE,
        "{product} was made as a tongue with a regular grammar.",
        roles=(RoleSpec(R.PRODUCT), RoleSpec(R.ACTOR, required=False)),
    ),
    IncidentKindSpec(
        "language.revived",
        G.KNOWLEDGE,
        "{learner} brought {predecessor} back into speech as {product}.",
        roles=(RoleSpec(R.PRODUCT), RoleSpec(R.PREDECESSOR), RoleSpec(R.LEARNER)),
    ),
    IncidentKindSpec(
        "social.taboo_word",
        G.SOCIAL,
        "{actor} gave offence to {target} with a slip of the tongue: {register}.",
        roles=PAIR,
        facts=(chosen("register", WordRegister),),
    ),
    IncidentKindSpec(
        "script.imposed",
        G.KNOWLEDGE,
        "{authority} replaced the script of {subject} by law with {system:an} script.",
        roles=(RoleSpec(R.AUTHORITY), RoleSpec(R.SUBJECT), RoleSpec(R.ACTOR, required=False)),
        facts=(chosen("system", WritingSystem),),
    ),
    IncidentKindSpec(
        "script.revealed",
        G.FAITH,
        "{actor} gave {subject} {system:an} script, held sacred from then on.",
        roles=(RoleSpec(R.ACTOR), RoleSpec(R.SUBJECT), RoleSpec(R.LEARNER, required=False)),
        facts=(chosen("system", WritingSystem),),
    ),
    IncidentKindSpec(
        "language.policy_set",
        G.LAW,
        "{authority} made {subject} {policy} in its lands.",
        roles=(RoleSpec(R.AUTHORITY), RoleSpec(R.SUBJECT)),
        facts=(chosen("policy", LanguagePolicy),),
    ),
    IncidentKindSpec(
        "language.sign_born",
        G.KNOWLEDGE,
        "At {subject}, where many tongues meet on the roads, {product} arose as a shared sign language and reached {reach:place|places}.",
        roles=(RoleSpec(R.SUBJECT), RoleSpec(R.PRODUCT)),
        facts=(number("reach"),),
    ),
    IncidentKindSpec(
        "writing.altered",
        G.KNOWLEDGE,
        "An intrusion altered {subject}, kept as {medium:an}.",
        roles=(RoleSpec(R.SUBJECT),),
        facts=(chosen("medium", WritingMedium),),
    ),
    IncidentKindSpec(
        "tools.mortal.construct_language",
        G.KNOWLEDGE,
        "{actor} made the tongue {product} with {words:first word|first words}.",
        roles=(RoleSpec(R.ACTOR), RoleSpec(R.PRODUCT)),
        facts=(number("words"),),
    ),
    IncidentKindSpec(
        "tools.mortal.impose_script",
        G.LAW,
        "{actor} ordered {subject} written in {system:an} script.",
        roles=PAIR_SUBJECT,
        facts=(chosen("system", WritingSystem),),
    ),
    IncidentKindSpec(
        "tools.son.reveal_script",
        G.FAITH,
        "{actor} revealed {system:an} script for {subject}.",
        roles=PAIR_SUBJECT,
        facts=(chosen("system", WritingSystem),),
    ),
    IncidentKindSpec(
        "account.made",
        G.SOCIAL,
        "{subject} came to keep {kind:an}{about:? of #}, told through {through}.",
        roles=(RoleSpec(R.SUBJECT),),
        facts=(
            chosen("kind", AccountKind),
            chosen("medium", AccountMedium),
            FactSpec("through", FactValue.NAME),
            FactSpec("about", FactValue.NAME, required=False),
        ),
    ),
    IncidentKindSpec(
        "tools.mortal.compose_account",
        G.SOCIAL,
        "{actor} composed {kind:an} for {subject}, its stance toward the doers being {stance}.",
        roles=PAIR_SUBJECT,
        facts=(chosen("kind", AccountKind), chosen("stance", AccountStance)),
    ),
    IncidentKindSpec(
        "workshop.founded",
        G.MAKING,
        "{maker} raised {workshop:an}.",
        roles=(RoleSpec(R.MAKER),),
        facts=(chosen("workshop", WorkshopKind),),
    ),
    IncidentKindSpec(
        "tools.mortal.found_workshop",
        G.MAKING,
        "{actor} founded {workshop:an} at {place}.",
        roles=(RoleSpec(R.ACTOR), RoleSpec(R.PLACE)),
        facts=(chosen("workshop", WorkshopKind),),
    ),
    IncidentKindSpec(
        "pollution.rose",
        G.NATURE,
        "{pollutant} pollution in {place} rose to {level}.",
        roles=(RoleSpec(R.PLACE),),
        facts=(chosen("pollutant", Pollutant), number("level", FactUnit.PERCENT)),
    ),
    IncidentKindSpec(
        "credit.rescued",
        G.EXCHANGE,
        "{patron} took up the debts of {subject} on terms of {terms}.",
        roles=(RoleSpec(R.SUBJECT), RoleSpec(R.PATRON), RoleSpec(R.ACTOR, required=False)),
        facts=(number("terms", FactUnit.PERCENT),),
    ),
    IncidentKindSpec(
        "credit.repudiated",
        G.EXCHANGE,
        "{subject} declared its debts void, and{victim:? #} lost {voided}.",
        roles=(RoleSpec(R.SUBJECT), RoleSpec(R.VICTIM, required=False), RoleSpec(R.ACTOR, required=False)),
        facts=(number("voided", FactUnit.COIN),),
    ),
    IncidentKindSpec(
        "loan.rescheduled",
        G.EXCHANGE,
        "{patron} gave {subject} {epochs:more epoch|more epochs} to repay a loan.",
        roles=(RoleSpec(R.SUBJECT), RoleSpec(R.PATRON), RoleSpec(R.ACTOR, required=False)),
        facts=(number("epochs"),),
    ),
    IncidentKindSpec(
        "loan.sold",
        G.EXCHANGE,
        "{seller} sold a loan owed by {subject} to {buyer} for {price}.",
        roles=(RoleSpec(R.SUBJECT), RoleSpec(R.SELLER), RoleSpec(R.BUYER), RoleSpec(R.ACTOR, required=False)),
        facts=(number("price", FactUnit.COIN),),
    ),
    IncidentKindSpec(
        "loan.collateral_seized",
        G.EXCHANGE,
        "{patron} took {target}, pledged by {subject} for a loan it could not repay.",
        roles=(RoleSpec(R.SUBJECT), RoleSpec(R.PATRON), RoleSpec(R.TARGET)),
    ),
    IncidentKindSpec(
        "insurance.paid",
        G.EXCHANGE,
        "Insurance against {cover} loss paid {beneficiary} {paid}.",
        roles=(RoleSpec(R.BENEFICIARY),),
        facts=(chosen("cover", InsuranceCover), number("paid", FactUnit.WEALTH_POINTS)),
    ),
    IncidentKindSpec(
        "market.hoard_seized",
        G.EXCHANGE,
        "{authority} seized the hoard of {good} held back by {victim}, {units:unit|units} put back on sale.",
        roles=(RoleSpec(R.AUTHORITY), RoleSpec(R.VICTIM), RoleSpec(R.PLACE), RoleSpec(R.ACTOR, required=False)),
        facts=(chosen("good", CommodityKind), number("units")),
    ),
    IncidentKindSpec(
        "market.rumour_play",
        G.EXCHANGE,
        "{actor} spread a false report to move the price of {good} at {place}.",
        roles=(RoleSpec(R.ACTOR), RoleSpec(R.PLACE)),
        facts=(chosen("good", CommodityKind),),
    ),
    IncidentKindSpec(
        "tools.mortal.repudiate_debts",
        G.EXCHANGE,
        "{actor} voided the debts of {subject}, {voided} in all.",
        roles=PAIR_SUBJECT,
        facts=(number("voided", FactUnit.COIN),),
    ),
    IncidentKindSpec(
        "tools.mortal.rescue_polity",
        G.EXCHANGE,
        "{actor} took up the debts of {subject} on terms of {terms}.",
        roles=PAIR_SUBJECT,
        facts=(number("terms", FactUnit.PERCENT),),
    ),
    IncidentKindSpec(
        "tools.mortal.reschedule_loan",
        G.EXCHANGE,
        "{actor} put off a loan owed by {subject} by {epochs:epoch|epochs}.",
        roles=PAIR_SUBJECT,
        facts=(number("epochs"),),
    ),
    IncidentKindSpec(
        "tools.mortal.sell_loan",
        G.EXCHANGE,
        "{actor} sold a loan to {buyer} for {price}.",
        roles=(RoleSpec(R.ACTOR), RoleSpec(R.BUYER)),
        facts=(number("price", FactUnit.COIN),),
    ),
    IncidentKindSpec(
        "tools.mortal.insure",
        G.EXCHANGE,
        "{actor} took cover against {cover} loss from {patron}.",
        roles=(RoleSpec(R.ACTOR), RoleSpec(R.PATRON)),
        facts=(chosen("cover", InsuranceCover),),
    ),
    IncidentKindSpec(
        "tools.mortal.seize_hoards",
        G.EXCHANGE,
        "{actor} seized {hoards:hoard|hoards} at {place}.",
        roles=(RoleSpec(R.ACTOR), RoleSpec(R.PLACE)),
        facts=(number("hoards"),),
    ),
    IncidentKindSpec(
        "tools.mortal.play_market",
        G.EXCHANGE,
        "{actor} played the market of {place} in {good}: {play}.",
        roles=(RoleSpec(R.ACTOR), RoleSpec(R.PLACE)),
        facts=(chosen("play", MarketPlay), chosen("good", CommodityKind)),
    ),
    IncidentKindSpec(
        "route.contested",
        G.EXCHANGE,
        "{subject} between {origin} and {destination} became contested ground, its goods carried at greater loss while the sides fight for it.",
        roles=(RoleSpec(R.SUBJECT), RoleSpec(R.ORIGIN), RoleSpec(R.DESTINATION)),
    ),
    IncidentKindSpec(
        "route.season_closed",
        G.EXCHANGE,
        "{subject} closes each year in {season}, and its trade waits until the way opens again.",
        roles=(RoleSpec(R.SUBJECT),),
        facts=(FactSpec("season", FactValue.NAME),),
    ),
    IncidentKindSpec(
        "route.loss",
        G.EXCHANGE,
        "{subject} lost {units:unit|units} of {good} to {loss}.",
        roles=(RoleSpec(R.SUBJECT), RoleSpec(R.BENEFICIARY, required=False)),
        facts=(chosen("loss", TradeLoss), chosen("good", CommodityKind), number("units")),
    ),
    IncidentKindSpec(
        "convoy.stranded",
        G.EXCHANGE,
        "A convoy on {subject} was caught by {season} and waited it out, eating into its cargo.",
        roles=(RoleSpec(R.SUBJECT),),
        facts=(FactSpec("season", FactValue.NAME),),
    ),
    IncidentKindSpec(
        "convoy.quarantined",
        G.EXCHANGE,
        "A convoy on {subject} was held in quarantine at {place} while sickness ran there.",
        roles=(RoleSpec(R.SUBJECT), RoleSpec(R.PLACE)),
    ),
)
