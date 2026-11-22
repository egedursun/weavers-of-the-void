from collections.abc import Mapping

from aerona.core.total import total
from aerona.domain.enums.military import (
    BattlePhase,
    CaptiveFate,
    CommanderTrait,
    ContractStatus,
    DefenderAction,
    FeudAction,
    FeudLevel,
    SiegeAction,
    SiegeWork,
    Stance,
    Tactic,
    WarAimKind,
)
from aerona.domain.enums.mind import MemoryKind, SkillKind
from aerona.domain.enums.polity import OfficeKind, TreatyKind
from aerona.domain.enums.records import StepAction, StepState
from aerona.domain.enums.war import WarCause, WarEnding

CAUSE_AIMS: dict[WarCause, tuple[WarAimKind, ...]] = {
    WarCause.HOSTILITY: (WarAimKind.CONQUER_REGION, WarAimKind.TRIBUTE),
    WarCause.UPRISING: (WarAimKind.LIBERATE, WarAimKind.REVENGE),
    WarCause.TRIBUTE_REVOLT: (WarAimKind.LIBERATE, WarAimKind.HUMILIATE),
    WarCause.INCITED: (WarAimKind.LOOT, WarAimKind.HUMILIATE),
    WarCause.DECLARED: (WarAimKind.CONQUER_REGION, WarAimKind.VASSALISE),
    WarCause.BETRAYAL: (WarAimKind.REVENGE, WarAimKind.HUMILIATE),
    WarCause.CONQUEST_JOURNEY: (WarAimKind.CONQUER_REGION, WarAimKind.SEIZE_SETTLEMENT),
    WarCause.FOREIGN_GOD: (WarAimKind.CONVERT, WarAimKind.DESTROY_CULT),
    WarCause.INDEPENDENCE: (WarAimKind.LIBERATE, WarAimKind.TRIBUTE),
    WarCause.VENDETTA: (WarAimKind.REVENGE, WarAimKind.LOOT),
    WarCause.GRUDGE: (WarAimKind.HUMILIATE, WarAimKind.REVENGE),
    WarCause.DIVINE_GRUDGE: (WarAimKind.CONVERT, WarAimKind.HUMILIATE),
    WarCause.RIVALRY: (WarAimKind.HUMILIATE, WarAimKind.VASSALISE),
    WarCause.DEBT: (WarAimKind.TRIBUTE, WarAimKind.LOOT),
    WarCause.ESPIONAGE: (WarAimKind.HUMILIATE, WarAimKind.TRIBUTE),
    WarCause.SABOTAGE: (WarAimKind.REVENGE, WarAimKind.TRIBUTE),
    WarCause.ENVY: (WarAimKind.LOOT, WarAimKind.SEIZE_RESOURCE),
    WarCause.SCHISM: (WarAimKind.CONVERT, WarAimKind.DESTROY_CULT),
    WarCause.BEAST: (WarAimKind.LOOT, WarAimKind.REVENGE),
    WarCause.RESOURCE: (WarAimKind.SEIZE_RESOURCE, WarAimKind.CONQUER_REGION),
    WarCause.IDEOLOGY: (WarAimKind.CHANGE_GOVERNMENT, WarAimKind.LIBERATE),
    WarCause.TRADE_ROUTE: (WarAimKind.SEIZE_ROUTE, WarAimKind.TRIBUTE),
    WarCause.CLAIM: (WarAimKind.PRESS_CLAIM, WarAimKind.CONQUER_REGION),
    WarCause.HOLY_WAR: (WarAimKind.CONVERT, WarAimKind.DESTROY_CULT),
    WarCause.SUCCESSION: (WarAimKind.PRESS_CLAIM, WarAimKind.HUMILIATE),
    WarCause.RAID: (WarAimKind.LOOT,),
    WarCause.LIBERATION: (WarAimKind.LIBERATE, WarAimKind.REVENGE),
    WarCause.PUNITIVE: (WarAimKind.REVENGE, WarAimKind.TRIBUTE),
}


GENERIC = (Tactic.HOLD_LINE, Tactic.FRONTAL_ASSAULT)


TRAIT_TACTICS: dict[CommanderTrait, tuple[Tactic, ...]] = {
    CommanderTrait.RECKLESS: (Tactic.FRONTAL_ASSAULT, Tactic.WEDGE),
    CommanderTrait.AGGRESSIVE_ASSAULTER: (Tactic.FRONTAL_ASSAULT, Tactic.WEDGE),
    CommanderTrait.CAUTIOUS: (Tactic.HOLD_LINE, Tactic.SHIELD_WALL),
    CommanderTrait.DEFENSIVE_GENIUS: (Tactic.HOLD_LINE, Tactic.RIVER_DEFENCE, Tactic.SHIELD_WALL),
    CommanderTrait.CAVALRY_MASTER: (Tactic.FLANK_CAVALRY, Tactic.FEIGNED_RETREAT),
    CommanderTrait.SIEGE_EXPERT: (Tactic.SIEGE_ASSAULT,),
    CommanderTrait.SKY_COMMANDER: (Tactic.AIR_SUPERIORITY,),
    CommanderTrait.SPACE_COMMANDER: (Tactic.ORBITAL_BOMBARDMENT, Tactic.DROP_ASSAULT),
    CommanderTrait.ARTILLERIST: (Tactic.ARTILLERY_BARRAGE, Tactic.MISSILE_ATTRITION),
    CommanderTrait.AMBUSHER: (Tactic.AMBUSH, Tactic.NIGHT_RAID, Tactic.GUERRILLA),
    CommanderTrait.FOREST_FIGHTER: (Tactic.AMBUSH, Tactic.SKIRMISH_HARASS),
    CommanderTrait.SKIRMISHER: (Tactic.SKIRMISH_HARASS, Tactic.FEINT),
    CommanderTrait.ARMOURED_COMMANDER: (Tactic.ARMOURED_THRUST,),
    CommanderTrait.DISCIPLINARIAN: (Tactic.HOLD_LINE, Tactic.SHIELD_WALL),
    CommanderTrait.SIGNALS_COMMANDER: (Tactic.ELECTRONIC_WARFARE,),
    CommanderTrait.SIEGE_DEFENDER: (Tactic.HOLD_LINE,),
    CommanderTrait.NIGHT_FIGHTER: (Tactic.NIGHT_RAID,),
}


PHASE_STATES: Mapping[BattlePhase, tuple[str, StepState]] = {
    BattlePhase.SCOUTING: ("hidden", StepState.HIDDEN),
    BattlePhase.MELEE: ("revealed", StepState.REVEALED),
}


PHASE_ACTIONS = {
    BattlePhase.SCOUTING: StepAction.DEPLOY,
    BattlePhase.PLAN: StepAction.DEPLOY,
    BattlePhase.COMMAND: StepAction.DEPLOY,
    BattlePhase.MISSILE: StepAction.VOLLEY,
    BattlePhase.CHARGE: StepAction.CHARGE,
    BattlePhase.MELEE: StepAction.ADVANCE,
    BattlePhase.RESERVES: StepAction.REINFORCE,
    BattlePhase.RITES: StepAction.PERFORM_RITE,
    BattlePhase.PURSUIT: StepAction.PURSUE,
    BattlePhase.SALVAGE: StepAction.PILLAGE,
    BattlePhase.AFTERMATH: StepAction.HOLD,
}


LEVELS: Mapping[FeudAction, FeudLevel | None] = total(
    FeudAction,
    {
        FeudAction.RAID: FeudLevel.RAID,
        FeudAction.ASSASSINATE: FeudLevel.BLOOD,
        FeudAction.DEMAND_WERGILD: None,
        FeudAction.ESCALATE: FeudLevel.WAR,
        FeudAction.REST: None,
        FeudAction.AMBUSH: FeudLevel.RAID,
        FeudAction.ABDUCT: FeudLevel.BLOOD,
        FeudAction.DESTROY_PROPERTY: FeudLevel.RAID,
        FeudAction.SEEK_MEDIATION: None,
        FeudAction.CALL_ALLIES: None,
    },
)


HEALING = (SkillKind.MEDICINE, SkillKind.SURGERY)


ATROCITIES = (MemoryKind.KILLED_KIN, MemoryKind.FOUGHT_US)


TREATY_ENDINGS = {
    WarEnding.VICTORY: TreatyKind.PEACE,
    WarEnding.CONQUEST: TreatyKind.PEACE,
    WarEnding.TRIBUTE: TreatyKind.TRIBUTE,
    WarEnding.EXHAUSTION: TreatyKind.PEACE,
    WarEnding.PEACE: TreatyKind.PEACE,
    WarEnding.WHITE_PEACE: TreatyKind.PEACE,
    WarEnding.MIRACLE: TreatyKind.PEACE,
}


NO_TREATY = {
    WarEnding.BETRAYAL: "the war ended in betrayal; no one sat down to sign",
    WarEnding.SAME_FRONT: "the war was folded into another front of the same war",
    WarEnding.NO_SIDE_LEFT: "no side was left standing to sign a peace",
}


SIEGE_ACTIONS = {
    SiegeAction.BLOCKADE: StepAction.HOLD,
    SiegeAction.BOMBARD: StepAction.BOMBARD,
    SiegeAction.MINE: StepAction.UNDERMINE,
    SiegeAction.ASSAULT: StepAction.STORM,
    SiegeAction.NEGOTIATE: StepAction.NEGOTIATE,
}


DEFENCE_ACTIONS = {
    DefenderAction.SALLY: StepAction.SORTIE,
    DefenderAction.REPAIR: StepAction.REPAIR,
    DefenderAction.RATION: StepAction.HOLD,
    DefenderAction.SEEK_RELIEF: StepAction.REINFORCE,
}


ACTION_WORKS = {
    SiegeAction.BLOCKADE: (SiegeWork.CIRCUMVALLATION,),
    SiegeAction.BOMBARD: (SiegeWork.TOWERS, SiegeWork.RAMS),
    SiegeAction.MINE: (SiegeWork.MINES,),
    SiegeAction.ASSAULT: (SiegeWork.LADDERS, SiegeWork.RAMS),
    SiegeAction.NEGOTIATE: (),
}

WANTED_TRAITS_TACTICS = frozenset({Tactic.FRONTAL_ASSAULT, Tactic.WEDGE})
SETTLE_COHORT_CAPTIVE_FATES = frozenset({CaptiveFate.RELEASED, CaptiveFate.RANSOMED, CaptiveFate.EXCHANGED})
SETTLE_COHORT_CAPTIVE_FATES_2 = frozenset({CaptiveFate.ENSLAVED, CaptiveFate.LABOUR})
PAY_CONTRACTS_CONTRACT_STATUSS = (ContractStatus.ACTIVE, ContractStatus.UNPAID)
ENTRENCH_STANCES = frozenset({Stance.ENTRENCH, Stance.GARRISON, Stance.BESIEGE})
FEED_STANCES = frozenset({Stance.FORAGE, Stance.MARCH, Stance.BESIEGE, Stance.RAID})
FEED_STANCES_2 = frozenset({Stance.FORAGE, Stance.RAID})
EXTRA_TERMS_WAR_ENDINGS = frozenset({WarEnding.WHITE_PEACE, WarEnding.EXHAUSTION, WarEnding.PEACE, WarEnding.MIRACLE})
BATTER_SIEGE_ACTIONS = frozenset({SiegeAction.BOMBARD, SiegeAction.MINE})
BLACKMAIL_OFFICE_OFFICE_KINDS = frozenset({OfficeKind.CHANCELLOR, OfficeKind.AMBASSADOR})
HIRE_MERCENARIES_CONTRACT_STATUSS = (ContractStatus.ACTIVE, ContractStatus.UNPAID)
