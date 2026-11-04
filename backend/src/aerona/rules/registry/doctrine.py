from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

R = RuleGroup.RELIGION_AND_LANGUAGE
D = RuleGroup.DEATH_AND_RESURRECTION


@dataclass(frozen=True)
class DoctrineRules:
    tenets_min: int = rule(3, 1, 10, R, "Fewest tenets a cult holds")
    tenets_max: int = rule(6, 1, 12, R, "Most tenets a cult holds")
    value_tenet: int = rule(35, 0, 100, R, "Doctrine value at which a tenet follows from it")
    reveal_fit: int = rule(40, 0, 100, R, "Fit with the doctrine at which a revealed tenet is accepted")
    holy_war_morale: int = rule(10, 0, 100, R, "Morale an army of the holy war gains against unbelievers")
    holy_peace_zeal: int = rule(8, 0, 100, R, "Zeal lost when a holy war cult makes peace with unbelievers")
    pacifist_warrior_pct: int = rule(50, 0, 100, R, "Share of the warrior class a pacifist faith keeps (%)")
    pacifist_drift_pct: int = rule(10, 0, 100, R, "Share of a pacifist people's surplus warriors who take up farming each epoch (%)")
    pacifist_legitimacy: int = rule(6, 0, 100, R, "Legitimacy a devout pacifist ruler loses for each war he wages")
    sacrifice_essence: int = rule(2, 0, 100, R, "Essence a death or blood god gains for each sacrificing cult in an epoch")
    sacrifice_infamy: int = rule(5, 0, 100, R, "Ill will other cultures hold for human sacrifice")
    animal_sacrifice_livestock: int = rule(3, 0, 1000, R, "Livestock an animal-sacrificing cult offers in an epoch")
    monastic_protection_pct: int = rule(50, 0, 100, R, "Share of knowledge loss in dark ages that monasteries prevent (%)")
    dietary_demand_pct: int = rule(0, 0, 100, R, "Demand left for a commodity forbidden by dietary law (%)")
    sacred_species_grievance: int = rule(20, 0, 100, R, "Grievance a faith holds against those who hunt its sacred species")
    proselytism_pct: int = rule(150, 100, 500, R, "Conversion strength of a proselytising cult (%)")
    exclusive_syncretism_pct: int = rule(0, 0, 100, R, "Syncretic conversions left for an exclusive faith (%)")
    open_syncretism_pct: int = rule(200, 100, 500, R, "Syncretic conversions of an open faith (%)")


@dataclass(frozen=True)
class ZealRules:
    decay: int = rule(3, 0, 100, R, "Zeal lost each epoch with nothing to stir it")
    persecution: int = rule(10, 0, 100, R, "Zeal persecution stirs")
    martyrdom: int = rule(8, 0, 100, R, "Zeal each martyr stirs, more where martyrdom is glory")
    miracle: int = rule(6, 0, 100, R, "Zeal a miracle of the god stirs")
    holy_victory: int = rule(5, 0, 100, R, "Zeal a holy war victory stirs")
    preaching_pct: int = rule(10, 0, 100, R, "Zeal the clergy's quality stirs at full quality (%)")
    crisis: int = rule(6, 0, 100, R, "Zeal plague, famine or doom omens stir")
    prosperity_pct: int = rule(10, 0, 100, R, "Zeal comfort erodes at full prosperity (%)")
    scandal: int = rule(10, 0, 100, R, "Zeal a clergy scandal costs")
    scandal_chance: int = rule(4, 0, 100, R, "A clergy vice comes to light in an epoch (%)")
    failed_prophecy: int = rule(10, 0, 100, R, "Zeal a mocked prophecy costs")
    pilgrimage_per_1000: int = rule(1, 0, 100, R, "Zeal each thousand pilgrims bring home")
    fanaticism: int = rule(80, 0, 100, R, "Zeal above which a cult turns fanatic")
    fanaticism_chance: int = rule(25, 0, 100, R, "A fanatic cult launches an inquisition, iconoclasm or crusade (%)")


@dataclass(frozen=True)
class TithesRules:
    rate: int = rule(10, 0, 100, R, "Share of followers' output a cult tithes (%)")
    output_per_100: int = rule(2, 0, 1000, R, "Output of a hundred followers in an epoch")
    temple_cost: int = rule(60, 0, 100000, R, "Treasury a new temple costs")
    alms_cost: int = rule(20, 0, 100000, R, "Treasury alms cost in an epoch")
    alms_poverty: int = rule(10, 0, 100, R, "Poverty pressure alms relieve")
    monastery_cost: int = rule(80, 0, 100000, R, "Treasury a monastery costs")
    war_chest_pct: int = rule(25, 0, 100, R, "Share of the treasury a zealous cult gives to a holy war (%)")


@dataclass(frozen=True)
class MissionsRules:
    base_pct: int = rule(3, 0, 100, R, "Conversion a mission along a trade route brings (%)")
    skill_pct: int = rule(100, 0, 300, R, "Weight of the missionary's skill (%)")
    miracle_pct: int = rule(50, 0, 300, R, "Weight of the god's recent miracles (%)")
    rival_clergy_pct: int = rule(50, 0, 300, R, "Weight of the rival clergy's quality against a mission (%)")
    language_pct: int = rule(50, 0, 100, R, "Mission strength left across a language barrier (%)")
    cap: int = rule(3, 0, 100, R, "Most missions in an epoch")


@dataclass(frozen=True)
class InquisitionRules:
    orthodoxy_suppress: int = rule(60, 0, 100, R, "Orthodoxy at which a cult suppresses its heresies")
    drift_heresy: int = rule(30, 0, 100, R, "Doctrinal distance at which a drifting sect becomes a heresy")
    drift_rate: int = rule(4, 0, 100, R, "Doctrine drift each epoch under a creative theologian")
    punish_hp: int = rule(20, 0, 1000, R, "Harm an inquisition deals")
    execution_chance: int = rule(15, 0, 100, R, "A heretic caught by the inquisition is executed (%)")
    iconoclasm_prosperity: int = rule(5, 0, 100, R, "Prosperity iconoclasts destroy")
    investiture_chance: int = rule(10, 0, 100, R, "A strong clergy and a ruler quarrel over appointments (%)")


@dataclass(frozen=True)
class AfterlifeRules:
    paradise_score: int = rule(60, 0, 100, D, "Judgement score that opens paradise")
    torment_score: int = rule(25, 0, 100, D, "Judgement score below which a soul is tormented")
    warrior_violence: int = rule(40, 0, 100, D, "Violence in the ledger that opens a warrior hall")
    no_rite_chance: int = rule(15, 0, 100, D, "A mortal dies without the rites (%)")
    battle_no_rite_chance: int = rule(50, 0, 100, D, "A mortal fallen in war lies unburied (%)")
    restless_unrest: int = rule(60, 0, 100, D, "Unrest of a soul denied its rites")
    reincarnation_min_score: int = rule(75, 0, 100, D, "Ledger score a soul needs to be reborn")
    reincarnation_chance_pct: int = rule(10, 0, 100, D, "A qualifying soul is reborn (%)")
    reincarnation_memory_pct: int = rule(15, 0, 100, D, "Memories a reborn soul carries over (%)")
    reincarnation_traits_pct: int = rule(30, 0, 100, D, "Traits a reborn soul carries over (%)")
    torment_honour: int = rule(3, 0, 100, D, "Honour and tradition a culture gains each epoch from fearing torment")
    favour_relation: int = rule(30, 0, 100, D, "Relation to the god at which a soul is favoured")


@dataclass(frozen=True)
class SpiritsRules:
    memory_decay: int = rule(5, 0, 100, D, "Memory a spirit loses each epoch unremembered")
    remembrance: int = rule(10, 0, 100, D, "Memory and veneration offerings restore")
    offering_chance: int = rule(40, 0, 100, D, "A venerating people makes offerings to its ancestors (%)")
    neglect_unrest: int = rule(10, 0, 100, D, "Unrest a neglected guardian spirit gains")
    guardian_veneration: int = rule(30, 0, 100, D, "Veneration at which an ancestor guards its people")
    guardian_morale: int = rule(5, 0, 100, D, "Morale ancestors lend an army fighting at home")
    vengeful_unrest: int = rule(60, 0, 100, D, "Unrest at which a spirit turns vengeful")
    ancestor_death_value: int = rule(30, -100, 100, D, "Death value of a people that keeps its ancestors")


@dataclass(frozen=True)
class NecromancyRules:
    possession_chance: int = rule(5, 0, 100, D, "A vengeful bound spirit possesses a living mortal (%)")
    possession_stress: int = rule(10, 0, 100, D, "Stress a possession lays on its host each epoch")
    exorcism_chance: int = rule(30, 0, 100, D, "Priests drive out a possessing spirit (%)")
    consumption_essence: int = rule(1, 0, 100, D, "Essence a death god gains for each soul eaten")
    soul_eater_chance: int = rule(10, 0, 100, D, "A soul-eater devours a wandering soul (%)")
