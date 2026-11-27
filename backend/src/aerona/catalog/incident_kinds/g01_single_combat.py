from collections.abc import Mapping
from enum import StrEnum
from typing import Any

from aerona.catalog.incident_kinds.spec import FactSpec, IncidentKindSpec, RoleSpec
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.chronicle import ChronicleKind as K
from aerona.domain.enums.chronicle import FeedCategory as F
from aerona.domain.enums.ecology import SizeClass
from aerona.domain.enums.entity import EntityFlag, MortalRole
from aerona.domain.enums.environment import TerrainKind, WeatherKind
from aerona.domain.enums.gathering import CollectionKind as C
from aerona.domain.enums.intervention import Disaster
from aerona.domain.enums.military import CaptiveFate, DuelContext, DuelEnd, FeudStatus
from aerona.domain.enums.modifier import IncidentRole as R
from aerona.domain.enums.mortal import CrimeKind, DeathCause, PunishmentKind
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.quests import QuestAim, QuestObstacle, QuestReward, QuestScale, QuestTargetKind
from aerona.domain.enums.records import FactUnit as U
from aerona.domain.enums.records import FactValue, PlaceRule, ProcessClock
from aerona.domain.enums.records import ProcessGroup as G
from aerona.domain.enums.records import StepAction as A
from aerona.domain.enums.society import CreatureTrait
from aerona.domain.enums.war import WarCause

DUEL_ACTIONS = frozenset(
    {
        A.INSULT,
        A.PLEAD,
        A.CLOSE,
        A.FLEE,
        A.STRIKE,
        A.CUT,
        A.THRUST,
        A.SHOOT,
        A.THROW,
        A.CHARGE,
        A.FEINT,
        A.BLOCK,
        A.PARRY,
        A.DODGE,
        A.DISARM,
        A.FALL,
        A.RISE,
        A.GRAPPLE,
        A.BITE,
        A.THROW_DOWN,
        A.CHOKE,
        A.LOCK,
        A.YIELD,
        A.SPARE,
        A.FINISH,
    }
)
QUEST_DEEDS: Mapping[QuestAim, str] = {
    QuestAim.FIND: "{actor} found {target} and took it up.",
    QuestAim.RESTORE: "{actor} restored {target}.",
    QuestAim.DESTROY: "{actor} destroyed {target}.",
    QuestAim.FREE: "{actor} freed {target}.",
    QuestAim.BIND: "{actor} bound {target} for {beneficiary}.",
    QuestAim.REACH: "{actor} reached {target}.",
    QuestAim.LEARN: "{actor} recovered {target} and brought it back to {beneficiary}.",
    QuestAim.RETURN: "{actor} brought {target} back to {beneficiary}.",
    QuestAim.PROTECT: "{actor} kept {target} safe.",
    QuestAim.AVENGE: "{actor} took vengeance on {target}.",
    QuestAim.HUNT: "{actor} brought down one of {target}.",
    QuestAim.DELIVER: "{actor} brought {target} to {beneficiary}.",
    QuestAim.RECONCILE: "{actor} reconciled {beneficiary} with {target}.",
    QuestAim.PROVE: "{actor} proved themself against {target}.",
    QuestAim.RESOLVE: "{actor} resolved the open matter around {target}.",
}
FEUD_DEEDS: Mapping[str, tuple[str, tuple[R, ...]]] = {
    "abduct": ("Kin of {actor} carried off {victim} of {target}.", (R.VICTIM,)),
    "ambush": ("Kin of {actor} ambushed {victim} of {target} on the road.", (R.VICTIM,)),
    "assassinate": ("An avenger of {actor} murdered {victim} of {target}.", (R.VICTIM,)),
    "call_allies": ("{actor} called {ally} into the feud with {target}.", (R.ALLY,)),
    "demand_wergild": ("{giver} paid {receiver} compensation for its dead and the blood feud ended.", (R.GIVER, R.RECEIVER)),
    "destroy_property": ("Kin of {actor} destroyed goods and works of {target}.", ()),
    "escalate": ("The blood feud between {actor} and {target} turned into open war.", (R.ALLY,)),
    "mediated": ("The blood feud between {actor} and {target} was ended by mediation.", (R.MEDIATOR,)),
    "raid": ("Kin of {actor} raided {target} to avenge their dead.", (R.VICTIM,)),
    "raid_halls": ("Kin of {actor} raided {target}, and {leader} led them through {halls:hall|halls} of it.", (R.VICTIM, R.LEADER)),
    "seek_mediation": ("{actor} asked for mediation and its feud with {target} was settled by {mediator}.", (R.MEDIATOR,)),
    "amends": ("{giver} made amends to {receiver} and the feud ended.", (R.GIVER, R.RECEIVER)),
    "sworn_off": ("{actor} and {target} swore an oath to end their feud.", (R.ALLY,)),
}
FEUD_STEPS: Mapping[str, frozenset[A]] = {
    "abduct": frozenset({A.AVENGE, A.CARRY_OFF}),
    "ambush": frozenset({A.AVENGE}),
    "assassinate": frozenset({A.AVENGE}),
    "demand_wergild": frozenset({A.APOLOGISE, A.RECONCILE}),
    "destroy_property": frozenset({A.AVENGE}),
    "mediated": frozenset({A.RECONCILE}),
    "raid": frozenset({A.AVENGE}),
    "raid_halls": frozenset({A.AVENGE}),
    "seek_mediation": frozenset({A.RECONCILE}),
    "amends": frozenset({A.APOLOGISE, A.RECONCILE}),
    "sworn_off": frozenset({A.RECONCILE}),
}
OPTIONAL_FEUD_ROLES = frozenset({("mediated", R.MEDIATOR), ("raid", R.VICTIM), ("raid_halls", R.VICTIM)})
MANY_ROLES = frozenset({R.VICTIM, R.ALLY})
FEUD_FACTS: Mapping[str, tuple[str, ...]] = {
    "ambush": ("harm",),
    "assassinate": ("cause",),
    "demand_wergild": ("wergild", "status"),
    "destroy_property": ("prosperity_loss",),
    "escalate": ("war_cause",),
    "mediated": ("status",),
    "raid": ("harm", "prosperity_loss"),
    "raid_halls": ("harm", "prosperity_loss", "halls"),
    "seek_mediation": ("status",),
    "amends": ("amends", "status"),
    "sworn_off": ("status",),
}


def role(kind: R, *, required: bool = True, many: bool = False) -> RoleSpec:
    return RoleSpec(kind, required=required, many=many)


def node(key: str, *, required: bool = True) -> FactSpec:
    return FactSpec(key, FactValue.NODE, required=required)


def number(key: str, unit: U, *, required: bool = True) -> FactSpec:
    return FactSpec(key, FactValue.NUMBER, unit, required=required)


def chosen(key: str, enum: type[StrEnum], *, required: bool = True, named: str | None = None) -> FactSpec:
    return FactSpec(named or key, FactValue.ENUM, enum=enum, required=required)


FEUD_FACT_SPECS: Mapping[str, FactSpec] = {
    "harm": number("harm", U.HP),
    "cause": chosen("cause", DeathCause),
    "war_cause": chosen("cause", WarCause),
    "wergild": number("wergild", U.WEALTH_POINTS),
    "amends": number("amends", U.WEALTH_POINTS),
    "status": chosen("status", FeudStatus),
    "prosperity_loss": number("prosperity_loss", U.PERCENT),
    "halls": number("halls", U.COUNT),
}


def kind(key: str, template: str, *, roles: tuple[RoleSpec, ...] = (), facts: tuple[FactSpec, ...] = (), **extra: Any) -> IncidentKindSpec:
    return IncidentKindSpec(key, G.SINGLE_COMBAT, template, roles=roles, facts=facts, **extra)


def feud_kind(action: str) -> IncidentKindSpec:
    template, extra = FEUD_DEEDS[action]
    facts = tuple(FEUD_FACT_SPECS[key] for key in FEUD_FACTS.get(action, ()))
    added = tuple(role(item, required=(action, item) not in OPTIONAL_FEUD_ROLES, many=item in MANY_ROLES) for item in extra)
    roles = (role(R.ACTOR), role(R.TARGET), *added)
    return kind(
        f"vendetta.{action}",
        template,
        roles=roles,
        facts=(number("intensity", U.PERCENT), *facts),
        chronicle_kind=K.WAR,
        feed=F.WAR,
        steps=FEUD_STEPS.get(action, frozenset()),
    )


def quest_kind(aim: QuestAim) -> IncidentKindSpec:
    roles = (role(R.ACTOR), role(R.TARGET), role(R.BENEFICIARY), role(R.ALLY, required=False, many=True))
    facts = (
        chosen("aim", QuestAim),
        chosen("reward", QuestReward),
        chosen("scale", QuestScale),
        number("chance", U.PERCENT),
        number("quarrels_closed", U.COUNT, required=False),
    )
    return kind(
        f"heroes.quest_{aim.value}", QUEST_DEEDS[aim], roles=roles, facts=facts, clock=ProcessClock.MARCH, collection=C.HEROQUEST, chronicle_kind=K.ADVENTURE
    )


def quest_end(ending: str, template: str) -> IncidentKindSpec:
    roles = (role(R.ACTOR), role(R.TARGET, required=False))
    facts = (chosen("aim", QuestAim), chosen("obstacle", QuestObstacle), number("epochs", U.COUNT))
    return kind(f"heroes.quest_{ending}", template, roles=roles, facts=facts, clock=ProcessClock.MARCH, collection=C.HEROQUEST, chronicle_kind=K.ADVENTURE)


def sentence_kind(punishment: PunishmentKind) -> IncidentKindSpec:
    roles = (role(R.ACCUSED), role(R.JUDGE, required=False))
    facts = (chosen("crime", CrimeKind), chosen("punishment", PunishmentKind), number("severity", U.SEVERITY))
    told = "{accused} was sentenced for {crime}; the punishment: {punishment}."
    return kind(f"justice.{punishment.value}", told, roles=roles, facts=facts, collection=C.TRIAL)


def prisoner_kind(key: str, template: str, facts: tuple[FactSpec, ...] = (), *, home: bool = False, steps: frozenset[A] = frozenset()) -> IncidentKindSpec:
    roles = (role(R.ACTOR), role(R.SUBJECT), role(R.ORIGIN, required=home))
    return kind(f"prisoner.{key}", template, roles=roles, facts=facts, chronicle_kind=K.WAR, steps=steps)


def accused_kind(key: str, template: str) -> IncidentKindSpec:
    roles = (role(R.ACCUSED), role(R.PLACE), role(R.ACCUSER, required=False))
    return kind(key, template, roles=roles, facts=(number("suspects", U.COUNT),), place=PlaceRule.REQUIRED, collection=C.PERSECUTION)


KINDS: tuple[IncidentKindSpec, ...] = (
    kind(
        "beasts.risen",
        "{subject} rose among the {species}.",
        roles=(role(R.SUBJECT),),
        facts=(node("species"), number("hp", U.HP), number("danger", U.PERCENT)),
        collection=C.BEAST_ATTACK,
    ),
    kind(
        "beasts.tribute",
        "{giver} paid tribute to {receiver}.",
        roles=(role(R.RECEIVER), role(R.GIVER, many=True)),
        facts=(number("towns", U.COUNT), number("units", U.COUNT)),
        clock=ProcessClock.SEASON,
    ),
    kind(
        "beasts.raid",
        "{actor} fell on {victim}.",
        roles=(role(R.ACTOR), role(R.VICTIM)),
        facts=(number("population_lost", U.PEOPLE), number("head", U.COUNT), number("attacks", U.COUNT), number("scale", U.PERCENT)),
        place=PlaceRule.REQUIRED,
        clock=ProcessClock.INSTANT,
        collection=C.BEAST_ATTACK,
        terms=True,
    ),
    kind(
        "beasts.raid_treasure",
        "{actor} fell on {victim} and bore {treasure} to its hoard.",
        roles=(role(R.ACTOR), role(R.VICTIM)),
        facts=(number("population_lost", U.PEOPLE), number("head", U.COUNT), number("attacks", U.COUNT), number("scale", U.PERCENT), node("treasure")),
        place=PlaceRule.REQUIRED,
        clock=ProcessClock.INSTANT,
        collection=C.BEAST_ATTACK,
        terms=True,
    ),
    kind("beasts.shunned", "{actor} prowled but shunned the towns of the beast slayers.", roles=(role(R.ACTOR), role(R.TARGET, many=True))),
    kind(
        "beasts.carried_off",
        "{actor} carried {victim} off from {origin}.",
        roles=(role(R.ACTOR), role(R.VICTIM), role(R.ORIGIN)),
        steps=frozenset({A.CARRY_OFF}),
        place=PlaceRule.REQUIRED,
        clock=ProcessClock.INSTANT,
        collection=C.ABDUCTION,
    ),
    kind(
        "beasts.fallen",
        "{victim} is dead.",
        roles=(role(R.VICTIM), role(R.ACTOR, required=False)),
        facts=(number("hoard", U.COUNT), number("treasures", U.COUNT)),
        collection=C.BEAST_ATTACK,
    ),
    kind(
        "beasts.fallen_by",
        "{victim} was killed by {actor}.",
        roles=(role(R.VICTIM), role(R.ACTOR)),
        facts=(number("hoard", U.COUNT), number("treasures", U.COUNT)),
        collection=C.BEAST_ATTACK,
    ),
    kind(
        "beasts.worshipped",
        "The towns near the lair of {subject} began to pray to it.",
        roles=(role(R.SUBJECT), role(R.PRODUCT), role(R.MEMBER, required=False, many=True)),
        facts=(number("renown", U.RENOWN), number("terror", U.PERCENT)),
    ),
    kind(
        "captives.fates",
        "{actor} settled the fate of {count:captive|captives} of war: {fate}.",
        roles=(role(R.ACTOR), role(R.ORIGIN, required=False)),
        facts=(chosen("fate", CaptiveFate), number("count", U.PEOPLE)),
        chronicle_kind=K.WAR,
        feed=F.WAR,
    ),
    kind(
        "casualties.commander_risen",
        "{subject} rose from the ranks of {origin} to lead {instrument}.",
        roles=(role(R.SUBJECT), role(R.INSTRUMENT), role(R.ORIGIN)),
        facts=(chosen("role", MortalRole), number("warfare", U.KNOWLEDGE)),
        chronicle_kind=K.WAR,
    ),
    kind(
        "casualties.disaster_dead",
        "{subject} took {dead:named life|named lives}.",
        roles=(role(R.SUBJECT), role(R.VICTIM, many=True)),
        facts=(chosen("disaster", Disaster), number("dead", U.PEOPLE), number("severity", U.PERCENT)),
        feed=F.DISASTER,
    ),
    kind(
        "casualties.fate_shielded",
        "{subject} came back from the edge of death; their fate was shielded.",
        roles=(role(R.SUBJECT),),
        facts=(chosen("flag", EntityFlag),),
    ),
    kind(
        "casualties.veterans",
        "Veterans of old wars joined {subject}; the army was seasoned from its first day.",
        roles=(role(R.SUBJECT), role(R.OWNER)),
        facts=(number("experience_before", U.PERCENT), number("experience_after", U.PERCENT)),
        chronicle_kind=K.WAR,
    ),
    kind("challenge.civic", "Hard times taught {subject} new ways of ordering its people.", roles=(role(R.SUBJECT),), facts=(number("challenge", U.PERCENT),)),
    kind(
        "challenge.response",
        "{subject} met its trials and grew stronger for them.",
        roles=(role(R.SUBJECT),),
        facts=(number("challenge", U.PERCENT), number("asabiyya_gain", U.PERCENT)),
        terms=True,
    ),
    kind(
        "challenge.collapse",
        "{subject} buckled under more than it could bear.",
        roles=(role(R.SUBJECT),),
        facts=(number("challenge", U.PERCENT), number("asabiyya_loss", U.PERCENT), number("stability_loss", U.PERCENT), number("legitimacy_loss", U.PERCENT)),
        terms=True,
    ),
    kind(
        "contract.posted",
        "{actor} posted a bounty of {bounty:coin|coins} on {target}.",
        roles=(role(R.ACTOR), role(R.TARGET)),
        facts=(number("bounty", U.COIN), number("raids", U.COUNT)),
        collection=C.HUNT,
    ),
    kind(
        "contract.taken",
        "{actor} took the bounty on {target}.",
        roles=(role(R.ACTOR), role(R.TARGET), role(R.GIVER)),
        facts=(number("bounty", U.COIN),),
        collection=C.HUNT,
    ),
    kind(
        "contract.slain",
        "{actor} slew {victim} and claimed a bounty of {bounty:coin|coins}.",
        roles=(role(R.ACTOR), role(R.VICTIM), role(R.GIVER, required=False)),
        facts=(number("bounty", U.COIN), number("renown", U.RENOWN), number("study", U.PERCENT)),
        steps=frozenset({A.FINISH}),
        collection=C.HUNT,
    ),
    kind(
        "contract.failed",
        "{actor} gave up the hunt for {target}, badly hurt.",
        roles=(role(R.ACTOR), role(R.TARGET)),
        facts=(number("wound", U.HP), number("study", U.PERCENT), number("bounty", U.COIN)),
        collection=C.HUNT,
    ),
    kind(
        "duel.honour",
        "{actor} called {target} out to settle a matter of honour.",
        roles=(role(R.ACTOR), role(R.TARGET)),
        facts=(number("grievance", U.STANDING),),
        collection=C.DUEL,
    ),
    kind(
        "duel.bout",
        "{actor} and {opponent} fought a duel of {exchanges:exchange|exchanges}; it ended in {end}.",
        roles=(role(R.ACTOR), role(R.OPPONENT), role(R.WITNESS, required=False, many=True)),
        facts=(
            chosen("context", DuelContext),
            number("exchanges", U.COUNT),
            chosen("end", DuelEnd),
            chosen("terrain", TerrainKind, required=False),
            chosen("weather", WeatherKind, required=False),
            node("winner_weapon", required=False),
            node("loser_weapon", required=False),
        ),
        steps=DUEL_ACTIONS,
        clock=ProcessClock.ROUNDS,
        collection=C.DUEL,
        chronicle_kind=K.WAR,
        terms=True,
    ),
    kind(
        "grudges.enmity",
        "The grudge between {patron} reached the mortals: {actor} and {opponent} became enemies.",
        roles=(role(R.ACTOR), role(R.OPPONENT), role(R.PATRON, many=True)),
        facts=(chosen("cause", WarCause),),
        chronicle_kind=K.WAR,
    ),
    kind(
        "grudges.holy_war",
        "The grudge between {patron} turned into a holy war between {actor} and {opponent}.",
        roles=(role(R.ACTOR), role(R.OPPONENT), role(R.PATRON, many=True)),
        facts=(chosen("cause", WarCause),),
        chronicle_kind=K.WAR,
    ),
    kind(
        "heroes.apprentice",
        "{teacher} began training {learner} as an apprentice.",
        roles=(role(R.TEACHER), role(R.LEARNER), role(R.INSTRUMENT, required=False)),
        facts=(number("age", U.YEARS),),
        chronicle_kind=K.LINEAGE,
    ),
    kind(
        "heroes.apprentice_armed",
        "{teacher} began training {learner} as an apprentice and entrusted {instrument} to them.",
        roles=(role(R.TEACHER), role(R.LEARNER), role(R.INSTRUMENT)),
        facts=(number("age", U.YEARS),),
        chronicle_kind=K.LINEAGE,
    ),
    kind("creation.shaped", "{product} came into being by the Creator's will.", roles=(role(R.PRODUCT),), chronicle_kind=K.CREATOR_HAND),
    kind(
        "mortals.shaped",
        "{child} came into being among {origin} by the Creator's will.",
        roles=(role(R.CHILD), role(R.ORIGIN)),
        feed=F.LIFE,
        chronicle_kind=K.BIRTH,
    ),
    kind(
        "heroes.birth",
        "A new hero, {child}, arose among {origin}.",
        roles=(role(R.CHILD), role(R.ORIGIN)),
        facts=(number("power", U.STRENGTH),),
        feed=F.LIFE,
        chronicle_kind=K.BIRTH,
    ),
    kind("heroes.companions", "{actor} and {ally} became companions.", roles=(role(R.ACTOR), role(R.ALLY)), chronicle_kind=K.ADVENTURE),
    kind(
        "heroes.quest_start",
        "{actor} set out on a quest to {aim} {target}.",
        roles=(role(R.ACTOR), role(R.TARGET)),
        facts=(chosen("aim", QuestAim), chosen("target_kind", QuestTargetKind), chosen("obstacle", QuestObstacle), chosen("reward", QuestReward)),
        collection=C.HEROQUEST,
        chronicle_kind=K.ADVENTURE,
    ),
    *(quest_kind(aim) for aim in QuestAim),
    quest_end("death", "{actor} gave their life on a quest to {aim}."),
    quest_end("failed", "{actor} was beaten back at the end of a quest to {aim}."),
    quest_end("abandoned", "{actor} searched for {epochs:epoch|epochs} but came back empty-handed from a quest to {aim}."),
    kind(
        "heroes.recalled",
        "{actor} was called back from a quest to {aim}.",
        roles=(role(R.ACTOR), role(R.TARGET, required=False)),
        facts=(chosen("aim", QuestAim),),
        chronicle_kind=K.ADVENTURE,
    ),
    kind(
        "heroism.age_change",
        "{actor} slew {victim}, and the balance of its world changed.",
        roles=(role(R.ACTOR), role(R.VICTIM), role(R.PRODUCT)),
        facts=(chosen("flag", EntityFlag), number("power", U.STRENGTH)),
        chronicle_kind=K.AGE_CHANGE,
        collection=C.BEAST_ATTACK,
    ),
    kind(
        "heroism.armor_save",
        "{subject} was beaten by {opponent}, but {instrument} saved them from death; they withdrew gravely wounded.",
        roles=(role(R.SUBJECT), role(R.OPPONENT), role(R.INSTRUMENT)),
        facts=(number("hp_lost", U.HP), number("protection_before", U.PERCENT), number("protection_after", U.PERCENT)),
        collection=C.BEAST_ATTACK,
    ),
    kind(
        "heroism.defeat",
        "{victim} fell before {opponent}.",
        roles=(role(R.VICTIM), role(R.OPPONENT), role(R.PRODUCT), role(R.PATRON, required=False)),
        facts=(chosen("cause", DeathCause),),
        steps=frozenset({A.DIE}),
        collection=C.BEAST_ATTACK,
    ),
    kind(
        "heroism.legendary_weapon",
        "{subject} became legendary after {victories:victory|victories} in the hands of {owner}.",
        roles=(role(R.SUBJECT), role(R.OWNER), role(R.OPPONENT)),
        facts=(number("victories", U.COUNT), number("might", U.STRENGTH)),
    ),
    kind(
        "heroism.rewind",
        "{subject} died but turned time back; {opponent} will see it once more.",
        roles=(role(R.SUBJECT), role(R.OPPONENT)),
        facts=(chosen("trait", CreatureTrait),),
    ),
    kind(
        "heroism.victory",
        "{actor} faced {opponent} and killed it.",
        roles=(role(R.ACTOR), role(R.OPPONENT), role(R.PATRON, required=False), role(R.PRODUCT, required=False)),
        facts=(number("danger", U.PERCENT), number("charisma_gain", U.STANDING)),
        steps=frozenset({A.FINISH}),
        collection=C.BEAST_ATTACK,
    ),
    kind(
        "heroism.drove_back",
        "{actor} faced {opponent} and drove it back.",
        roles=(role(R.ACTOR), role(R.OPPONENT), role(R.PATRON, required=False), role(R.PRODUCT, required=False)),
        facts=(number("danger", U.PERCENT), number("charisma_gain", U.STANDING)),
        steps=frozenset({A.STRIKE}),
        collection=C.BEAST_ATTACK,
    ),
    *(sentence_kind(punishment) for punishment in PunishmentKind),
    kind(
        "monsters.emerged",
        "{subject} climbed out of the deep mines of {region}.",
        roles=(role(R.SUBJECT),),
        facts=(node("region"), number("mined", U.PERCENT), chosen("size", SizeClass)),
        place=PlaceRule.REQUIRED,
    ),
    kind(
        "monsters.herd_raid",
        "{actor} fell on the herds of {victim} and carried off {head:head|head}.",
        roles=(role(R.ACTOR), role(R.VICTIM)),
        facts=(number("head", U.COUNT),),
        place=PlaceRule.REQUIRED,
        clock=ProcessClock.INSTANT,
        collection=C.BEAST_ATTACK,
    ),
    kind(
        "monsters.raid",
        "{actor} raided {victim}; {lost_pct} in a hundred of its people were lost.",
        roles=(role(R.ACTOR), role(R.VICTIM)),
        facts=(
            number("lost_pct", U.PERCENT),
            number("population_before", U.PEOPLE),
            number("population_after", U.PEOPLE),
            number("prosperity_loss", U.PERCENT),
        ),
        place=PlaceRule.REQUIRED,
        clock=ProcessClock.INSTANT,
        collection=C.BEAST_ATTACK,
        terms=True,
    ),
    kind(
        "monsters.void_roamed",
        "{subject} crossed from {origin} to {destination}.",
        roles=(role(R.SUBJECT), role(R.ORIGIN), role(R.DESTINATION)),
        facts=(number("danger", U.PERCENT),),
        clock=ProcessClock.VOYAGE,
    ),
    prisoner_kind("escaped", "{subject} escaped from the captivity of {actor}.", (number("agility", U.STRENGTH), number("intellect", U.STRENGTH))),
    prisoner_kind("executed", "{actor} executed its prisoner {subject}; {origin} swore vengeance.", (chosen("cause", HarmCause),), home=True),
    prisoner_kind("married", "{subject} was married into the house of {actor}."),
    prisoner_kind(
        "ransomed",
        "{origin} paid {actor} a ransom of {ransom:coin|coins} for {subject}; the prisoner returned home.",
        (number("ransom", U.COIN),),
        home=True,
        steps=frozenset({A.PAY, A.BUY_FREEDOM}),
    ),
    prisoner_kind("released", "{actor} thought well of the people of {subject} and let the prisoner go."),
    prisoner_kind(
        "turncoat", "After {epochs_held:epoch|epochs} of captivity {subject} pledged to {actor} and joined their side.", (number("epochs_held", U.COUNT),)
    ),
    prisoner_kind("ward_home", "{subject}, raised at the court of {actor}, came of age and went home.", (number("age", U.YEARS),)),
    kind(
        "prisoner.freed",
        "{subject} was freed from captivity when the captors scattered.",
        roles=(role(R.SUBJECT),),
        facts=(node("captor"),),
        chronicle_kind=K.RESCUE,
    ),
    kind(
        "prisoner.freed_by_decree",
        "{subject} was freed from {actor} by decree.",
        roles=(role(R.AUTHORITY, required=False), role(R.SUBJECT), role(R.ACTOR)),
        chronicle_kind=K.RESCUE,
    ),
    *(feud_kind(action) for action in FEUD_DEEDS),
    kind(
        "vendetta.faded",
        "The old feud between {actor} and {opponent} faded with the generations.",
        roles=(role(R.ACTOR), role(R.OPPONENT)),
        facts=(number("generations", U.COUNT), number("since", U.COUNT)),
        chronicle_kind=K.WAR,
    ),
    kind(
        "vendetta.outlawed",
        "The law ended the feud between {actor} and {opponent}.",
        roles=(role(R.ACTOR), role(R.OPPONENT)),
        facts=(chosen("law", LawKind),),
        chronicle_kind=K.WAR,
    ),
    accused_kind("witchcraft.accused", "{accused} of {place} was accused of witchcraft."),
    accused_kind("witchcraft.accused_by_diviners", "{accused} of {place} was accused of witchcraft, named by its diviners."),
    accused_kind("witchcraft.accused_by_rumour", "{accused} of {place} was accused of witchcraft, named by rumour."),
    kind(
        "witchcraft.hunt",
        "A witch hunt took hold of {place}.",
        roles=(role(R.PLACE),),
        facts=(number("fervour", U.PERCENT), number("accusations", U.COUNT)),
        place=PlaceRule.REQUIRED,
        clock=ProcessClock.SEASON,
        collection=C.PERSECUTION,
    ),
    kind(
        "witchcraft.hunt_over",
        "The witch hunt in {place} came to an end after {accused:accusation|accusations}.",
        roles=(role(R.PLACE),),
        facts=(number("accused", U.COUNT),),
        place=PlaceRule.REQUIRED,
        collection=C.PERSECUTION,
    ),
)
