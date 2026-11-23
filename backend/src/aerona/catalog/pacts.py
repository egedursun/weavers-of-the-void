from collections.abc import Callable, Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.communication import DispatchContent, DispatchState, EnvoyFate, OpinionSubject, SignalState
from aerona.domain.enums.intrigue import FavourOrigin, HookDemand, IdentityReason, IntrigueSecret
from aerona.domain.enums.minds import MadeMindsLaw
from aerona.domain.enums.polity import PartyRole, RegionalStanding, TreatyStatus
from aerona.domain.enums.renown import ClaimKind, ClaimStatus, LorePrice, ServiceTask
from aerona.domain.enums.statecraft import CrisisState, ResolutionKind
from aerona.rules.registry import Rules

Amount = Callable[[Rules], int]


@dataclass(frozen=True)
class RoleSpec:
    label: str
    principal: bool
    defends: bool = False
    settles: bool = False


PARTY_ROLES: Mapping[PartyRole, RoleSpec] = total(
    PartyRole,
    {
        PartyRole.SIGNATORY: RoleSpec("Signatory", True),
        PartyRole.OVERLORD: RoleSpec("Overlord", True),
        PartyRole.VASSAL: RoleSpec("Vassal", True),
        PartyRole.GUARANTOR: RoleSpec("Guarantor", False, defends=True),
        PartyRole.MEDIATOR: RoleSpec("Mediator", False, settles=True),
    },
)
PRINCIPAL_ROLES = frozenset(role for role, spec in PARTY_ROLES.items() if spec.principal)


@dataclass(frozen=True)
class TreatyStateSpec:
    label: str
    binds: bool
    paused: bool = False


TREATY_STATES: Mapping[TreatyStatus, TreatyStateSpec] = total(
    TreatyStatus,
    {
        TreatyStatus.IN_FORCE: TreatyStateSpec("In force", True),
        TreatyStatus.FULFILLED: TreatyStateSpec("Fulfilled", False),
        TreatyStatus.BROKEN: TreatyStateSpec("Broken", False),
        TreatyStatus.EXPIRED: TreatyStateSpec("Expired", False),
        TreatyStatus.PROPOSED: TreatyStateSpec("Proposed", False),
        TreatyStatus.REJECTED: TreatyStateSpec("Rejected", False),
        TreatyStatus.SUSPENDED: TreatyStateSpec("Suspended", False, paused=True),
    },
)
PAUSED_STATES = frozenset(state for state, spec in TREATY_STATES.items() if spec.paused)
BREAKABLE_STATES = frozenset(state for state, spec in TREATY_STATES.items() if spec.binds or spec.paused)


@dataclass(frozen=True)
class CrisisStateSpec:
    label: str
    open: bool
    third_party: bool = False


CRISIS_STATES: Mapping[CrisisState, CrisisStateSpec] = total(
    CrisisState,
    {
        CrisisState.ESCALATING: CrisisStateSpec("Escalating", True),
        CrisisState.BACKED_DOWN: CrisisStateSpec("Backed down", False),
        CrisisState.CONCEDED: CrisisStateSpec("Conceded", False),
        CrisisState.WAR: CrisisStateSpec("War", False),
        CrisisState.MEDIATED: CrisisStateSpec("Settled by a mediator", False, third_party=True),
    },
)
THIRD_PARTY_STATES = frozenset(state for state, spec in CRISIS_STATES.items() if spec.third_party)


@dataclass(frozen=True)
class StandingSpec:
    label: str
    war_pct: Amount
    allies: bool = True
    declared: bool = False


STANDINGS: Mapping[RegionalStanding, StandingSpec] = total(
    RegionalStanding,
    {
        RegionalStanding.HEGEMON: StandingSpec("Hegemon", lambda rules: rules.treaties.hegemon_war_pct),
        RegionalStanding.GREAT_POWER: StandingSpec("Great power", lambda rules: rules.treaties.great_war_pct),
        RegionalStanding.MINOR_POWER: StandingSpec("Minor power", lambda rules: rules.treaties.minor_war_pct),
        RegionalStanding.CLIENT: StandingSpec("Client", lambda rules: rules.treaties.client_war_pct),
        RegionalStanding.NEUTRAL: StandingSpec("Neutral", lambda rules: rules.treaties.minor_war_pct, allies=False, declared=True),
    },
)
DECLARED_STANDINGS = frozenset(standing for standing, spec in STANDINGS.items() if spec.declared)


@dataclass(frozen=True)
class ResolutionSpec:
    effect: Amount
    needs_target: bool


RESOLUTIONS: Mapping[ResolutionKind, ResolutionSpec] = total(
    ResolutionKind,
    {
        ResolutionKind.ROUTE_SECURITY: ResolutionSpec(lambda rules: rules.council_of_worlds.route_security_effect, False),
        ResolutionKind.EMBARGO: ResolutionSpec(lambda rules: rules.council_of_worlds.embargo_effect, True),
        ResolutionKind.VOID_BAN: ResolutionSpec(lambda rules: rules.council_of_worlds.void_ban_effect, False),
        ResolutionKind.SANCTION: ResolutionSpec(lambda rules: rules.council_of_worlds.sanction_effect, True),
        ResolutionKind.QUARANTINE: ResolutionSpec(lambda rules: rules.council_of_worlds.quarantine_effect, True),
        ResolutionKind.ARBITRATION: ResolutionSpec(lambda rules: rules.council_of_worlds.arbitration_effect, True),
        ResolutionKind.AID: ResolutionSpec(lambda rules: rules.council_of_worlds.aid_effect, True),
    },
)


@dataclass(frozen=True)
class ContentSpec:
    commands: bool = False
    warns: bool = False


DISPATCH_CONTENTS: Mapping[DispatchContent, ContentSpec] = total(
    DispatchContent,
    {
        DispatchContent.PROPOSAL: ContentSpec(),
        DispatchContent.DEMAND: ContentSpec(),
        DispatchContent.THREAT: ContentSpec(),
        DispatchContent.INSULT: ContentSpec(),
        DispatchContent.GIFT_NOTICE: ContentSpec(),
        DispatchContent.DECLARATION: ContentSpec(),
        DispatchContent.REPORT: ContentSpec(),
        DispatchContent.PLEA: ContentSpec(),
        DispatchContent.INTELLIGENCE: ContentSpec(),
        DispatchContent.ORDER: ContentSpec(commands=True),
        DispatchContent.WARNING: ContentSpec(warns=True),
    },
)


@dataclass(frozen=True)
class DispatchStateSpec:
    travelling: bool
    arrived: bool


DISPATCH_STATES: Mapping[DispatchState, DispatchStateSpec] = total(
    DispatchState,
    {
        DispatchState.UNDER_WAY: DispatchStateSpec(True, False),
        DispatchState.DELIVERED: DispatchStateSpec(False, True),
        DispatchState.INTERCEPTED: DispatchStateSpec(False, False),
        DispatchState.LOST: DispatchStateSpec(False, False),
        DispatchState.DELAYED: DispatchStateSpec(True, False),
        DispatchState.FORGED: DispatchStateSpec(False, True),
        DispatchState.MISREAD: DispatchStateSpec(False, True),
    },
)
TRAVELLING_STATES = frozenset(state for state, spec in DISPATCH_STATES.items() if spec.travelling)
ARRIVED_STATES = frozenset(state for state, spec in DISPATCH_STATES.items() if spec.arrived)


@dataclass(frozen=True)
class EnvoyFateSpec:
    harmed: bool
    goes_home: bool


ENVOY_FATES: Mapping[EnvoyFate, EnvoyFateSpec] = total(
    EnvoyFate,
    {
        EnvoyFate.RECEIVED: EnvoyFateSpec(False, True),
        EnvoyFate.INSULTED: EnvoyFateSpec(True, True),
        EnvoyFate.IMPRISONED: EnvoyFateSpec(True, False),
        EnvoyFate.KILLED: EnvoyFateSpec(True, False),
        EnvoyFate.EXPELLED: EnvoyFateSpec(True, True),
        EnvoyFate.DEFECTED: EnvoyFateSpec(False, False),
    },
)


@dataclass(frozen=True)
class SignalStateSpec:
    carries: bool
    restorable: bool


SIGNAL_STATES: Mapping[SignalState, SignalStateSpec] = total(
    SignalState,
    {
        SignalState.ACTIVE: SignalStateSpec(True, False),
        SignalState.CAPTURED: SignalStateSpec(True, False),
        SignalState.BURNED: SignalStateSpec(False, False),
        SignalState.DISUSED: SignalStateSpec(False, True),
        SignalState.JAMMED: SignalStateSpec(False, True),
    },
)

CARRYING_STATES = frozenset(state for state, spec in SIGNAL_STATES.items() if spec.carries)


OPINION_WEIGHTS: Mapping[OpinionSubject, Amount] = total(
    OpinionSubject,
    {
        OpinionSubject.RULER: lambda rules: rules.opinion_subjects.ruler_weight,
        OpinionSubject.LAW: lambda rules: rules.opinion_subjects.law_weight,
        OpinionSubject.WAR: lambda rules: rules.opinion_subjects.war_weight,
        OpinionSubject.GOD: lambda rules: rules.opinion_subjects.god_weight,
        OpinionSubject.IDEOLOGY: lambda rules: rules.opinion_subjects.ideology_weight,
        OpinionSubject.FACTION: lambda rules: rules.opinion_subjects.faction_weight,
        OpinionSubject.FOREIGN_POWER: lambda rules: rules.opinion_subjects.foreign_power_weight,
    },
)


@dataclass(frozen=True)
class PriceSpec:
    deferred: bool = False
    swaps: bool = False


LORE_PRICES: Mapping[LorePrice, PriceSpec] = total(
    LorePrice,
    {
        LorePrice.WEALTH: PriceSpec(),
        LorePrice.FAVOUR: PriceSpec(),
        LorePrice.RENOWN: PriceSpec(),
        LorePrice.EXCHANGE: PriceSpec(swaps=True),
        LorePrice.SERVICE: PriceSpec(deferred=True),
    },
)
SERVICE_TASKS: Mapping[ServiceTask, str] = total(
    ServiceTask,
    {
        ServiceTask.QUEST: "A quest",
        ServiceTask.THEFT: "A theft",
        ServiceTask.KILLING: "A killing",
        ServiceTask.RITE: "A rite",
    },
)


@dataclass(frozen=True)
class ClaimSpec:
    takes_all: bool
    contestable: bool


CLAIM_KINDS: Mapping[ClaimKind, ClaimSpec] = total(
    ClaimKind,
    {
        ClaimKind.TRUE: ClaimSpec(True, False),
        ClaimKind.SHARED: ClaimSpec(False, False),
        ClaimKind.FALSE: ClaimSpec(True, True),
        ClaimKind.INFLATED: ClaimSpec(True, True),
    },
)
CONTESTABLE_CLAIMS = frozenset(kind for kind, spec in CLAIM_KINDS.items() if spec.contestable)


@dataclass(frozen=True)
class ClaimStateSpec:
    credit_pct: int
    settled: bool


CLAIM_STATES: Mapping[ClaimStatus, ClaimStateSpec] = total(
    ClaimStatus,
    {
        ClaimStatus.STANDING: ClaimStateSpec(100, False),
        ClaimStatus.VERIFIED: ClaimStateSpec(100, True),
        ClaimStatus.EXPOSED: ClaimStateSpec(0, True),
        ClaimStatus.DISPUTED: ClaimStateSpec(50, False),
    },
)
UNSETTLED_CLAIMS = frozenset(state for state, spec in CLAIM_STATES.items() if not spec.settled)


SECRET_WEIGHTS: Mapping[IntrigueSecret, Amount] = total(
    IntrigueSecret,
    {
        IntrigueSecret.AFFAIR: lambda rules: rules.secret_kinds.affair_severity,
        IntrigueSecret.ILLEGITIMATE_CHILD: lambda rules: rules.secret_kinds.illegitimate_child_severity,
        IntrigueSecret.MURDER: lambda rules: rules.secret_kinds.murder_severity,
        IntrigueSecret.HERESY: lambda rules: rules.secret_kinds.heresy_severity,
        IntrigueSecret.SECRET_CULT_MEMBERSHIP: lambda rules: rules.secret_kinds.secret_cult_membership_severity,
        IntrigueSecret.DEBT: lambda rules: rules.secret_kinds.debt_severity,
        IntrigueSecret.CRIME: lambda rules: rules.secret_kinds.crime_severity,
        IntrigueSecret.COWARDICE_IN_BATTLE: lambda rules: rules.secret_kinds.cowardice_in_battle_severity,
        IntrigueSecret.HIDDEN_CONDITION: lambda rules: rules.secret_kinds.hidden_condition_severity,
        IntrigueSecret.FALSE_IDENTITY: lambda rules: rules.secret_kinds.false_identity_severity,
        IntrigueSecret.DEAL_WITH_OUTER_BEING: lambda rules: rules.secret_kinds.deal_with_outer_being_severity,
        IntrigueSecret.TRUE_PARENTAGE: lambda rules: rules.secret_kinds.true_parentage_severity,
        IntrigueSecret.BROKEN_OATH: lambda rules: rules.secret_kinds.broken_oath_severity,
        IntrigueSecret.ECOSABOTAGE: lambda rules: rules.secret_kinds.ecosabotage_severity,
        IntrigueSecret.BROKEN_CIPHER: lambda rules: rules.secret_kinds.broken_cipher_severity,
        IntrigueSecret.TRUE_HISTORY: lambda rules: rules.secret_kinds.true_history_severity,
        IntrigueSecret.HIDDEN_POWER: lambda rules: rules.secret_kinds.hidden_power_severity,
        IntrigueSecret.FORGERY: lambda rules: rules.secret_kinds.forgery_severity,
    },
)
HOOK_COSTS: Mapping[HookDemand, Amount] = total(
    HookDemand,
    {
        HookDemand.MARRIAGE: lambda rules: rules.hooks.marriage_cost,
        HookDemand.STEP_DOWN: lambda rules: rules.hooks.step_down_cost,
        HookDemand.SUPPORT: lambda rules: rules.hooks.support_cost,
        HookDemand.VOTE: lambda rules: rules.hooks.vote_cost,
        HookDemand.LAW: lambda rules: rules.hooks.law_cost,
        HookDemand.APPOINTMENT: lambda rules: rules.hooks.appointment_cost,
        HookDemand.SILENCE: lambda rules: rules.hooks.silence_cost,
        HookDemand.PAYMENT: lambda rules: rules.hooks.payment_cost,
    },
)
FAVOUR_WEIGHTS: Mapping[FavourOrigin, Amount] = total(
    FavourOrigin,
    {
        FavourOrigin.GIFT: lambda rules: rules.favours.gift_weight,
        FavourOrigin.RESCUE: lambda rules: rules.favours.rescue_weight,
        FavourOrigin.WAR_SUPPORT: lambda rules: rules.favours.war_support_weight,
        FavourOrigin.SUCCESSION_SUPPORT: lambda rules: rules.favours.succession_support_weight,
        FavourOrigin.SCHEME_AID: lambda rules: rules.favours.scheme_aid_weight,
        FavourOrigin.VOTE: lambda rules: rules.favours.vote_weight,
        FavourOrigin.RELIEF: lambda rules: rules.favours.relief_weight,
        FavourOrigin.HOSPITALITY: lambda rules: rules.favours.hospitality_weight,
        FavourOrigin.RANSOM: lambda rules: rules.favours.ransom_weight,
    },
)


@dataclass(frozen=True)
class IdentitySpec:
    secret: IntrigueSecret
    persecuted: bool = False


IDENTITY_REASONS: Mapping[IdentityReason, IdentitySpec] = total(
    IdentityReason,
    {
        IdentityReason.SPY: IdentitySpec(IntrigueSecret.FALSE_IDENTITY),
        IdentityReason.BLOOD_CURSE: IdentitySpec(IntrigueSecret.FALSE_IDENTITY),
        IdentityReason.EXILE: IdentitySpec(IntrigueSecret.FALSE_IDENTITY),
        IdentityReason.IMPOSTOR: IdentitySpec(IntrigueSecret.FALSE_IDENTITY),
        IdentityReason.HIDDEN_POWER: IdentitySpec(IntrigueSecret.HIDDEN_POWER),
        IdentityReason.FUGITIVE: IdentitySpec(IntrigueSecret.FALSE_IDENTITY),
        IdentityReason.HIDDEN_FAITH: IdentitySpec(IntrigueSecret.HERESY, persecuted=True),
        IdentityReason.PASSING_KIND: IdentitySpec(IntrigueSecret.FALSE_IDENTITY, persecuted=True),
    },
)
WILLLESS_LAWS = frozenset({MadeMindsLaw.NO_WILL, MadeMindsLaw.INSTRUCTED_ONLY})
