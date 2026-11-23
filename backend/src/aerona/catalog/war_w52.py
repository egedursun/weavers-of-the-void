from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.entity import MortalRole
from aerona.domain.enums.honours import UnitHonourKind, VeteranGrant
from aerona.domain.enums.law_depth import RecruitMotive
from aerona.domain.enums.military import (
    AgentStatus,
    ArmyRole,
    CaptiveFate,
    CasualtyFate,
    DefenderAction,
    SackChoice,
    SiegeAction,
    SiegeWork,
    SpyOperation,
    Stance,
)
from aerona.domain.enums.war import SiegeStatus


@dataclass(frozen=True)
class StanceSpec:
    label: str
    resting: bool
    feeds: bool
    plunders: bool
    entrenches: bool
    winters: bool = False
    chases: bool = False


STANCES: Mapping[Stance, StanceSpec] = total(
    Stance,
    {
        Stance.MARCH: StanceSpec("March", resting=False, feeds=True, plunders=False, entrenches=False, winters=True, chases=True),
        Stance.FORAGE: StanceSpec("Forage", resting=False, feeds=True, plunders=True, entrenches=False, winters=True),
        Stance.ENTRENCH: StanceSpec("Entrench", resting=True, feeds=False, plunders=False, entrenches=True, winters=True),
        Stance.BESIEGE: StanceSpec("Besiege", resting=True, feeds=True, plunders=False, entrenches=True),
        Stance.GARRISON: StanceSpec("Garrison", resting=True, feeds=False, plunders=False, entrenches=True, winters=True),
        Stance.RAID: StanceSpec("Raid", resting=False, feeds=True, plunders=True, entrenches=False, winters=True, chases=True),
        Stance.RETREAT: StanceSpec("Retreat", resting=False, feeds=False, plunders=False, entrenches=False),
        Stance.WINTER_QUARTERS: StanceSpec("Winter quarters", resting=True, feeds=True, plunders=False, entrenches=True),
        Stance.PURSUE: StanceSpec("Pursue", resting=False, feeds=False, plunders=False, entrenches=False),
        Stance.ESCORT: StanceSpec("Escort", resting=False, feeds=True, plunders=False, entrenches=False, winters=True),
    },
)

WINTERING = frozenset(stance for stance, spec in STANCES.items() if spec.winters)
CHASING = frozenset(stance for stance, spec in STANCES.items() if spec.chases)


@dataclass(frozen=True)
class RoleSpec:
    label: str
    effect_rule: str | None
    staffed_from: MortalRole | None = None


ARMY_ROLES: Mapping[ArmyRole, RoleSpec] = total(
    ArmyRole,
    {
        ArmyRole.COMMANDER: RoleSpec("Commander", None),
        ArmyRole.SUB_COMMANDER: RoleSpec("Sub-commander", None),
        ArmyRole.QUARTERMASTER: RoleSpec("Quartermaster", None),
        ArmyRole.STANDARD_BEARER: RoleSpec("Standard bearer", None),
        ArmyRole.SURGEON: RoleSpec("Surgeon", None),
        ArmyRole.CHAPLAIN: RoleSpec("Chaplain", "chaplain_effect", MortalRole.PRIEST),
        ArmyRole.PAYMASTER: RoleSpec("Paymaster", "paymaster_effect", MortalRole.MERCHANT),
        ArmyRole.SCOUT_MASTER: RoleSpec("Master of scouts", "scout_master_effect", MortalRole.HUNTER),
    },
)
STAFF_ROLES = frozenset(role for role in ArmyRole if role is not ArmyRole.COMMANDER)
STAFFED_ROLES = {role: spec.staffed_from for role, spec in ARMY_ROLES.items() if spec.staffed_from is not None}


@dataclass(frozen=True)
class HonourSpec:
    label: str
    esprit_rule: str
    sign: int


UNIT_HONOURS: Mapping[UnitHonourKind, HonourSpec] = total(
    UnitHonourKind,
    {
        UnitHonourKind.VICTORY: HonourSpec("Victory", "honour_esprit", 1),
        UnitHonourKind.STAND: HonourSpec("A stand held", "honour_esprit", 1),
        UnitHonourKind.SIEGE: HonourSpec("A siege won", "honour_esprit", 1),
        UnitHonourKind.SURVIVAL: HonourSpec("Survival", "survival_esprit", 1),
        UnitHonourKind.MASSACRE: HonourSpec("Massacre", "massacre_esprit", -1),
        UnitHonourKind.RELIEF: HonourSpec("Relief of a siege", "relief_esprit", 1),
        UnitHonourKind.CROSSING: HonourSpec("A crossing under arms", "crossing_esprit", 1),
    },
)


@dataclass(frozen=True)
class GrantSpec:
    label: str
    loyalty_rule: str
    cost_rule: str


VETERAN_GRANTS: Mapping[VeteranGrant, GrantSpec] = total(
    VeteranGrant,
    {
        VeteranGrant.LAND: GrantSpec("Land", "land_loyalty", "land_cost"),
        VeteranGrant.PENSION: GrantSpec("Pension", "pension_loyalty", "pension_grant_cost"),
        VeteranGrant.NONE: GrantSpec("Nothing", "none_loyalty", "none_cost"),
        VeteranGrant.MEMBERSHIP: GrantSpec("Membership", "membership_loyalty", "membership_cost"),
        VeteranGrant.TITLE: GrantSpec("A lesser title", "title_loyalty", "title_cost"),
        VeteranGrant.TAX_EXEMPTION: GrantSpec("Freedom from taxes", "tax_exemption_loyalty", "tax_exemption_cost"),
    },
)

VETERAN_ROLES = frozenset({MortalRole.WARRIOR, MortalRole.SWORN_WARRIOR, MortalRole.OFFICER})


@dataclass(frozen=True)
class CasualtySpec:
    label: str
    lost: bool
    unresolved: bool


CASUALTY_FATES: Mapping[CasualtyFate, CasualtySpec] = total(
    CasualtyFate,
    {
        CasualtyFate.KILLED: CasualtySpec("Killed", lost=True, unresolved=False),
        CasualtyFate.WOUNDED: CasualtySpec("Wounded", lost=False, unresolved=False),
        CasualtyFate.MAIMED: CasualtySpec("Maimed", lost=False, unresolved=False),
        CasualtyFate.CAPTURED: CasualtySpec("Captured", lost=True, unresolved=False),
        CasualtyFate.MISSING: CasualtySpec("Missing", lost=True, unresolved=True),
        CasualtyFate.DESERTED: CasualtySpec("Deserted", lost=True, unresolved=False),
    },
)
UNRESOLVED_FATES = frozenset(fate for fate, spec in CASUALTY_FATES.items() if spec.unresolved)


@dataclass(frozen=True)
class CaptiveSpec:
    label: str
    settles_home: bool
    settles_captor: bool
    killed: bool
    serves_captor: bool


CAPTIVE_FATES: Mapping[CaptiveFate, CaptiveSpec] = total(
    CaptiveFate,
    {
        CaptiveFate.HELD: CaptiveSpec("Held", settles_home=False, settles_captor=False, killed=False, serves_captor=False),
        CaptiveFate.RANSOMED: CaptiveSpec("Ransomed", settles_home=True, settles_captor=False, killed=False, serves_captor=False),
        CaptiveFate.ENSLAVED: CaptiveSpec("Enslaved", settles_home=False, settles_captor=True, killed=False, serves_captor=False),
        CaptiveFate.SACRIFICED: CaptiveSpec("Sacrificed", settles_home=False, settles_captor=False, killed=True, serves_captor=False),
        CaptiveFate.LABOUR: CaptiveSpec("Put to labour", settles_home=False, settles_captor=True, killed=False, serves_captor=False),
        CaptiveFate.EXCHANGED: CaptiveSpec("Exchanged", settles_home=True, settles_captor=False, killed=False, serves_captor=False),
        CaptiveFate.RELEASED: CaptiveSpec("Released", settles_home=True, settles_captor=False, killed=False, serves_captor=False),
        CaptiveFate.EXECUTED: CaptiveSpec("Executed", settles_home=False, settles_captor=False, killed=True, serves_captor=False),
        CaptiveFate.RECRUITED: CaptiveSpec("Recruited", settles_home=False, settles_captor=False, killed=False, serves_captor=True),
    },
)
HOMEWARD_FATES = frozenset(fate for fate, spec in CAPTIVE_FATES.items() if spec.settles_home)
KEPT_FATES = frozenset(fate for fate, spec in CAPTIVE_FATES.items() if spec.settles_captor)


@dataclass(frozen=True)
class SiegeActionSpec:
    label: str
    batters: bool
    works: tuple[SiegeWork, ...]


SIEGE_ACTION_SPECS: Mapping[SiegeAction, SiegeActionSpec] = total(
    SiegeAction,
    {
        SiegeAction.BLOCKADE: SiegeActionSpec("Blockade", False, (SiegeWork.CIRCUMVALLATION, SiegeWork.BLOCKADE_LINES)),
        SiegeAction.BOMBARD: SiegeActionSpec("Bombard", True, (SiegeWork.TOWERS, SiegeWork.RAMS, SiegeWork.BOMBARDMENT)),
        SiegeAction.MINE: SiegeActionSpec("Mine", True, (SiegeWork.MINES, SiegeWork.SAPPING)),
        SiegeAction.ASSAULT: SiegeActionSpec("Assault", False, (SiegeWork.LADDERS, SiegeWork.RAMS, SiegeWork.RAMP)),
        SiegeAction.NEGOTIATE: SiegeActionSpec("Negotiate", False, ()),
        SiegeAction.SUBORN: SiegeActionSpec("Suborn the garrison", False, ()),
    },
)


@dataclass(frozen=True)
class SiegeWorkSpec:
    label: str
    labour_rule: str
    effect_rule: str
    breaches: bool
    covers: bool
    tops_wall: bool
    needs_flight: bool
    needs_network: bool
    needs_rites: bool


SIEGE_WORKS: Mapping[SiegeWork, SiegeWorkSpec] = total(
    SiegeWork,
    {
        SiegeWork.CIRCUMVALLATION: SiegeWorkSpec(
            "Circumvallation", "circumvallation_labour", "circumvallation_effect", False, False, False, False, False, False
        ),
        SiegeWork.TOWERS: SiegeWorkSpec("Siege towers", "towers_labour", "towers_effect", True, False, True, False, False, False),
        SiegeWork.RAMS: SiegeWorkSpec("Rams", "rams_labour", "rams_effect", True, False, False, False, False, False),
        SiegeWork.MINES: SiegeWorkSpec("Mines", "mines_labour", "mines_effect", True, False, False, False, False, False),
        SiegeWork.COUNTERMINES: SiegeWorkSpec("Countermines", "countermines_labour", "countermines_effect", False, False, False, False, False, False),
        SiegeWork.LADDERS: SiegeWorkSpec("Ladders", "ladders_labour", "ladders_effect", False, False, True, False, False, False),
        SiegeWork.BOMBARDMENT: SiegeWorkSpec("Massed bombardment", "bombardment_labour", "bombardment_effect", True, False, False, False, False, False),
        SiegeWork.SAPPING: SiegeWorkSpec("Sapping trenches", "sapping_labour", "sapping_effect", False, True, False, False, False, False),
        SiegeWork.BLOCKADE_LINES: SiegeWorkSpec("Blockade lines", "blockade_lines_labour", "blockade_lines_effect", False, False, False, False, False, False),
        SiegeWork.AIR_ASSAULT: SiegeWorkSpec("Assault from the air", "air_assault_labour", "air_assault_effect", False, False, True, True, False, False),
        SiegeWork.NETWORK_ATTACK: SiegeWorkSpec(
            "Attack on the networks", "network_attack_labour", "network_attack_effect", True, False, False, False, True, False
        ),
        SiegeWork.RITE_BREACH: SiegeWorkSpec("Breaching rite", "rite_breach_labour", "rite_breach_effect", True, False, False, False, False, True),
        SiegeWork.RAMP: SiegeWorkSpec("Siege ramp", "ramp_labour", "ramp_effect", False, False, True, False, False, False),
    },
)
BREACHING_WORKS = frozenset(work for work, spec in SIEGE_WORKS.items() if spec.breaches)
COVERING_WORKS = frozenset(work for work, spec in SIEGE_WORKS.items() if spec.covers)
WALL_TOP_WORKS = frozenset(work for work, spec in SIEGE_WORKS.items() if spec.tops_wall)
ENCIRCLING_WORKS = frozenset({SiegeWork.CIRCUMVALLATION, SiegeWork.BLOCKADE_LINES})
SPECIAL_WORKS = tuple(work for work, spec in SIEGE_WORKS.items() if spec.needs_flight or spec.needs_network or spec.needs_rites)


@dataclass(frozen=True)
class DefenceSpec:
    label: str
    rations: bool
    needs_water: bool


DEFENCES: Mapping[DefenderAction, DefenceSpec] = total(
    DefenderAction,
    {
        DefenderAction.SALLY: DefenceSpec("Sally", rations=False, needs_water=False),
        DefenderAction.REPAIR: DefenceSpec("Repair", rations=False, needs_water=False),
        DefenderAction.RATION: DefenceSpec("Ration", rations=True, needs_water=False),
        DefenderAction.SEEK_RELIEF: DefenceSpec("Seek relief", rations=False, needs_water=False),
        DefenderAction.FLOOD_APPROACHES: DefenceSpec("Flood the approaches", rations=False, needs_water=True),
        DefenderAction.SCORCHED_EARTH: DefenceSpec("Burn the land around", rations=True, needs_water=False),
        DefenderAction.EXPEL_MOUTHS: DefenceSpec("Expel those who cannot fight", rations=True, needs_water=False),
    },
)


@dataclass(frozen=True)
class FallSpec:
    label: str
    plunders: bool
    razes: bool
    spares: bool


FALL_CHOICES: Mapping[SackChoice, FallSpec] = total(
    SackChoice,
    {
        SackChoice.MERCY: FallSpec("Mercy", plunders=False, razes=False, spares=True),
        SackChoice.SACK: FallSpec("Sack", plunders=True, razes=False, spares=False),
        SackChoice.RAZE: FallSpec("Raze", plunders=True, razes=True, spares=False),
        SackChoice.RANSOM_CITY: FallSpec("Ransom the city", plunders=False, razes=False, spares=True),
        SackChoice.DEPORT: FallSpec("Deport its people", plunders=False, razes=False, spares=False),
    },
)


@dataclass(frozen=True)
class SiegeStateSpec:
    label: str
    ended: bool
    fallen: bool


SIEGE_STATES: Mapping[SiegeStatus, SiegeStateSpec] = total(
    SiegeStatus,
    {
        SiegeStatus.ONGOING: SiegeStateSpec("Ongoing", ended=False, fallen=False),
        SiegeStatus.BREACHED: SiegeStateSpec("Breached", ended=True, fallen=True),
        SiegeStatus.REPULSED: SiegeStateSpec("Repulsed", ended=True, fallen=False),
        SiegeStatus.LIFTED: SiegeStateSpec("Lifted", ended=True, fallen=False),
        SiegeStatus.SURRENDERED: SiegeStateSpec("Surrendered on terms", ended=True, fallen=True),
    },
)
FALLEN_STATES = frozenset(state for state, spec in SIEGE_STATES.items() if spec.fallen)


@dataclass(frozen=True)
class OperationSpec:
    label: str
    in_war: bool
    in_peace: bool
    difficulty_rule: str


OPERATIONS: Mapping[SpyOperation, OperationSpec] = total(
    SpyOperation,
    {
        SpyOperation.STEAL_KNOWLEDGE: OperationSpec("Steal knowledge", False, True, "steal_knowledge_difficulty"),
        SpyOperation.SABOTAGE: OperationSpec("Sabotage", True, False, "sabotage_difficulty"),
        SpyOperation.ASSASSINATE: OperationSpec("Assassinate", True, False, "assassinate_difficulty"),
        SpyOperation.INCITE: OperationSpec("Incite", False, True, "incite_difficulty"),
        SpyOperation.INTEL: OperationSpec("Gather intelligence", True, True, "intel_difficulty"),
        SpyOperation.BLACKMAIL: OperationSpec("Blackmail", False, True, "blackmail_difficulty"),
        SpyOperation.COUNTERFEIT: OperationSpec("Counterfeit", False, True, "counterfeit_difficulty"),
        SpyOperation.INFILTRATE: OperationSpec("Infiltrate an institution", False, True, "infiltrate_difficulty"),
        SpyOperation.EXFILTRATE: OperationSpec("Bring an agent out", True, True, "exfiltrate_difficulty"),
        SpyOperation.DISINFORM: OperationSpec("Feed false beliefs", True, True, "disinform_difficulty"),
    },
)
WAR_OPERATIONS = tuple(operation for operation, spec in OPERATIONS.items() if spec.in_war)
PEACE_OPERATIONS = tuple(operation for operation, spec in OPERATIONS.items() if spec.in_peace)


@dataclass(frozen=True)
class MotiveSpec:
    label: str
    loyalty_rule: str
    double_risk_rule: str
    text: str
    bonded: bool
    vengeful: bool


MOTIVES: Mapping[RecruitMotive, MotiveSpec] = total(
    RecruitMotive,
    {
        RecruitMotive.MONEY: MotiveSpec("Money", "money_loyalty", "money_double_risk", "for money", bonded=False, vengeful=False),
        RecruitMotive.IDEOLOGY: MotiveSpec("Belief", "ideology_loyalty", "ideology_double_risk", "for belief", bonded=False, vengeful=False),
        RecruitMotive.COMPROMISE: MotiveSpec("A hook", "compromise_loyalty", "compromise_double_risk", "under a hook", bonded=False, vengeful=False),
        RecruitMotive.EGO: MotiveSpec("Pride", "ego_loyalty", "ego_double_risk", "for pride", bonded=False, vengeful=False),
        RecruitMotive.LOVE: MotiveSpec("Love", "love_loyalty", "love_double_risk", "for love of a handler", bonded=True, vengeful=False),
        RecruitMotive.REVENGE: MotiveSpec("Revenge", "revenge_loyalty", "revenge_double_risk", "for revenge", bonded=False, vengeful=True),
    },
)


@dataclass(frozen=True)
class AgentStateSpec:
    label: str
    reports: bool
    at_large: bool


AGENT_STATES: Mapping[AgentStatus, AgentStateSpec] = total(
    AgentStatus,
    {
        AgentStatus.ACTIVE: AgentStateSpec("Active", reports=True, at_large=True),
        AgentStatus.CAUGHT: AgentStateSpec("Caught", reports=False, at_large=False),
        AgentStatus.TURNED: AgentStateSpec("Turned", reports=False, at_large=True),
        AgentStatus.DEAD: AgentStateSpec("Dead", reports=False, at_large=False),
        AgentStatus.RETIRED: AgentStateSpec("Retired", reports=False, at_large=False),
        AgentStatus.MISSING: AgentStateSpec("Missing", reports=False, at_large=True),
        AgentStatus.EXPOSED: AgentStateSpec("Exposed", reports=True, at_large=True),
    },
)
WORKING_STATES = frozenset(state for state, spec in AGENT_STATES.items() if spec.reports)
AT_LARGE = frozenset(state for state, spec in AGENT_STATES.items() if spec.at_large)
