from aerona.catalog.incident_kinds.spec import FactSpec, IncidentKindSpec, RoleSpec, per_value
from aerona.domain.enums.chronicle import ChronicleKind as K
from aerona.domain.enums.chronicle import FeedCategory as F
from aerona.domain.enums.collective import Tincture
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.entity import EntityType as T
from aerona.domain.enums.environment import TerrainKind, WeatherKind
from aerona.domain.enums.honours import VeteranGrant
from aerona.domain.enums.law_depth import KillMethod, MoleHuntOutcome
from aerona.domain.enums.military import DefenderAction, MutinyOutcome, OutcomeClass, SabotageKind, SackChoice, SiegeAction, StarvationStage, Tactic, UnitKind
from aerona.domain.enums.modifier import IncidentRole as R
from aerona.domain.enums.operations import CrewStation, EchelonOrder
from aerona.domain.enums.records import FactUnit as U
from aerona.domain.enums.records import FactValue as V
from aerona.domain.enums.records import PlaceRule, ProcessClock, StepLocus
from aerona.domain.enums.records import ProcessGroup as G
from aerona.domain.enums.records import StepAction as A
from aerona.domain.enums.settlement import DistrictKind
from aerona.domain.enums.titles import TitleTenure
from aerona.domain.enums.war import WarCause, WarEnding
from aerona.domain.enums.world_view import WarTerrain

ARMY = frozenset({T.ARMY})
BATTLE_STEPS = frozenset(
    {
        A.DEPLOY,
        A.ADVANCE,
        A.HOLD,
        A.VOLLEY,
        A.WHEEL,
        A.FLANK,
        A.CHARGE,
        A.ROUT,
        A.RALLY,
        A.REINFORCE,
        A.WITHDRAW,
        A.ENCIRCLE,
        A.COUNTER,
        A.PURSUE,
        A.PERFORM_RITE,
        A.PILLAGE,
        A.TAKE_CAPTIVES,
        A.TAKE_STANDARD,
        A.FALL,
        A.BREACH,
        A.STORM,
        A.BOMBARD,
        A.FIRE,
        A.IGNITE,
        A.EXPLODE,
        A.FLOOD,
        A.VENT,
        A.CRASH,
        A.COLLAPSE,
        A.BREAK,
    }
)
STRUCK_VEHICLES = frozenset({A.FIRE, A.IGNITE, A.EXPLODE, A.FLOOD, A.VENT, A.CRASH, A.ROUT, A.COLLAPSE, A.BREAK})
SIEGE_STEPS = frozenset({A.BOMBARD, A.UNDERMINE, A.HOLD, A.STORM, A.NEGOTIATE, A.SORTIE, A.REPAIR, A.RAISE, A.BREACH, A.REINFORCE, A.SURRENDER})


def number(key: str, unit: U, *, required: bool = True) -> FactSpec:
    return FactSpec(key, V.NUMBER, unit=unit, required=required)


def node(key: str, *, required: bool = True) -> FactSpec:
    return FactSpec(key, V.NODE, required=required)


def enum(key: str, kind: type, *, required: bool = True) -> FactSpec:
    return FactSpec(key, V.ENUM, enum=kind, required=required)


def name(key: str) -> FactSpec:
    return FactSpec(key, V.NAME)


def role(kind: R, *, required: bool = True, many: bool = False, accepts: frozenset[T] = frozenset()) -> RoleSpec:
    return RoleSpec(kind, accepts, required=required, many=many)


def kind(
    key: str,
    template: str,
    roles: tuple[RoleSpec, ...],
    facts: tuple[FactSpec, ...] = (),
    *,
    place: PlaceRule = PlaceRule.WHEN_KNOWN,
    clock: ProcessClock = ProcessClock.INSTANT,
    chronicle: K = K.WAR,
    feed: F | None = F.WAR,
    terms: bool = False,
    magnitude: int = 0,
    place_kind: StepLocus | None = None,
    steps: frozenset[A] = frozenset(),
) -> IncidentKindSpec:
    return IncidentKindSpec(
        key,
        G.BATTLES,
        template,
        roles=roles,
        facts=facts,
        steps=steps,
        place=place,
        place_kind=place_kind,
        clock=clock,
        chronicle_kind=chronicle,
        feed=feed,
        terms=terms,
        magnitude=magnitude,
    )


BATTLE_FACTS = (
    node("war"),
    node("battle", required=False),
    number("winner_start", U.PEOPLE),
    number("loser_start", U.PEOPLE),
    number("winner_lost", U.PEOPLE),
    number("loser_lost", U.PEOPLE),
    number("wounded", U.PEOPLE),
    number("captured", U.PEOPLE),
    number("missing", U.PEOPLE),
    number("deserted", U.PEOPLE),
    number("gap", U.PERCENT),
    enum("outcome_class", OutcomeClass),
    enum("winner_tactic", Tactic),
    enum("loser_tactic", Tactic),
    enum("terrain", TerrainKind, required=False),
    enum("weather", WeatherKind, required=False),
    enum("ground", WarTerrain, required=False),
)
BATTLE_ROLES = (
    role(R.ACTOR),
    role(R.OPPONENT),
    role(R.MEMBER, required=False, many=True, accepts=ARMY),
    role(R.LEADER, required=False, many=True),
    role(R.ALLY, required=False, many=True),
)
LOSSES = "; {loser_lost:soldier|soldiers} of {opponent} and {winner_lost} of {actor} were lost, and {captured:soldier was|soldiers were} led away captive."


def battle(key: str, lead: str) -> IncidentKindSpec:
    return kind(
        key, lead + LOSSES, BATTLE_ROLES, BATTLE_FACTS, clock=ProcessClock.ROUNDS, terms=True, magnitude=60, place_kind=StepLocus.REGION, steps=BATTLE_STEPS
    )


WAR_ENDINGS = {
    WarEnding.VICTORY: "{war} ended: {actor} won over {opponent}.",
    WarEnding.CONQUEST: "{war} ended: {actor} conquered {opponent}.",
    WarEnding.TRIBUTE: "{war} ended: {actor} won, and {opponent} will pay tribute.",
    WarEnding.EXHAUSTION: "{war} ended in exhaustion between {actor} and {opponent}.",
    WarEnding.PEACE: "{war} ended in a peace between {actor} and {opponent}.",
    WarEnding.WHITE_PEACE: "{war} ended with no victor; {actor} and {opponent} were both exhausted.",
    WarEnding.BETRAYAL: "{war} ended in betrayal between {actor} and {opponent}.",
    WarEnding.SAME_FRONT: "{war} ended as {actor} and {opponent} came to stand on the same side.",
    WarEnding.NO_SIDE_LEFT: "{war} ended: neither {actor} nor {opponent} was left to fight it.",
    WarEnding.MIRACLE: "{war} ended by a miracle between {actor} and {opponent}.",
}
MUTINIES = {
    MutinyOutcome.GRUMBLING: "The soldiers of {subject} grew restless, hungry and unpaid.",
    MutinyOutcome.REFUSAL: "{subject} refused to march further and halted where it stood.",
    MutinyOutcome.DEPOSED: "The soldiers of {subject} rose against their commander and cast them out.",
    MutinyOutcome.BANDITRY: "{subject} turned to plunder the lands it was raised to guard.",
    MutinyOutcome.TURNCOAT: "{subject} went over to the enemy.",
}
SACKS = {
    SackChoice.MERCY: "{actor} spared {target}.",
    SackChoice.SACK: (
        "{actor} sacked {target}: {dead:person|people} died, {captives:person was|people were} "
        "led away captive and {relics:treasure was|treasures were} carried off."
    ),
    SackChoice.RAZE: "{actor} razed {target}: {dead:person|people} died, {captives:person was|people were} enslaved and its districts burned.",
}
MOLES = {
    MoleHuntOutcome.CAUGHT: "{actor}, spymaster of {authority}, hunted for moles and caught one.",
    MoleHuntOutcome.CLEARED: "{actor}, spymaster of {authority}, hunted for moles, accused {accused} and cleared them.",
    MoleHuntOutcome.PURGED: "{actor}, spymaster of {authority}, hunted for moles and purged {accused}, who was innocent.",
    MoleHuntOutcome.DEFECTED: "{actor}, spymaster of {authority}, hunted for moles and drove {accused}, who was innocent, to flee to the enemy.",
}
SPY = (role(R.ACTOR), role(R.TARGET))

KINDS: tuple[IncidentKindSpec, ...] = (
    kind(
        "battlefield.haunted", "{subject} rose from the mass grave of {battlefield}.", (role(R.SUBJECT),), (node("battlefield"),), chronicle=K.WORLD, feed=None
    ),
    kind(
        "espionage.assassination",
        "Agents of {actor} reached {victim}, ruler of {target}, and killed them by {method}.",
        (*SPY, role(R.VICTIM)),
        (enum("method", KillMethod),),
        chronicle=K.INTRIGUE,
        feed=None,
        magnitude=50,
    ),
    kind(
        "espionage.assassination_hidden",
        "{victim}, ruler of {target}, died, and no one saw the hand behind it.",
        (*SPY, role(R.VICTIM)),
        (enum("method", KillMethod),),
        chronicle=K.INTRIGUE,
        feed=None,
        magnitude=40,
    ),
    kind(
        "espionage.assassination_wounded",
        "An assassin of {actor} struck at {victim}, ruler of {target}, and left them wounded.",
        (*SPY, role(R.VICTIM)),
        chronicle=K.INTRIGUE,
        feed=None,
    ),
    kind(
        "espionage.blackmail",
        "{actor} held the secrets of the rulers of {target} over them.",
        (*SPY, role(R.VICTIM, required=False)),
        (number("paid", U.WEALTH_POINTS, required=False), number("intel_spent", U.PERCENT)),
        chronicle=K.INTRIGUE,
        feed=None,
    ),
    kind(
        "espionage.caught",
        "Spies of {actor} were caught in {target}.",
        (*SPY, role(R.SUBJECT, required=False)),
        (number("exposure", U.PERCENT),),
        chronicle=K.INTRIGUE,
        feed=None,
    ),
    kind(
        "espionage.counterfeit",
        "False coins of {currency} from the agents of {actor} spread through the markets of {target}.",
        SPY,
        (name("currency"), number("trust_lost", U.PERCENT)),
        chronicle=K.INTRIGUE,
        feed=None,
        terms=True,
    ),
    kind(
        "espionage.defected",
        "{subject} defected, carrying {secrets:secret|secrets}.",
        (role(R.SUBJECT), role(R.OPPONENT, required=False), role(R.RECEIVER, required=False)),
        (number("secrets", U.COUNT),),
    ),
    kind(
        "espionage.incite",
        "Agents of {actor} stirred unrest in {target}.",
        (*SPY, role(R.SUBJECT, required=False)),
        (number("unrest", U.PERCENT),),
        chronicle=K.INTRIGUE,
        feed=None,
        terms=True,
    ),
    *(
        kind(
            f"espionage.mole_{outcome.value}",
            template,
            (role(R.ACTOR), role(R.AUTHORITY), role(R.ACCUSED, required=outcome is not MoleHuntOutcome.CAUGHT)),
            (enum("outcome", MoleHuntOutcome),),
        )
        for outcome, template in MOLES.items()
    ),
    kind(
        "espionage.incite_uprising",
        "Agents of {actor} stirred unrest in {target} until its people rose against their rulers.",
        (*SPY, role(R.SUBJECT, required=False)),
        (number("unrest", U.PERCENT),),
        chronicle=K.INTRIGUE,
        feed=None,
        terms=True,
    ),
    kind(
        "espionage.intel",
        "The agents of {actor} learned the secrets of {target}, and {aims:war aim lies|war aims lie} open to them.",
        SPY,
        (number("intel", U.PERCENT), number("aims", U.COUNT)),
        chronicle=K.INTRIGUE,
        feed=None,
        terms=True,
    ),
    kind("espionage.network_founded", "{actor} began building a secret agent network inside {target}.", SPY, chronicle=K.INTRIGUE, feed=None),
    *per_value(
        "espionage.sabotage.",
        SabotageKind,
        kind(
            "espionage.sabotage.",
            "The agents of {actor} struck at {target}: {sabotage}.",
            SPY,
            (
                enum("sabotage", SabotageKind),
                number("food_burned", U.COUNT, required=False),
                number("wall_damage", U.PERCENT, required=False),
                number("severity", U.SEVERITY, required=False),
                number("harm", U.PERCENT, required=False),
                enum("district", DistrictKind, required=False),
            ),
            chronicle=K.INTRIGUE,
            feed=None,
            terms=True,
        ),
    ),
    kind(
        "espionage.stole_design",
        "The agents of {actor} carried off the design of {design} from {target}.",
        SPY,
        (name("design"),),
        chronicle=K.INTRIGUE,
        feed=None,
    ),
    kind(
        "espionage.stole_knowledge",
        "The agents of {actor} stole the knowledge of {knowledge} from {target}.",
        SPY,
        (node("knowledge"),),
        chronicle=K.INTRIGUE,
        feed=None,
    ),
    kind(
        "espionage.stole_technique",
        "The agents of {actor} carried off the secret of {technique} from {target}.",
        SPY,
        (enum("technique", Technique),),
        chronicle=K.INTRIGUE,
        feed=None,
    ),
    kind(
        "honours.disbanded",
        "{actor} disbanded {unit}, whose standard bore {honours:honour|honours}.",
        (role(R.ACTOR),),
        (name("unit"), number("honours", U.COUNT), number("renown_lost", U.RENOWN)),
        terms=True,
    ),
    kind(
        "honours.nicknamed",
        "{unit} came to be called {nickname}.",
        (role(R.OWNER, required=False),),
        (name("unit"), name("nickname"), number("honours", U.COUNT)),
    ),
    kind(
        "honours.reconstituted",
        "{unit} was raised again from its veterans.",
        (role(R.SUBJECT, accepts=ARMY),),
        (name("unit"), number("esprit", U.PERCENT)),
        terms=True,
    ),
    kind(
        "logistics.collapsed",
        "{subject} pressed on past the end of its supply, and its offensive collapsed.",
        (role(R.SUBJECT, accepts=ARMY), role(R.OWNER)),
        (number("morale_lost", U.PERCENT),),
        clock=ProcessClock.MARCH,
        terms=True,
    ),
    kind(
        "logistics.culminated",
        "{subject} outran its supply and paused its offensive for {pause:season|seasons}.",
        (role(R.SUBJECT, accepts=ARMY), role(R.OWNER)),
        (number("pause", U.SEASONS),),
        clock=ProcessClock.MARCH,
        terms=True,
    ),
    kind(
        "logistics.depot_founded",
        "{actor} stocked a depot of {supplies:supply|supplies} in {region}.",
        (role(R.ACTOR),),
        (node("region"), number("supplies", U.COUNT), number("capacity", U.COUNT)),
        place=PlaceRule.REQUIRED,
        place_kind=StepLocus.REGION,
    ),
    kind(
        "logistics.field_depot",
        "{subject} founded a field depot in {region} to feed its advance.",
        (role(R.SUBJECT, accepts=ARMY),),
        (node("region"), number("supplies", U.COUNT), number("capacity", U.COUNT)),
        place=PlaceRule.REQUIRED,
        place_kind=StepLocus.REGION,
        clock=ProcessClock.MARCH,
    ),
    kind(
        "theatres.misjudged",
        "{actor} misread its fronts and sent its reserves where the danger was smaller.",
        (role(R.ACTOR), role(R.LEADER, required=False)),
        (number("reserves", U.PEOPLE), number("priority", U.PERCENT)),
    ),
    kind("unit_types.drawn", "{actor} raised a new kind of soldier: {product}.", (role(R.ACTOR), role(R.PRODUCT))),
    kind("veterans.association", "The veterans of {actor} banded into {product}.", (role(R.ACTOR), role(R.PRODUCT)), chronicle=K.WORLD, feed=None),
    kind(
        "veterans.granted",
        "{actor} gave its {veterans:veteran|veterans} the grant of {grant}.",
        (role(R.ACTOR), role(R.PRODUCT, required=False)),
        (enum("grant", VeteranGrant), number("veterans", U.PEOPLE), node("region", required=False)),
    ),
    *(
        battle(f"war.battle.{outcome}", lead)
        for outcome, lead in (
            ("field_victory", "{actor} won the field against {opponent} in {war}"),
            ("great_victory", "{actor} won a great victory over {opponent} in {war}"),
            ("siege_repulsed", "{actor} threw back the assault of {opponent} in {war}"),
            ("siege_breached", "{actor} carried the assault on the defences of {opponent} in {war}"),
            ("siege_starvation", "{actor} took the starved defences of {opponent} in {war}"),
        )
    ),
    kind(
        "war.battle.refused",
        "{opponent} saw {actor} coming in {war} and would not give battle.",
        (role(R.ACTOR), role(R.OPPONENT), role(R.MEMBER, required=False, many=True, accepts=ARMY)),
        (node("war"), number("margin", U.PERCENT)),
        clock=ProcessClock.MARCH,
        terms=True,
    ),
    kind(
        "war.call_betrayed",
        "{actor} would not march when {victim} called; the alliance is betrayed.",
        (role(R.ACTOR), role(R.VICTIM)),
        chronicle=K.DIPLOMACY,
        steps=frozenset({A.BETRAY, A.REFUSE}),
    ),
    kind(
        "war.cap_closed_fronts",
        "{war} between {actor} and {opponent} ended in exhaustion as the fronts multiplied; the two sides made a truce.",
        (role(R.ACTOR), role(R.OPPONENT)),
        (node("war"),),
    ),
    kind(
        "war.cap_closed_idle",
        "{war} between {actor} and {opponent}, with no battle fought for {idle:epoch|epochs}, ended in exhaustion; the two sides made a truce.",
        (role(R.ACTOR), role(R.OPPONENT)),
        (node("war"), number("idle", U.COUNT)),
    ),
    kind(
        "war.debasement",
        "{actor} clipped its coin {currency} to pay its soldiers; its purity fell by {purity_lost} and its trust by {trust_lost}.",
        (role(R.ACTOR),),
        (name("currency"), number("purity_lost", U.PERCENT), number("trust_lost", U.PERCENT), number("added", U.COIN), number("raised", U.COIN)),
        chronicle=K.TRADE,
        terms=True,
    ),
    kind(
        "war.duel_decree",
        "By decree, {actor} and {opponent} fought a duel, and {victor} won.",
        (role(R.ACTOR), role(R.OPPONENT)),
        (node("victor"), node("war", required=False)),
    ),
    kind(
        "war.god_duel",
        "Before the gods of {war}, {actor} and {opponent} fought as champions, and {victor} won; the war moved {score:point|points}.",
        (role(R.ACTOR), role(R.OPPONENT)),
        (node("war"), node("victor"), number("score", U.COUNT)),
        terms=True,
        magnitude=50,
    ),
    kind(
        "war.trial_by_combat",
        "{actor} challenged {opponent} for {realm} in a trial by combat, and {victor} won.",
        (role(R.ACTOR), role(R.OPPONENT)),
        (node("realm"), node("victor")),
        magnitude=40,
    ),
    *(
        kind(
            f"war.ended_{ending.value}",
            template,
            (role(R.ACTOR), role(R.OPPONENT), role(R.SUBJECT, required=False, accepts=ARMY)),
            (node("war"), enum("ending", WarEnding)),
            terms=True,
            magnitude=70,
        )
        for ending, template in WAR_ENDINGS.items()
    ),
    kind(
        "war.fought_on",
        "{actor} refused the terms of the victor in {war} and fought on.",
        (role(R.ACTOR),),
        (node("war"), number("weariness", U.PERCENT)),
        terms=True,
    ),
    kind(
        "war.incitement_reaped",
        "{war}, which {actor} had incited, ended after {battles:battle|battles}.",
        (role(R.ACTOR), role(R.TARGET, required=False)),
        (node("war"), number("battles", U.COUNT)),
    ),
    kind(
        "war.loan",
        "{borrower} borrowed {principal:coin|coins} from {lender} to keep its soldiers paid.",
        (role(R.BORROWER), role(R.LENDER)),
        (number("principal", U.COIN), number("lent_wealth", U.WEALTH_POINTS)),
        chronicle=K.DEBT,
        terms=True,
    ),
    kind(
        "war.mercenaries_hired",
        "{actor} hired {receiver} by contract; {instrument} now marches for pay.",
        (role(R.ACTOR), role(R.RECEIVER), role(R.INSTRUMENT, accepts=ARMY)),
        (number("wage", U.COIN),),
        steps=frozenset({A.HIRE}),
    ),
    kind(
        "war.mercenaries_turned",
        "{actor}, left unpaid by {victim}, broke its contract and left.",
        (role(R.ACTOR, accepts=ARMY), role(R.VICTIM), role(R.RECEIVER, required=False)),
        (number("owed", U.COIN, required=False),),
    ),
    *(
        kind(
            f"war.mutiny.{outcome.value}",
            template,
            (role(R.SUBJECT, accepts=ARMY), role(R.OWNER, required=False)),
            (enum("outcome", MutinyOutcome), number("mutiny", U.PERCENT)),
            clock=ProcessClock.MARCH,
            terms=True,
            steps=frozenset({A.DEPOSE}) if outcome is MutinyOutcome.DEPOSED else frozenset(),
        )
        for outcome, template in MUTINIES.items()
    ),
    kind(
        "war.outbreak",
        (
            "War broke out between {actor} and {target}: {attacker_army} "
            "({attacker_soldiers:soldier|soldiers}) faces {defender_army} ({defender_soldiers:soldier|soldiers})."
        ),
        (role(R.ACTOR), role(R.TARGET)),
        (
            node("war"),
            node("attacker_army"),
            node("defender_army"),
            number("attacker_soldiers", U.PEOPLE),
            number("defender_soldiers", U.PEOPLE),
            enum("cause", WarCause),
        ),
        magnitude=60,
    ),
    kind(
        "war.partisans",
        "Partisans struck at the occupying armies of {victim}; {fallen:soldier|soldiers} fell.",
        (role(R.VICTIM),),
        (number("fallen", U.PEOPLE),),
        place=PlaceRule.REQUIRED,
        place_kind=StepLocus.REGION,
    ),
    *(
        kind(
            f"war.sack.{choice.value}",
            template,
            (role(R.ACTOR), role(R.TARGET)),
            (enum("choice", SackChoice), number("dead", U.PEOPLE), number("captives", U.PEOPLE), number("relics", U.COUNT)),
            place=PlaceRule.REQUIRED,
            place_kind=StepLocus.SETTLEMENT,
            magnitude=60,
        )
        for choice, template in SACKS.items()
    ),
    kind(
        "war.sea_battle",
        "At sea the ships of {actor} beat those of {opponent}, sank {sunk:vessel|vessels} and closed its harbours.",
        (role(R.ACTOR), role(R.OPPONENT), role(R.MEMBER, required=False, many=True, accepts=ARMY)),
        (number("sunk", U.COUNT), node("winner_fleet"), node("loser_fleet")),
        clock=ProcessClock.ROUNDS,
        steps=STRUCK_VEHICLES,
        terms=True,
    ),
    kind(
        "war.made_barren",
        "The conquerors from {actor} made the fields of {victim} barren.",
        (role(R.ACTOR), role(R.VICTIM)),
        (number("depth", U.PERCENT),),
        place=PlaceRule.REQUIRED,
        place_kind=StepLocus.REGION,
        terms=True,
    ),
    kind(
        "war.fleet_storm",
        "The {weather} struck the fleet of {subject}, and {lost:vessel was|vessels were} lost.",
        (role(R.SUBJECT, accepts=ARMY), role(R.OWNER)),
        (enum("weather", WeatherKind), number("lost", U.COUNT)),
        clock=ProcessClock.VOYAGE,
        steps=STRUCK_VEHICLES,
        terms=True,
    ),
    kind("war.separate_peace", "{actor} made a separate peace with {opponent} and left {war}.", (role(R.ACTOR), role(R.OPPONENT)), (node("war"),)),
    kind(
        "war.siege.relieved",
        "{actor} came to the relief of {target}; the besiegers broke camp and the siege was lifted.",
        (role(R.ACTOR, accepts=ARMY), role(R.TARGET), role(R.OPPONENT, accepts=ARMY)),
        (number("relief_soldiers", U.PEOPLE), number("besiegers", U.PEOPLE)),
        place=PlaceRule.REQUIRED,
        place_kind=StepLocus.SETTLEMENT,
        clock=ProcessClock.SEASON,
    ),
    kind(
        "war.siege.season",
        "In season {seasons} of the siege of {target}, {actor} chose to {action}, and the defenders chose to {defence}.",
        (role(R.ACTOR), role(R.TARGET), role(R.MEMBER, required=False, accepts=ARMY)),
        (
            node("war"),
            number("seasons", U.COUNT),
            enum("action", SiegeAction),
            enum("defence", DefenderAction),
            number("walls", U.PERCENT),
            number("breaches", U.COUNT),
            number("supplies", U.PERCENT),
            number("sally_dead", U.PEOPLE),
            enum("hunger", StarvationStage),
        ),
        place=PlaceRule.REQUIRED,
        place_kind=StepLocus.SETTLEMENT,
        clock=ProcessClock.SEASON,
        steps=SIEGE_STEPS,
        terms=True,
    ),
    kind(
        "war.siege.surrender",
        "{target} surrendered to {actor} after {seasons:season|seasons} of siege in {war}, its hunger at {hunger}; {dead:person|people} died in the sack.",
        (role(R.ACTOR), role(R.TARGET)),
        (node("war"), number("seasons", U.COUNT), enum("hunger", StarvationStage), number("dead", U.PEOPLE)),
        place=PlaceRule.REQUIRED,
        place_kind=StepLocus.SETTLEMENT,
        clock=ProcessClock.SEASON,
        magnitude=60,
    ),
    kind(
        "war.terror",
        "After the {deed} by {actor}, fear spread through {victim}; other realms took note.",
        (role(R.ACTOR), role(R.VICTIM)),
        (name("deed"), node("war")),
    ),
    kind(
        "war.terror_hardened",
        "After the {deed} by {actor}, {victim} only hardened; other realms took note.",
        (role(R.ACTOR), role(R.VICTIM)),
        (name("deed"), node("war")),
    ),
    kind(
        "war.uprising_redirected",
        "{actor} defied the rule of {authority}; the revolt became an open war with {target}.",
        (role(R.ACTOR), role(R.AUTHORITY), role(R.TARGET)),
    ),
    kind(
        "war.weary_peace",
        "{war} ended because one side was worn out by war and sued for peace.",
        (role(R.ACTOR, required=False), role(R.OPPONENT)),
        (node("war"), number("weariness", U.PERCENT, required=False)),
    ),
    kind(
        "warfare.army_stood_down",
        "{subject} stood down: {returned:soldier|soldiers} without a war went home.",
        (role(R.SUBJECT, accepts=ARMY), role(R.OWNER, required=False)),
        (number("returned", U.PEOPLE),),
    ),
    kind(
        "tools.mortal.army",
        "{actor} called {count:person|people} to arms: {product}.",
        (role(R.ACTOR), role(R.PRODUCT, accepts=ARMY)),
        (number("count", U.PEOPLE),),
        feed=F.WAR,
    ),
    kind(
        "tools.mortal.commander",
        "{leader} took command of {subject}.",
        (role(R.LEADER), role(R.SUBJECT, accepts=ARMY), role(R.ACTOR)),
        (number("morale", U.PERCENT),),
    ),
    kind(
        "tools.mortal.defend_system",
        "{actor} hardened the defences of {target}.",
        (role(R.ACTOR), role(R.TARGET, required=False)),
        (number("security", U.PERCENT),),
        chronicle=K.WORLD,
        feed=None,
    ),
    kind("tools.mortal.draft_unit_type", "{actor} set out a new kind of soldier for {owner}: {product}.", (role(R.ACTOR), role(R.OWNER), role(R.PRODUCT))),
    kind(
        "tools.mortal.hunt_moles",
        "{actor} hunted for moles at the court of {authority}: {caught:mole was|moles were} caught, {purged} purged and {cleared} cleared.",
        (role(R.ACTOR), role(R.AUTHORITY)),
        (number("caught", U.COUNT), number("purged", U.COUNT), number("cleared", U.COUNT)),
        chronicle=K.WORLD,
        feed=None,
    ),
    kind(
        "tools.mortal.man_station",
        "{actor} set {count:hand|hands} at the {station} station on {subject}.",
        (role(R.ACTOR), role(R.SUBJECT, accepts=frozenset({T.VESSEL}))),
        (enum("station", CrewStation), number("count", U.PEOPLE)),
        chronicle=K.CIVILIZATION,
        feed=None,
    ),
    kind(
        "tools.mortal.order_formation",
        "{actor} gave {formation} the order to {order}.",
        (role(R.ACTOR), role(R.SUBJECT, required=False)),
        (name("formation"), enum("order", EchelonOrder)),
        chronicle=K.ORDER,
        feed=None,
    ),
    kind(
        "tools.mortal.seize_failed",
        "{actor} tried to seize {target} but was wounded and fled.",
        (role(R.ACTOR), role(R.TARGET), role(R.OWNER, required=False)),
        (number("mine", U.STRENGTH), number("theirs", U.STRENGTH)),
        chronicle=K.ADVENTURE,
        feed=None,
    ),
    kind(
        "tools.mortal.seize_repelled",
        "{actor} tried to seize {target}, but {owner} drove them back.",
        (role(R.ACTOR), role(R.TARGET), role(R.OWNER, many=True)),
        (number("mine", U.STRENGTH), number("theirs", U.STRENGTH)),
        chronicle=K.RESOURCE,
        feed=None,
    ),
    kind(
        "tools.mortal.seized",
        "{actor} seized {target}.",
        (role(R.ACTOR), role(R.TARGET), role(R.VICTIM, required=False)),
        (number("mine", U.STRENGTH), number("theirs", U.STRENGTH)),
        chronicle=K.ADVENTURE,
        feed=None,
    ),
    kind(
        "tools.mortal.spies",
        "Spies were placed among {target}.",
        (role(R.ACTOR), role(R.TARGET)),
        (number("wits", U.STRENGTH), number("watch", U.STRENGTH)),
        chronicle=K.INTRIGUE,
        feed=None,
    ),
    kind(
        "tools.mortal.spies_caught",
        "The spies of {actor} were caught among {target}; the network was broken.",
        (role(R.ACTOR), role(R.TARGET)),
        (number("wits", U.STRENGTH), number("watch", U.STRENGTH)),
        chronicle=K.INTRIGUE,
        feed=None,
    ),
    kind(
        "tools.mortal.take_arms",
        "{actor} took new arms for {subject} on a field of {field}.",
        (role(R.ACTOR), role(R.SUBJECT)),
        (enum("field", Tincture),),
        chronicle=K.CIVILIZATION,
        feed=None,
    ),
    kind(
        "tools.mortal.title_seized",
        "{actor} {tenure} the title {subject}.",
        (role(R.ACTOR), role(R.SUBJECT)),
        (enum("tenure", TitleTenure),),
        chronicle=K.WORLD,
        feed=None,
    ),
    kind("tools.mortal.war", "{actor} declared war on {target}.", (role(R.ACTOR), role(R.TARGET)), (enum("cause", WarCause),), magnitude=60),
    kind(
        "military.stack_modernised",
        "{owner} retrained {soldiers:soldier|soldiers} of {subject} from {from_kind} to {to_kind}.",
        (role(R.SUBJECT, accepts=ARMY), role(R.OWNER)),
        (enum("from_kind", UnitKind), enum("to_kind", UnitKind), number("soldiers", U.PEOPLE)),
        place=PlaceRule.NONE,
        clock=ProcessClock.SEASON,
    ),
)
