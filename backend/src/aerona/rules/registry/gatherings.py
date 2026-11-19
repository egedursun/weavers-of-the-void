from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span

M = RuleGroup.MORTALS
S = RuleGroup.SETTLEMENTS
H = RuleGroup.RECORDS


@dataclass(frozen=True)
class GatheringRules(Spanned):
    per_world_max: int = rule(40, 0, 1000, M, "Gatherings the engine holds on one world each epoch")
    funeral_renown: int = rule(30, 0, 100, M, "Renown of the dead above which a funeral is held rather than a wake")
    anniversary_pct: int = rule(10, 0, 100, M, "Chance each epoch a married couple keeps an anniversary with their kin (%)")
    birth_pct: int = rule(25, 0, 100, M, "Chance each named birth is marked by a gathering of the family (%)")
    festival_pct: int = rule(40, 0, 100, S, "Chance each epoch a community keeping a festival holds it as a gathering (%)")
    fair_pct: int = rule(30, 0, 100, S, "Chance each epoch a market settlement holds a fair (%)")
    council_pct: int = rule(35, 0, 100, M, "Chance each epoch a ruler calls a council of the realm (%)")
    summit_pct: int = rule(15, 0, 100, M, "Chance each epoch a world holds a summit of several realms (%)")
    summit_parties: int = rule(3, 2, 20, M, "Realms a summit needs before it meets")
    summit_hops: int = rule(4, 0, 50, M, "Lands a realm may lie from the summit's host and still be called")
    tournament_pct: int = rule(20, 0, 100, M, "Chance each epoch a realm holds a tournament (%)")
    hunt_pct: int = rule(20, 0, 100, M, "Chance each epoch a noble house head holds a hunt (%)")
    games_pct: int = rule(25, 0, 100, S, "Chance each epoch a settlement with an arena holds games (%)")
    exhibition_pct: int = rule(20, 0, 100, S, "Chance each epoch a settlement with a museum or gallery holds an exhibition (%)")
    trade_fair_pct: int = rule(20, 0, 100, S, "Chance each epoch a settlement with an exchange or guildhall holds a trade fair (%)")
    sport_match_pct: int = rule(30, 0, 100, S, "Chance each epoch a settlement with a stadium holds a match (%)")
    network_gathering_pct: int = rule(15, 0, 100, M, "Chance each epoch a network gathers its members through itself (%)")
    realm_gathering_pct: int = rule(15, 0, 100, M, "Chance each epoch the keeper of a made realm gathers its dwellers (%)")
    initiation_pct: int = rule(50, 0, 100, M, "Chance a mortal who joins an order or society this epoch is initiated with a gathering (%)")
    performance_pct: int = rule(25, 0, 100, S, "Chance each epoch a settlement with a theatre holds a performance (%)")
    pilgrimage_sacredness: int = rule(50, 0, 100, M, "Sacredness of a place that draws an organised pilgrimage")
    pilgrimage_pct: int = rule(30, 0, 100, M, "Chance each epoch a sacred place draws an organised pilgrimage (%)")
    procession_zeal: int = rule(55, 0, 100, M, "Zeal of a cult above which it leads processions")
    procession_pct: int = rule(25, 0, 100, M, "Chance each epoch a zealous cult leads a procession (%)")
    feast_pct: int = rule(20, 0, 100, M, "Chance each epoch a noble or wealthy mortal holds a feast (%)")
    feast_wealth: int = rule(60, 0, 100, M, "Wealth a commoner needs before holding a feast")
    guests_max: int = rule(12, 1, 200, M, "Guests one gathering invites at most")
    attend_base_pct: int = rule(55, 0, 100, M, "Chance an invited guest comes before friendship and distance (%)")
    attend_friendship_pct: int = rule(40, 0, 200, M, "Attendance added at full friendship with the host (%)")
    attend_obligation_pct: int = rule(30, 0, 100, M, "Attendance added for guests who owe the host (kin, vassals, members) (%)")
    attend_hop_pct: int = rule(12, 0, 100, M, "Attendance lost for each land between guest and host (%)")
    mingle_pairs: int = rule(8, 0, 200, M, "Pairs of attendees who spend time together at a gathering")
    mingle_friendship: int = rule(4, 0, 100, M, "Friendship each pair of attendees gains from their time together")
    mingle_familiarity: int = rule(6, 0, 100, M, "Familiarity each pair of attendees gains")
    romance_pct: int = rule(8, 0, 100, M, "Chance a pair of unwed adult attendees begins a romance (%)")
    romance_gain: int = rule(20, 0, 100, M, "Romance a pair gains when one begins at a gathering")
    betrothal_romance: int = rule(60, 0, 100, M, "Romance between unwed attendees at which a match is proposed and made")
    secret_pct: int = rule(6, 0, 100, M, "Chance an attendee learns a secret another attendee keeps (%)")
    scheme_progress: int = rule(10, 0, 100, M, "Progress a scheme makes when its owner and an agent meet at a gathering")
    strike_boost_pct: int = rule(25, 0, 200, M, "Better chance a murder scheme has against a target who attends a gathering (%)")
    massacre_pct: int = rule(3, 0, 100, M, "Chance a host kills hated guests at the gathering it holds (%)")
    massacre_rivalry: int = rule(70, 0, 100, M, "Rivalry of a host with a guest that can turn a gathering into a massacre")
    massacre_hp: int = rule(80, 0, 200, M, "Harm the host's people deal each guest they turn on")
    massacre_shameful_pct: int = rule(40, 0, 100, M, "Share of the massacre chance left when the host's culture holds killing a guest shameful (%)")
    quarrel_rivalry: int = rule(40, 0, 100, M, "Rivalry between two attendees at which their meeting turns to a quarrel")
    quarrel_shift: int = rule(6, 0, 100, M, "Rivalry a quarrel adds between the two")
    feast_cost: int = rule(4, 0, 10000, M, "Treasury coin a feast costs its host for each guest")
    feast_prestige: int = rule(3, 0, 100, M, "Prestige of a feast for each guest who comes")
    feast_food: int = rule(2, 0, 1000, M, "Units of food a feast serves each guest from its host's stores")
    host_honour: int = rule(4, 0, 100, M, "Honour a host gains from a well attended gathering")
    guest_opinion: int = rule(5, 0, 100, M, "Friendship guests gain toward a generous host")
    bout_hp: int = rule(12, 0, 200, M, "Harm a contestant takes when beaten in a bout")
    bout_renown: int = rule(8, 0, 100, M, "Renown the champion of a tournament or games wins")
    hunt_beast_pct: int = rule(20, 0, 100, M, "Chance a hunt meets a beast of its land (%)")
    hunt_hp: int = rule(25, 0, 200, M, "Harm a beast deals the hunter it turns on")
    hunt_renown: int = rule(6, 0, 100, M, "Renown a hunter gains for a beast faced and survived")
    performer_renown: int = rule(5, 0, 100, M, "Renown performers gain from a performance")
    coronation_legitimacy: int = rule(6, 0, 100, M, "Legitimacy a realm gains when its ruler is crowned before many guests")
    summit_friendship: int = rule(10, 0, 100, M, "Friendship each pair of realms at a summit gains")
    summit_treaty_friendship: int = rule(20, -100, 100, M, "Friendship two realms at a summit need before they sign a peace there")
    summit_treaty_years: int = span(20, 1, 2500, M, "Years a peace signed at a summit runs")
    festival_cohesion: int = rule(3, 0, 100, S, "Cohesion a community gains from a festival held as a gathering")
    fair_wealth: int = rule(3, 0, 100, S, "Wealth the merchants of a settlement gain from a fair")
    pilgrim_sacredness: int = rule(2, 0, 100, M, "Sacredness a place gains from an organised pilgrimage")
    procession_zeal_gain: int = rule(2, 0, 100, M, "Zeal a cult gains from a procession")
    council_loyalty: int = rule(3, 0, 100, M, "Friendship of the council toward the ruler who called it")
    execution_stress: int = rule(4, 0, 100, M, "Stress a public execution lays on those who watch it")
    milestone_memory: int = rule(20, 0, 100, M, "Strength of the memory a milestone gathering leaves with those who came")
    thought_intensity: int = rule(30, 0, 100, M, "Intensity of the thought a gathering leaves with those who came")
    election_pct: int = rule(25, 0, 100, M, "Chance each epoch a realm that rules by assembly holds an election (%)")
    election_legitimacy: int = rule(6, 0, 100, M, "Legitimacy an election gives the realm that holds it")
    strike_worker_pct: int = rule(10, 0, 100, S, "Worker share a settlement needs before its workers strike (%)")
    strike_satisfaction: int = rule(35, 0, 100, S, "Worker satisfaction at or below which the workers strike")
    strike_pct: int = rule(30, 0, 100, S, "Chance each epoch discontented workers strike (%)")
    strike_prosperity_loss: int = rule(4, 0, 100, S, "Prosperity a settlement loses to a strike")
    strike_satisfaction_gain: int = rule(8, 0, 100, S, "Satisfaction the workers win by a strike")
    rally_unrest: int = rule(40, 0, 100, S, "Unrest above which a settlement's folk gather in rallies")
    rally_pct: int = rule(25, 0, 100, S, "Chance each epoch a restless settlement holds a rally (%)")
    rally_unrest_gain: int = rule(3, 0, 100, S, "Unrest a rally stirs")
    convention_pct: int = rule(20, 0, 100, S, "Chance each epoch a settlement with an office tower holds a convention (%)")
    convention_renown: int = rule(3, 0, 100, M, "Renown each professional at a convention gains")
    launch_pct: int = rule(25, 0, 100, S, "Chance each epoch a settlement with a spaceport holds a launch (%)")
    launch_prestige: int = rule(4, 0, 100, S, "Prestige a launch gives its settlement")
    broadcast_pct: int = rule(40, 0, 100, S, "Chance each epoch a settlement with a broadcast tower holds a broadcast (%)")
    broadcast_cohesion: int = rule(2, 0, 100, S, "Cohesion a broadcast gives the community that sends it")

    @property
    def summit_treaty_epochs(self) -> int:
        return self.epochs(self.summit_treaty_years)


@dataclass(frozen=True)
class CollectionRules(Spanned):
    join_window_years: int = span(5, 0, 2500, H, "Years within which a new incident joins an open history of its kind")
    close_after_years: int = span(10, 1, 2500, H, "Years without a new incident after which a history is closed")
    purge_at: int = rule(4, 1, 1000, H, "Executions in one realm in one epoch that make a purge")

    @property
    def join_window(self) -> int:
        return self.epochs(self.join_window_years)

    @property
    def close_after(self) -> int:
        return self.epochs(self.close_after_years)
