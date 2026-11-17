from aerona.catalog.incident_kinds.spec import FactSpec, IncidentKindSpec, RoleSpec
from aerona.domain.enums.chronicle import ChronicleKind as K
from aerona.domain.enums.chronicle import FeedCategory as F
from aerona.domain.enums.entity import EntityType as T
from aerona.domain.enums.environment import WeatherKind
from aerona.domain.enums.modifier import IncidentRole as R
from aerona.domain.enums.records import FactUnit, FactValue, PlaceRule, ProcessClock, StepLocus
from aerona.domain.enums.records import ProcessGroup as G
from aerona.domain.enums.records import StepAction as A
from aerona.domain.enums.vehicles import VehicleDomain, VehicleFrame

VESSEL = frozenset({T.VESSEL})
REALM = frozenset({T.POLITY, T.SETTLEMENT, T.PEOPLE, T.FACTION, T.CULT, T.MORTAL})
ENGAGED = frozenset(
    {
        A.MANOEUVRE,
        A.TAKE_POSITION,
        A.FIRE,
        A.RAM,
        A.BOARD,
        A.REPEL,
        A.IGNITE,
        A.EXTINGUISH,
        A.FLOOD,
        A.PUMP,
        A.REPAIR_UNDERWAY,
        A.JETTISON,
        A.LAUNCH_CRAFT,
        A.RAISE_SHIELD,
        A.LOSE_SHIELD,
        A.VENT,
        A.LOSE_POWER,
        A.CRASH,
        A.EXPLODE,
        A.SINK,
        A.STRIKE_COLOURS,
        A.ESCAPE,
        A.DRIFT,
        A.CLOSE,
        A.STRIKE,
        A.PARRY,
        A.YIELD,
        A.DIE,
    }
)
FOUGHT = (
    FactSpec("domain", FactValue.ENUM, enum=VehicleDomain),
    FactSpec("rounds", FactValue.NUMBER, unit=FactUnit.COUNT),
    FactSpec("hits_given", FactValue.NUMBER, unit=FactUnit.COUNT),
    FactSpec("hits_taken", FactValue.NUMBER, unit=FactUnit.COUNT),
    FactSpec("power", FactValue.NUMBER, unit=FactUnit.STRENGTH),
    FactSpec("foe_power", FactValue.NUMBER, unit=FactUnit.STRENGTH),
)
SIDES = (RoleSpec(R.ACTOR, VESSEL), RoleSpec(R.OPPONENT, VESSEL), RoleSpec(R.WITNESS, required=False, many=True))


def engagement(key: str, template: str) -> IncidentKindSpec:
    return IncidentKindSpec(
        key,
        G.VESSELS,
        template,
        roles=SIDES,
        facts=FOUGHT,
        steps=ENGAGED,
        place=PlaceRule.WHEN_KNOWN,
        place_kind=StepLocus.REGION,
        clock=ProcessClock.ROUNDS,
        terms=True,
        chronicle_kind=K.WAR,
        feed=F.WAR,
        magnitude=40,
    )


KINDS: tuple[IncidentKindSpec, ...] = (
    IncidentKindSpec(
        "admiralty.commissioned",
        G.VESSELS,
        "The admiralty of {actor} paid {cost:coin|coins} and laid down {laid:new ship|new ships} on the {frame} frame at {yard}.",
        roles=(RoleSpec(R.ACTOR, REALM),),
        facts=(
            FactSpec("laid", FactValue.NUMBER, unit=FactUnit.COUNT),
            FactSpec("cost", FactValue.NUMBER, unit=FactUnit.COIN),
            FactSpec("frame", FactValue.ENUM, enum=VehicleFrame),
            FactSpec("yard", FactValue.NODE),
        ),
        place=PlaceRule.REQUIRED,
        place_kind=StepLocus.SETTLEMENT,
        clock=ProcessClock.BUILDING,
        terms=True,
        chronicle_kind=K.WAR,
        feed=F.WAR,
    ),
    IncidentKindSpec(
        "admiralty.fleet_exposed",
        G.VESSELS,
        "The hidden ships of {actor} were found out: it had kept {hidden:ton|tons} of shipping beyond the fleet limit of {treaty}.",
        roles=(RoleSpec(R.ACTOR, REALM),),
        facts=(FactSpec("hidden", FactValue.NUMBER, unit=FactUnit.TONS), FactSpec("treaty", FactValue.NODE)),
        steps=frozenset({A.REVEAL}),
        place=PlaceRule.NONE,
        clock=ProcessClock.INSTANT,
        chronicle_kind=K.WAR,
        feed=F.WAR,
    ),
    IncidentKindSpec(
        "seafaring.ghost_ship",
        G.VESSELS,
        "{subject} went down, and it is still seen on the routes it sailed, though no living crew sails it.",
        roles=(RoleSpec(R.SUBJECT, VESSEL),),
        place=PlaceRule.WHEN_KNOWN,
        place_kind=StepLocus.REGION,
        clock=ProcessClock.VOYAGE,
        feed=F.VOYAGE,
        magnitude=50,
    ),
    IncidentKindSpec(
        "seafaring.prize_taken",
        G.VESSELS,
        "{actor} took {target} as a prize; {prize_crew:sailor went|sailors went} aboard and {prize_money:coin was|coins were} paid out.",
        roles=(RoleSpec(R.ACTOR, VESSEL), RoleSpec(R.TARGET, VESSEL), RoleSpec(R.OWNER, REALM, required=False), RoleSpec(R.RECEIVER, required=False)),
        facts=(FactSpec("prize_money", FactValue.NUMBER, unit=FactUnit.COIN), FactSpec("prize_crew", FactValue.NUMBER, unit=FactUnit.PEOPLE)),
        place=PlaceRule.WHEN_KNOWN,
        place_kind=StepLocus.REGION,
        clock=ProcessClock.INSTANT,
        terms=True,
        chronicle_kind=K.WAR,
        feed=F.WAR,
    ),
    engagement("seafaring.sea_fight", "{actor} beat {opponent} in {rounds:round|rounds} of fighting, landing {hits_given:hit|hits} and taking {hits_taken}."),
    engagement("seafaring.escaped", "{opponent} broke off and got away from {actor} after {rounds:round|rounds} of fighting."),
    engagement("seafaring.struck", "{opponent} yielded to {actor} after {rounds:round|rounds} of fighting and {hits_taken:hit|hits} taken."),
    engagement("seafaring.boarded", "{actor} boarded {opponent} and took it after {rounds:round|rounds} of fighting."),
    engagement("seafaring.foundered", "{opponent} was lost under the fire of {actor} after {rounds:round|rounds} of fighting."),
    engagement("seafaring.blew_up", "{opponent} blew up in its fight with {actor} in round {rounds}."),
    engagement("seafaring.downed", "{opponent} fell and was lost in its fight with {actor} in round {rounds}."),
    IncidentKindSpec(
        "seafaring.lost_in_battle",
        G.VESSELS,
        "{subject} was lost in the sea battle of {fleet}.",
        roles=(RoleSpec(R.SUBJECT, VESSEL),),
        facts=(FactSpec("fleet", FactValue.NODE),),
        place=PlaceRule.WHEN_KNOWN,
        place_kind=StepLocus.REGION,
        clock=ProcessClock.INSTANT,
        chronicle_kind=K.WAR,
        feed=F.WAR,
    ),
    IncidentKindSpec(
        "seafaring.storm",
        G.VESSELS,
        "{subject} rode out the {weather} on its voyage; the hull lost {damage} of its condition and {lost:crew member was|crew were} lost.",
        roles=(RoleSpec(R.SUBJECT, VESSEL),),
        facts=(
            FactSpec("weather", FactValue.ENUM, enum=WeatherKind),
            FactSpec("damage", FactValue.NUMBER, unit=FactUnit.PERCENT),
            FactSpec("lost", FactValue.NUMBER, unit=FactUnit.PEOPLE),
        ),
        place=PlaceRule.WHEN_KNOWN,
        place_kind=StepLocus.REGION,
        clock=ProcessClock.VOYAGE,
        terms=True,
        chronicle_kind=K.DISASTER,
        feed=F.VOYAGE,
    ),
    IncidentKindSpec(
        "seafaring.wreck",
        G.VESSELS,
        "{subject} was wrecked by the {weather}.",
        roles=(RoleSpec(R.SUBJECT, VESSEL),),
        facts=(FactSpec("weather", FactValue.ENUM, enum=WeatherKind),),
        place=PlaceRule.WHEN_KNOWN,
        place_kind=StepLocus.REGION,
        clock=ProcessClock.VOYAGE,
        chronicle_kind=K.DISASTER,
        feed=F.VOYAGE,
        magnitude=30,
    ),
)
