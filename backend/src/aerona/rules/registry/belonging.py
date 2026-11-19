from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span

M = RuleGroup.MIND
P = RuleGroup.POLITY
R = RuleGroup.RELIGION_AND_LANGUAGE


@dataclass(frozen=True)
class IdentityRules:
    base_salience: int = rule(30, 0, 100, M, "Salience every identity layer drifts back toward when nothing stirs it")
    decay_pct: int = rule(20, 0, 100, M, "Share of the gap to the resting salience an identity closes each epoch (%)")
    holy_war: int = rule(25, 0, 100, M, "Faith salience a community gains while its realm fights a holy war")
    famine: int = rule(20, 0, 100, M, "Class salience a community gains in a year of hunger in its land")
    invasion: int = rule(25, 0, 100, M, "People and realm salience a community gains while an enemy army stands in its land")
    strike: int = rule(15, 0, 100, M, "Profession salience a community gains while its guilds strike")
    rhetoric: int = rule(10, 0, 100, M, "Salience a community gains in the layer a movement there preaches")
    segregation: int = rule(
        10,
        0,
        100,
        M,
        "People and class salience a community gains when its districts keep peoples or ranks apart, as a foreign quarter or the quarters of its castes",
    )
    crossing: int = rule(
        10, 0, 100, M, "People and faith salience a community loses for marriages across those lines among its folk, and for guilds whose members cross them"
    )
    mortal_pct: int = rule(70, 0, 100, M, "Share of its home community's salience a mortal's identity takes each epoch (%)")
    in_group_opinion: int = rule(15, 0, 100, M, "Opinion two holders gain for an identity they share, at full salience")
    cohesion: int = rule(15, 0, 100, P, "Loyalty a realm member gains from a fully salient identity with the realm")
    separatism: int = rule(20, 0, 100, P, "Loyalty a realm member loses when a fully salient people or locality differs from its ruler's")
    mobilisation_pct: int = rule(20, 0, 100, P, "Share more or less levy a realm raises as realm salience stands above or below the resting salience (%)")
    revolt_cut: int = rule(
        15, 0, 100, P, "Threshold a crowd of a town loses when the line its realm divides along sets the town apart from its ruler, at full salience"
    )
    fault_at: int = rule(55, 0, 100, M, "Salience from which a layer becomes the line along which a realm divides")
    memory_at: int = rule(50, 0, 100, M, "Salience from which the identity group of a place keeps its own account of what happened there")


@dataclass(frozen=True)
class PeerRules:
    min_children: int = rule(2, 1, 100, M, "Named children of one town and rank that form a peer group")
    play_facet: int = rule(2, 0, 20, M, "Facet a child's play shifts each epoch")
    play_skill: int = rule(20, 0, 500, M, "Practice a child's play gives the skill it teaches each epoch")
    friend_chance: int = rule(30, 0, 100, M, "Chance two children of a group become friends in an epoch (%)")
    friendship: int = rule(20, 0, 100, M, "Friendship a childhood friendship begins with")
    rival_chance: int = rule(10, 0, 100, M, "Chance two children of a group become rivals in an epoch (%)")
    rivalry: int = rule(15, 0, 100, M, "Rivalry a childhood rivalry begins with")
    deprived_cheer: int = rule(3, 0, 20, M, "Cheerfulness a child deprived of play loses each epoch")
    deprived_stress: int = rule(8, 0, 100, M, "Stress a grown member carries for each epoch it was deprived of play")
    companion_weight: int = rule(15, 0, 100, P, "Weight a ruler's childhood companion gains when a seat on the council is filled")


@dataclass(frozen=True)
class SanctuaryRules(Spanned):
    seek_chance: int = rule(40, 0, 100, R, "Chance a hunted mortal seeks sanctuary in an epoch (%)")
    fee: int = rule(2, 0, 1000, R, "Coin a sheltered fugitive pays its host each epoch")
    cult_influence: int = rule(1, 0, 20, R, "Influence a cult gains each epoch a temple it holds is paid for sanctuary")
    negotiate_chance: int = rule(30, 0, 100, P, "Chance a pursuer bargains for the fugitive in an epoch (%)")
    besiege_chance: int = rule(25, 0, 100, P, "Chance a pursuer surrounds the refuge in an epoch (%)")
    violate_chance: int = rule(10, 0, 100, P, "Chance a pursuer breaks the sanctuary in an epoch (%)")
    ransom: int = rule(10, 0, 1000, P, "Coin a pursuer pays the host to settle a negotiated surrender")
    surrender_years: int = span(1, 1, 1250, P, "Years of siege after which a fugitive gives itself up")
    infamy: int = rule(15, 0, 100, P, "Infamy a pursuer earns for breaking a sanctuary")
    asylum_relation: int = rule(10, 0, 100, P, "Relation two realms lose when one gives asylum to the other's fugitive")
    law_chance: int = rule(30, 0, 100, P, "Chance each epoch that a realm whose own refuges shelter those it hunts lays down a law of sanctuary (%)")
    restrict_from: int = rule(60, 0, 100, P, "Regard for law of a ruler from which its realm bars sanctuary rather than taxing it")
    levy_pct: int = rule(30, 0, 100, P, "Share of a refuge's fees a realm takes once it taxes sanctuary (%)")

    @property
    def surrender_epochs(self) -> int:
        return self.epochs(self.surrender_years)


@dataclass(frozen=True)
class SatireRules(Spanned):
    jest_chance: int = rule(40, 0, 100, P, "Chance a court jester mocks the ruler in an epoch (%)")
    artwork_quality: int = rule(50, 0, 100, M, "Quality from which a work about a ruler its maker dislikes is read as satire")
    bite: int = rule(20, 0, 100, M, "Bite of a satire when nothing sets it")
    opinion_pct: int = rule(30, 0, 100, M, "Share of a satire's bite its realm's communities take from their approval of the ruler (%)")
    prestige: int = rule(5, 0, 100, P, "Glory a ruler loses for a satire at full bite")
    vent: int = rule(10, 0, 100, M, "Riot threshold a community's crowd gains from a tolerated satire at full bite")
    suppression: int = rule(6, 0, 100, P, "Loyalty a realm member loses for each satire the realm punishes")
    groupthink_relief: int = rule(10, 0, 100, M, "Groupthink a ruler sheds each epoch a jester speaks freely at court")
    punish_term_years: int = span(2, 0, 500, P, "Years of prison a satirist serves where satire is not tolerated")

    @property
    def punish_term(self) -> int:
        return self.epochs(self.punish_term_years)
