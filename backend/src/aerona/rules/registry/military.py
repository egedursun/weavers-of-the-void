from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span

W = RuleGroup.WAR_AND_DIPLOMACY


@dataclass(frozen=True)
class MilitaryUnitsRules:
    min_stack: int = rule(20, 1, 100000, W, "Smallest stack worth fielding")
    equipment_quality_pct: int = rule(60, 0, 200, W, "Weight of the army's equipment in a stack's quality (%)")
    experience_pct: int = rule(40, 0, 200, W, "Weight of experience in a stack's fighting (%)")
    veteran_skill_pct: int = rule(20, 0, 200, W, "Quality a stack gains from a named veteran's weapon skill at full level (%)")
    noble_share_pct: int = rule(100, 0, 500, W, "Weight of the noble class in fielding heavy cavalry (%)")
    style_share_pct: int = rule(60, 0, 100, W, "Share of an army raised in its people's way of war (%)")
    beast_share_pct: int = rule(10, 0, 100, W, "Share of an army that rides or drives beasts when its land has war beasts (%)")
    magic_share_pct: int = rule(5, 0, 100, W, "Share of an army that is war mages where magic is known (%)")
    priest_share_pct: int = rule(3, 0, 100, W, "Share of an army that is battle priests where the priests are many (%)")
    naval_share_pct: int = rule(15, 0, 100, W, "Share of a coastal seafaring people's army that serves on ships (%)")
    engineer_share_pct: int = rule(4, 0, 100, W, "Share of an army that is sappers and engines where building is known (%)")
    successor_share_pct: int = rule(60, 0, 100, W, "Share of an older missile role a realm moves to its newer successor once it can field it (%)")
    successor_settled_eras: int = rule(
        2, 0, 12, W, "Eras after a newer role first comes into reach when a realm has moved every soldier of the older role to it (eras)"
    )
    medic_share_pct: int = rule(3, 0, 100, W, "Share of an army that is medics where medicine is known (%)")
    electronic_share_pct: int = rule(5, 0, 100, W, "Share of an army that is signals troops and drone operators once it can field them (%)")
    air_share_pct: int = rule(6, 0, 100, W, "Share of an army that flies as pilots once it can field them (%)")
    special_share_pct: int = rule(3, 0, 100, W, "Share of an army that is special forces once it can field them (%)")
    peace_share_pct: int = rule(4, 0, 100, W, "Share of an army that keeps order as peacekeepers once civics allows it (%)")
    partisan_share_pct: int = rule(12, 0, 100, W, "Share of a community at war that takes up arms as partisans (%)")


@dataclass(frozen=True)
class LogisticsRules:
    supply_days: int = rule(120, 0, 10000, W, "Days of food an army carries when raised")
    season_days: int = rule(90, 1, 1000, W, "Days in a campaign season")
    forage_days: int = rule(40, 0, 1000, W, "Days of food an army forages in a season from a fed land")
    forage_scar: int = rule(25, 0, 100, W, "Share of one year's harvest of the land a foraging army eats or spoils (%)")
    supply_per_farmed: int = rule(80, 0, 100000, W, "Soldiers a point of farmed land feeds in a season")
    over_supply_attrition_pct: int = rule(4, 0, 100, W, "Soldiers lost in a season per doubling above what the land feeds (%)")
    raid_line_chance: int = rule(15, 0, 100, W, "A long supply line is raided in a season (%)")
    raid_line_length: int = rule(3, 1, 100, W, "Regions of supply line at which raids begin")
    pay_per_100: int = rule(2, 0, 100000, W, "Treasury a hundred soldiers cost in a season")
    unpaid_morale: int = rule(10, 0, 100, W, "Morale an unpaid army loses in a season")
    march_regions: int = rule(2, 0, 20, W, "Regions an ordinary army marches in a season")
    forced_march_pct: int = rule(150, 100, 300, W, "Distance of a forced march (%)")
    forced_fatigue: int = rule(25, 0, 100, W, "Fatigue a forced march adds")
    rest_fatigue: int = rule(30, 0, 100, W, "Fatigue shed in a season of rest")
    entrench_gain: int = rule(25, 0, 100, W, "Earthworks an entrenched army raises in a season")
    entrench_defence_pct: int = rule(40, 0, 300, W, "Defence of the defender at full earthworks (%)")
    passability_floor: int = rule(15, 0, 100, W, "Passability below which an army cannot cross a land in a season")


@dataclass(frozen=True)
class AttritionRules:
    disease_pct: int = rule(5, 0, 100, W, "Soldiers lost to camp sickness in a season at full camp disease (%)")
    camp_disease_gain: int = rule(10, 0, 100, W, "Camp disease gained in a season, scaled by the land's disease load")
    starvation_pct: int = rule(8, 0, 100, W, "Soldiers lost in a season without food (%)")
    desertion_pct: int = rule(5, 0, 100, W, "Soldiers who desert in a season of hunger or no pay (%)")


@dataclass(frozen=True)
class MoraleRules:
    base: int = rule(55, 0, 100, W, "Morale of a stack with nothing for or against it")
    leadership_pct: int = rule(25, 0, 200, W, "Morale from the commander's leadership at full skill (%)")
    supply_pct: int = rule(15, 0, 100, W, "Morale lost when supplies run out (%)")
    priests_gain: int = rule(6, 0, 100, W, "Morale battle priests lend their army")
    terror_pct: int = rule(100, 0, 500, W, "Weight of terror from beasts and horrors against an army's courage (%)")
    home_sacked_rage: int = rule(8, 0, 100, W, "Morale a sack of the soldiers' home city adds to the warlike")
    home_sacked_desertion_pct: int = rule(5, 0, 100, W, "Soldiers who go home when their city is sacked (%)")
    rout_morale: int = rule(25, 0, 100, W, "Morale below which a stack routs")
    rout_contagion: int = rule(10, 0, 100, W, "Morale every stack loses when a neighbouring stack routs")
    trait_chance_pct: int = rule(30, 0, 100, W, "Chance a commander earns a trait a battle showed (%)")
    warned_morale: int = rule(6, 0, 100, W, "Morale a side gains when its spies warned it of the attack")
    medicine_levels: int = rule(5, 1, 20, W, "Medicine knowledge level at which the wounded get full care")


@dataclass(frozen=True)
class TerrainEffectsRules:
    strength_pct: int = rule(100, 0, 300, W, "How strongly terrain changes each kind of unit (%)")
    defender_height_pct: int = rule(100, 0, 300, W, "How strongly hills, passes and walls favour the defender (%)")
    river_crossing_pct: int = rule(70, 0, 100, W, "Attacker strength while crossing a river (%)")
    urban_civilian_pct: int = rule(3, 0, 100, W, "Share of a city's people who die in street fighting (%)")


@dataclass(frozen=True)
class WeatherBattleEffectsRules:
    strength_pct: int = rule(100, 0, 300, W, "How strongly the weather changes each kind of unit (%)")
    fog_ambush_pct: int = rule(200, 100, 500, W, "Ambush strength in fog or at night (%)")
    heavy_fatigue_pct: int = rule(150, 100, 300, W, "Fatigue of heavily armoured troops in heat or snow (%)")


@dataclass(frozen=True)
class TacticsRules:
    counter_pct: int = rule(125, 100, 300, W, "Strength of a tactic that counters the enemy's (%)")
    countered_pct: int = rule(80, 0, 100, W, "Strength of a tactic that is countered (%)")
    terrain_pct: int = rule(115, 100, 300, W, "Strength of a tactic suited to the ground (%)")
    misplaced_pct: int = rule(85, 0, 100, W, "Strength of a tactic that needs other ground (%)")
    barrage_pct: int = rule(130, 100, 300, W, "Strength of the volleys of a side that lays an artillery barrage (%)")
    bombardment_pct: int = rule(160, 100, 400, W, "Strength of the volleys of a side that bombards from orbit (%)")
    jammed_pct: int = rule(75, 0, 100, W, "Strength of volleys aimed at a side that wages electronic warfare (%)")
    strike_surprise_pct: int = rule(130, 100, 300, W, "Surprise of a side that infiltrates or drops onto the field (%)")
    skill_weight: int = rule(3, 0, 100, W, "Weight of each level of tactics skill in choosing well")
    scouting_margin: int = rule(15, 0, 100, W, "Scouting lead that lets a side choose ambush, ground or retreat")
    melee_rounds: int = rule(3, 1, 10, W, "Most rounds of melee in a battle")
    loss_scale_pct: int = rule(8, 0, 100, W, "Share of the weaker side's strength lost in an even round (%)")
    pyrrhic_pct: int = rule(40, 0, 100, W, "Share of its strength a winner loses for a pyrrhic victory (%)")
    massacre_pct: int = rule(50, 0, 100, W, "Share of the loser lost in pursuit for a massacre (%)")
    pursuit_pct: int = rule(12, 0, 100, W, "Share of a routed army lost to a pursuer's light horse at full strength (%)")
    captive_pct: int = rule(25, 0, 100, W, "Share of pursuit losses taken captive rather than killed (%)")
    decisive_ratio_pct: int = rule(200, 100, 1000, W, "Strength ratio after battle for a decisive victory (%)")
    wounded_pct: int = rule(40, 0, 100, W, "Share of losses who are wounded rather than killed (%)")
    fortune_pct: int = rule(10, 0, 50, W, "Fortune each stack meets in a phase of battle, either way (%)")
    stalemate_ratio_pct: int = rule(115, 100, 300, W, "Strength ratio after battle below which it is a stalemate (%)")
    parley_ratio_pct: int = rule(40, 0, 100, W, "Strength a side must fall below, against its foe, before it will yield at a parley (%)")
    parley_pct: int = rule(35, 0, 100, W, "Chance a much weaker side yields at a parley before battle (%)")


@dataclass(frozen=True)
class SiegecraftRules:
    ration_use_pct: int = rule(60, 0, 100, W, "Food a rationing city eats against a full ration (%)")
    famine_days: int = rule(0, 0, 10000, W, "Days of food at which a besieged city starves")
    taboo_seasons: int = rule(2, 0, 100, W, "Seasons of famine after which the starving break their last taboos")
    bombard_breach: int = rule(25, 0, 100, W, "Damage a season of bombardment does to the walls at full engines")
    bombard_hurt: int = rule(2, 0, 20, W, "Named townsfolk struck each season the siege engines shell a town")
    bombard_hp: int = rule(30, 0, 200, W, "Health a shelling takes from each townsfolk it strikes")
    mine_chance: int = rule(30, 0, 100, W, "Sappers' mine brings down a stretch of wall in a season (%)")
    repair_pct: int = rule(15, 0, 100, W, "Wall condition repaired in a season by the defenders")
    breach_condition: int = rule(35, 0, 100, W, "Wall condition below which a breach opens")
    assault_breaches: int = rule(1, 0, 20, W, "Breaches at which the besiegers storm the walls")
    sally_ratio_pct: int = rule(60, 0, 300, W, "Garrison strength against the besiegers at which the defenders sally (%)")
    sally_losses_pct: int = rule(6, 0, 100, W, "Besiegers lost to a sally (%)")
    surrender_chance: int = rule(35, 0, 100, W, "A starving city surrenders in a season (%)")
    negotiate_chance: int = rule(20, 0, 100, W, "Terms are agreed when the besiegers offer them to a rationing city (%)")
    camp_disease_gain: int = rule(8, 0, 100, W, "Sickness that grows outside the walls in a season of siege")
    wall_defence_pct: int = rule(20, 0, 100, W, "Defence each level of walls lends the garrison (%)")
    sack_loot: int = rule(20, 0, 100, W, "Wealth a sack carries off")
    sack_prosperity: int = rule(15, 0, 100, W, "Prosperity a sack destroys")
    hunger_sickness_seasons: int = rule(2, 0, 20, W, "Seasons of famine after which hunger sickness takes a besieged town before its taboos break")
    hunger_sickness_death_pct: int = rule(3, 0, 100, W, "Share of a besieged town's people hunger sickness kills each season (%)")
    hunger_sickness_disease: int = rule(10, 0, 100, W, "Disease load hunger sickness adds to the region of a besieged town each season")
    poison_water_days: int = rule(30, 0, 365, W, "Days of water a poisoned supply takes from a besieged town each season")
    poison_after_rounds: int = rule(3, 0, 100, W, "Rounds of a siege after which besiegers who will turn to poison its water")


@dataclass(frozen=True)
class NavalRules:
    storm_sink_pct: int = rule(10, 0, 100, W, "Share of a fleet's vessels a storm strikes in a season without seamanship (%)")
    boarding_pct: int = rule(100, 0, 300, W, "Weight of the troops a fleet carries when it boards (%)")
    ram_pct: int = rule(60, 0, 300, W, "Weight of a fleet's hull strength when it rams (%)")
    fire_wind_pct: int = rule(150, 0, 500, W, "Strength of fire ships in the wind (%)")
    blockade_trade_pct: int = rule(30, 0, 100, W, "Trade kept through a blockaded sea (%)")
    sky_storm_pct: int = rule(15, 0, 100, W, "Share of an army's air vehicles a storm strikes (%)")
    sky_counter_pct: int = rule(40, 0, 100, W, "Strength of a ground army against flying beasts it cannot reach (%)")


@dataclass(frozen=True)
class DuelsRules:
    exchanges_min: int = rule(3, 1, 20, W, "Fewest exchanges in a duel")
    exchanges_max: int = rule(7, 1, 30, W, "Most exchanges in a duel")
    reach_pct: int = rule(20, 0, 200, W, "First-exchange edge of the longer weapon (%)")
    armour_pct: int = rule(100, 0, 300, W, "Weight of armour in a duel (%)")
    stamina_loss: int = rule(12, 0, 100, W, "Stamina a fighter loses per exchange")
    hit_hp: int = rule(14, 0, 1000, W, "Harm of a clean hit in a duel")
    yield_honour: int = rule(20, -100, 100, W, "Honour value below which a beaten fighter yields")
    mercy_spare: int = rule(20, -100, 100, W, "Mercy value at which a victor spares a downed foe")
    disarm_chance: int = rule(10, 0, 100, W, "A clean parry disarms the foe (%)")
    honour_grievance: int = rule(40, 0, 100, W, "Grievance at which a mortal of an honour culture calls a duel")
    honour_cap: int = rule(4, 0, 10000, W, "Base of the most honour duels in an epoch, grown by the number of standing grievances")
    honour_cap_grievance_divisor: int = rule(3, 0, 10000, W, "Standing grievances per extra honour duel in an epoch (0: the cap stays at its base)")
    pain_pct: int = rule(60, 0, 300, W, "Pain a hit leaves against its harm (%)")
    stagger: int = rule(10, 0, 100, W, "Footing a heavy hit costs")
    footing_floor: int = rule(40, 0, 100, W, "Least footing a fighter keeps")
    terrain_footing: int = rule(15, 0, 100, W, "Footing lost on slippery ground")
    weather_footing: int = rule(10, 0, 100, W, "Footing lost in rain or snow")
    injury_footing: int = rule(5, 0, 100, W, "Footing lost per standing injury")
    trial_chance: int = rule(30, 0, 100, W, "A claim in a realm that settles succession by combat goes to trial in an epoch (%)")
    god_duel_chance: int = rule(20, 0, 100, W, "Champions of rival gods meet in single combat in a holy war in an epoch (%)")
    god_duel_score: int = rule(2, 0, 20, W, "War score a god's champion wins for its side")
    initiative_die: int = rule(20, 1, 100, W, "Spread of the roll that decides who acts first in an exchange")
    reach_initiative: int = rule(10, 0, 100, W, "Initiative the longer weapon gives while the fighters stand apart")
    prone_initiative: int = rule(15, 0, 100, W, "Initiative a fighter on the ground loses")
    prone_penalty_pct: int = rule(40, 0, 100, W, "Strength a fighter on the ground loses (%)")
    called_shot_skill: int = rule(60, 0, 100, W, "Weapon skill at which a fighter aims at a chosen part")
    feint_skill: int = rule(40, 0, 100, W, "Deception skill at which a fighter feints")
    feint_chance: int = rule(25, 0, 100, W, "A fighter able to feint feints before a strike (%)")
    feint_edge_pct: int = rule(30, 0, 100, W, "Edge a feint gives against the read of the next strike")
    read_base_pct: int = rule(45, 0, 100, W, "A defence meets an even attack (%)")
    read_weight_pct: int = rule(50, 0, 100, W, "Weight of intuition and feinting against skill in reading an attack (%)")
    read_floor_pct: int = rule(5, 0, 50, W, "Least and most chance a defence meets an attack (%)")
    couched_charge_pct: int = rule(60, 0, 300, W, "Edge a couched charge from a mount gives its first strike (%)")
    rise_punish_chance: int = rule(50, 0, 100, W, "A foe strikes a fighter who rises from the ground (%)")
    rise_strike_pct: int = rule(50, 0, 300, W, "Edge a strike against a rising fighter gets (%)")
    knockdown_pct: int = rule(30, 0, 100, W, "A heavy hit throws its target to the ground (%)")
    grapple_chance: int = rule(20, 0, 100, W, "A fighter at close quarters who is no worse unarmed grapples (%)")
    grapple_die: int = rule(30, 1, 100, W, "Spread of the roll in a grapple")
    choke_chance: int = rule(35, 0, 100, W, "A grappler holding a foe on the ground chokes them senseless instead of locking a limb (%)")
    bite_honour: int = rule(-20, -100, 100, W, "Honour at or below which a badly hurt grappler bites")
    mount_target_pct: int = rule(15, 0, 100, W, "A strike at a mounted foe hits the mount (%)")
    mount_fall_pct: int = rule(60, 0, 100, W, "Share of its strength a mount loses before it throws its rider (%)")
    fall_hp: int = rule(10, 0, 1000, W, "Harm a rider takes falling from a mount")
    yield_refuse_mercy: int = rule(-40, -100, 100, W, "Mercy below which a victor refuses a foe's yield")
    ritual_death_pct: int = rule(2, 0, 100, W, "Chance a ritual duel that downs a fighter ends in a death (%)")
    ritual_pct: int = rule(30, 0, 100, W, "Chance each epoch a town that keeps a duel custom holds a ritual duel to mark a passage (%)")
    ring_footing: int = rule(50, 0, 100, W, "Footing at or below which a fighter is driven beyond the marked bounds of a duel")
    ritual_renown: int = rule(5, 0, 100, W, "Renown each fighter of a ritual duel gains for the passage it marks")
    ritual_shame: int = rule(30, 0, 100, W, "Grievance the people bear a fighter who kills in a ritual duel against its rules")


@dataclass(frozen=True)
class CaptivityRules:
    ransom_pct: int = rule(30, 0, 100, W, "Captive cohorts ransomed home in an epoch where the origin is rich (%)")
    sacrifice_chance: int = rule(15, 0, 100, W, "Captives sacrificed by a death-loving faith (%)")
    sacrifice_death: int = rule(40, -100, 100, W, "Death value at which a captor sacrifices its captives")
    sacrifice_essence_per_100: int = rule(1, 0, 100, W, "Essence a patron god draws from each hundred captives sacrificed")
    labour_pct: int = rule(30, 0, 100, W, "Captives put to labour in the fields (%)")
    release_mercy: int = rule(30, -100, 100, W, "Mercy at which captives are released")
    exchange_pct: int = rule(50, 0, 100, W, "Captives exchanged at peace (%)")
    ward_chance: int = rule(25, 0, 100, W, "A captive heir is raised as a ward of the captor's court (%)")
    ward_drift: int = rule(10, 0, 100, W, "Values a ward takes from the captor each epoch")
    torture_chance: int = rule(15, 0, 100, W, "A named captive is tortured for intelligence by a cruel captor (%)")
    torture_hp: int = rule(20, 0, 1000, W, "Harm torture deals")
    torture_intel: int = rule(20, 0, 100, W, "Intelligence a torture yields about the captive's people")
    execution_memory: int = rule(40, 0, 100, W, "Grief an execution leaves in the captive's kin")


@dataclass(frozen=True)
class WarAimsRules:
    aims_per_side: int = rule(2, 1, 10, W, "War aims each side pursues")
    occupation_score: int = rule(30, 0, 100, W, "Score a season of occupation of an aim's land earns")
    siege_score: int = rule(40, 0, 100, W, "Score a breached or surrendered city earns toward its aim")
    battle_score: int = rule(10, 0, 100, W, "Score a won battle earns toward every aim")


@dataclass(frozen=True)
class OccupationRules:
    control_gain: int = rule(20, 0, 100, W, "Control an occupier gains in a season")
    resistance_base: int = rule(30, 0, 100, W, "Resistance of an occupied land")
    distance_pct: int = rule(50, 0, 200, W, "Weight of value distance in resistance (%)")
    atrocity_pct: int = rule(100, 0, 300, W, "Weight of remembered atrocities in resistance (%)")
    partisan_chance: int = rule(20, 0, 100, W, "A resisting land raids its occupier in an epoch at full resistance (%)")
    partisan_losses_pct: int = rule(5, 0, 100, W, "Soldiers an occupying army loses to partisans (%)")
    tax_pct: int = rule(50, 0, 100, W, "Share of an occupied land's taxes taken by the occupier at full control (%)")
    revolt_resistance: int = rule(70, 0, 100, W, "Resistance at which an occupied land may rise in revolt")
    revolt_chance: int = rule(15, 0, 100, W, "An occupied land at revolt resistance rises in an epoch (%)")
    collaborator_cost_cut_pct: int = rule(20, 0, 100, W, "Share of the cost of rule each collaborator saves the occupier (%)")
    measure_partisan_cut_pct: int = rule(30, 0, 100, W, "Share of partisan raids a measure at full strength prevents in its epoch (%)")
    measure_grievance: int = rule(20, 0, 100, W, "Resistance a harsh measure at full strength adds")
    exposure_kill_pct: int = rule(15, 0, 100, W, "Chance in an epoch that a fully exposed collaborator is killed by partisans (%)")
    extraction_cap_pct: int = rule(50, 0, 100, W, "Highest share of an occupied land's taxes, levies or labour an occupier may take (%)")
    rule_upkeep: int = rule(20, 0, 1000, W, "Treasury an occupier spends in an epoch on ruling one occupied land under military rule")
    collaborator_intel_pct: int = rule(10, 0, 100, W, "Share of partisan raids each informing or policing collaborator prevents (%)")
    exposure_gain: int = rule(10, 0, 100, W, "Exposure a collaborator gains in an epoch at full resistance")
    measure_decay: int = rule(25, 0, 100, W, "Strength a measure loses in an epoch")
    settle_per_epoch: int = rule(
        200, 0, 100000, W, "Settlers of the occupier's people who move into an annexed or civilly ruled land in an epoch at full control"
    )
    annex_control: int = rule(80, 0, 100, W, "Control at which a land under annexation rule is annexed")
    deport_pct: int = rule(5, 0, 100, W, "Share of an occupied town a deportation at full strength carries off (%)")
    requisition_pct: int = rule(20, 0, 100, W, "Share of an occupied town's treasury a requisition at full strength takes (%)")
    recruit_chance_pct: int = rule(30, 0, 100, W, "Chance in an epoch that an occupier at full control wins a local collaborator (%)")
    measure_chance_pct: int = rule(30, 0, 100, W, "Chance in an epoch that an occupier facing full resistance imposes a measure (%)")
    labour_prosperity: int = rule(10, 0, 100, W, "Prosperity an occupied town loses in an epoch to forced labour at full rate")
    rule_shift_chance_pct: int = rule(20, 0, 100, W, "Chance in an epoch that an occupier with enough control moves from military to civil rule (%)")


@dataclass(frozen=True)
class WarWearinessRules:
    casualty_per_1000: int = rule(4, 0, 100, W, "Weariness per thousand dead")
    maimed_per_100: int = rule(2, 0, 100, W, "Weariness per hundred maimed veterans coming home")
    occupation_gain: int = rule(10, 0, 100, W, "Weariness per home land under occupation")
    season_gain: int = rule(3, 0, 100, W, "Weariness per season at war")
    martial_resist_pct: int = rule(50, 0, 100, W, "Share of weariness a martial people shrugs off at full martial value (%)")
    peace_threshold: int = rule(70, 0, 100, W, "Weariness above which a side seeks peace")
    honour_hold_pct: int = rule(50, 0, 100, W, "Share of peace pressure an honour culture resists while humiliated (%)")
    recovery_pct: int = rule(15, 0, 100, W, "Share of its war weariness a realm at peace sheds each epoch (%)")
    maimed_slow_pct: int = rule(50, 0, 100, W, "Share of that recovery a realm loses while its maimed veterans are many, at their most (%)")
    maimed_full: int = rule(1000, 1, 100000, W, "Maimed veterans of a realm at which its recovery is slowed the most")
    memory_slow_pct: int = rule(30, 0, 100, W, "Share of that recovery a realm loses while it keeps accounts of its wars (%)")


@dataclass(frozen=True)
class PeaceRules(Spanned):
    cession_score: int = rule(50, 0, 100, W, "Score at which a winner takes the land it occupies")
    vassal_score: int = rule(80, 0, 100, W, "Score at which a winner makes the loser its vassal")
    tribute_score: int = rule(30, 0, 100, W, "Score at which a winner demands tribute")
    hostage_score: int = rule(40, 0, 100, W, "Score at which a winner takes a hostage")
    reparations: int = rule(20, 0, 100, W, "Share of its coin and treasury a loser pays in reparations, unless the war aim names an amount (%)")
    treaty_years: int = span(20, 1, 2500, W, "Years a peace treaty binds")

    @property
    def treaty_epochs(self) -> int:
        return self.epochs(self.treaty_years)

    apology_prestige: int = rule(5, 0, 50, W, "Prestige a side gives up, and its foe gains, when a peace makes it own its wrong")


@dataclass(frozen=True)
class VendettaRules(Spanned):
    grievance: int = rule(35, 0, 100, W, "Grief for slain kin at which a house or people acts on a feud")
    raid_chance: int = rule(30, 0, 100, W, "An aggrieved side raids in an epoch (%)")
    assassinate_chance: int = rule(10, 0, 100, W, "An aggrieved side sends an assassin (%)")
    wergild_chance: int = rule(25, 0, 100, W, "An aggrieved side demands wergild where custom allows (%)")
    escalate_chance: int = rule(8, 0, 100, W, "A feud escalates to war (%)")
    mediation_chance: int = rule(20, 0, 100, W, "A peace-minded priest mediates a feud (%)")
    raid_hp: int = rule(25, 0, 1000, W, "Harm a feud raid deals")
    cap: int = rule(
        6, 0, 10000, W, "Base of the most feud actions in an epoch, grown by the number of live feuds; also the most people of a side a feud action reaches"
    )
    cap_feud_divisor: int = rule(1, 0, 10000, W, "Live feuds per extra feud action in an epoch (0: the cap stays at its base)")
    honour_pct: int = rule(100, 0, 300, W, "Weight of an honour culture in a feud's intensity (%)")
    marriage_brake_pct: int = rule(40, 0, 100, W, "Intensity a marriage between the feuding sides takes away (%)")
    common_enemy_brake_pct: int = rule(30, 0, 100, W, "Intensity a shared enemy takes away (%)")
    fade_per_epoch: int = rule(3, 0, 100, W, "Grievance and intensity a feud loses in an epoch")
    generation_years: int = span(25, 1, 2500, W, "Years that count as a generation of a feud")
    generation_fade: int = rule(10, 0, 100, W, "Intensity a feud loses with each new generation")
    ambush_chance: int = rule(10, 0, 100, W, "An aggrieved side lies in wait for its foe's people on the road (%)")
    abduct_chance: int = rule(5, 0, 100, W, "An aggrieved side carries off one of its foe's people (%)")
    property_chance: int = rule(10, 0, 100, W, "An aggrieved side destroys its foe's goods and works (%)")
    seek_mediation_chance: int = rule(10, 0, 100, W, "A weary side asks a ruler or a priest to mediate (%)")
    allies_chance: int = rule(8, 0, 100, W, "An aggrieved side calls on its allies and kin to join the feud (%)")
    ambush_hp: int = rule(15, 0, 1000, W, "Harm an ambush deals to each of the foe's people it catches")
    property_loss: int = rule(5, 0, 100, W, "Prosperity a foe loses when its goods and works are destroyed")
    insult_below: int = rule(30, 0, 100, W, "Intensity below which a feud stands at insults alone")
    fade_floor: int = rule(10, 0, 100, W, "Intensity at which a feud fades away")
    peace_tenet_mediation: int = rule(30, 0, 100, W, "A faith of peace mediates a burning feud (%)")

    @property
    def generation_epochs(self) -> int:
        return self.epochs(self.generation_years)

    amends_chance: int = rule(10, 0, 100, W, "An aggrieved side seeks amends in goods or rites to end the feud (%)")
    amends_wealth: int = rule(5, 0, 100, W, "Wealth the side that did the wrong gives as amends to end a feud")
    swear_off_chance: int = rule(5, 0, 100, W, "An honour-minded side swears an oath with its foe to end the feud; breaking it is oathbreaking (%)")
    dormant_years: int = span(500, 50, 5000, W, "Years without an act after which a feud lies dormant")
    wake_pct: int = rule(10, 0, 100, W, "Chance a dormant feud wakes in an epoch by a new offence, an insult or a remembered date (%)")
