from pydantic import Field

from aerona.core.grammar import several
from aerona.db.tables.unions import UNION_TERM_MAX
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.cycles import (
    ChallengeKind,
    CousinTerms,
    CyclePhase,
    DescentGroup,
    GiftOccasion,
    KinshipDescent,
    LabourRegime,
    LegacyKind,
    LongPlanKind,
    ManumissionPath,
    MarriagePayment,
    MarriagePreference,
    MobilityMode,
    ReproductiveCaste,
    ReproductiveSystem,
    ResidenceRule,
)
from aerona.domain.enums.unions import PartnerScope, UnionArrangement, UnionDescent, UnionDissolution, UnionExchange, UnionForm, UnionPurpose, UnionResidence
from aerona.engine.cycles import control
from aerona.services.player.cosmography import Edited
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

SPAN = 100
MANY = 1_000_000_000
NAME = 200


class StressDraft(Command):
    polity_id: int
    pressure: int = Field(default=0, ge=0, le=SPAN)
    immiseration: int = Field(default=0, ge=0, le=SPAN)
    elite_overproduction: int = Field(default=0, ge=0, le=SPAN)
    fiscal_distress: int = Field(default=0, ge=0, le=SPAN)
    phase: CyclePhase = CyclePhase.GROWTH


class PolityTarget(Command):
    polity_id: int


class StressEdit(Edited):
    polity_id: int


class ReadingDraft(Command):
    polity_id: int
    epoch: int = Field(ge=0)
    psi: int = Field(default=0, ge=0, le=SPAN)
    phase: CyclePhase = CyclePhase.GROWTH


class ReadingTarget(Command):
    polity_id: int
    epoch: int = Field(ge=0)


class ReadingEdit(Edited):
    polity_id: int
    epoch: int = Field(ge=0)


class AsabiyyaDraft(Command):
    holder_id: int
    value: int = Field(default=50, ge=0, le=SPAN)
    conflict: int = Field(default=0, ge=0, le=SPAN)


class HolderTarget(Command):
    holder_id: int


class HolderEdit(Edited):
    holder_id: int


class ChallengeDraft(Command):
    polity_id: int
    kind: ChallengeKind = ChallengeKind.DISASTER
    severity: int = Field(default=30, ge=0, le=SPAN)


class ChallengeTarget(Command):
    challenge_id: int


class ChallengeEdit(Edited):
    challenge_id: int


class PlanDraft(Command):
    holder_id: int
    kind: LongPlanKind
    name: str = Field(min_length=1, max_length=NAME)
    target_id: int | None = None
    carrier_id: int | None = None
    steps: int = Field(default=10, ge=1, le=10_000)
    step_cost: int = Field(default=10, ge=0, le=MANY)
    secrecy: int = Field(default=50, ge=0, le=SPAN)


class PlanTarget(Command):
    plan_id: int


class PlanEdit(Edited):
    plan_id: int


class PlanAdvance(Command):
    plan_id: int
    steps: int = Field(default=1, ge=-10_000, le=10_000)


class GiftDraft(Command):
    giver_id: int
    receiver_id: int
    value: int = Field(default=10, ge=0, le=MANY)
    occasion: GiftOccasion = GiftOccasion.COURTESY
    item_id: int | None = None


class GiftTarget(Command):
    gift_id: int


class GiftEdit(Edited):
    gift_id: int


class GiftAnswer(Command):
    gift_id: int
    value: int | None = Field(default=None, ge=0, le=MANY)


class CircuitDraft(Command):
    name: str = Field(min_length=1, max_length=NAME)
    stops: list[int] = Field(min_length=2)
    item_id: int | None = None


class CircuitTarget(Command):
    circuit_id: int


class CircuitEdit(Edited):
    circuit_id: int


class CircuitRoute(Command):
    circuit_id: int
    stops: list[int] = Field(min_length=2)


class DebtDraft(Command):
    god_id: int
    community_id: int
    offered: int = Field(default=0, ge=0, le=MANY)
    answered: int = Field(default=0, ge=0, le=MANY)


class DebtTarget(Command):
    god_id: int
    community_id: int


class DebtEdit(Edited):
    god_id: int
    community_id: int


class KinshipDraft(Command):
    people_id: int
    descent: KinshipDescent = KinshipDescent.BILATERAL
    residence: ResidenceRule = ResidenceRule.NEOLOCAL
    descent_group: DescentGroup = DescentGroup.LINEAGE
    cousin_terms: CousinTerms = CousinTerms.DISTINCT
    preference: MarriagePreference = MarriagePreference.NONE
    payment: MarriagePayment = MarriagePayment.NONE
    payment_value: int = Field(default=10, ge=0, le=MANY)
    levirate: bool = False
    sororate: bool = False


class UnionDraft(Command):
    people_id: int
    form: UnionForm = UnionForm.PAIR
    purpose: UnionPurpose = UnionPurpose.KINSHIP
    residence: UnionResidence = UnionResidence.NEW_HOUSEHOLD
    descent: UnionDescent = UnionDescent.THROUGH_BOTH
    exchange: UnionExchange = UnionExchange.NONE
    arrangement: UnionArrangement = UnionArrangement.BOTH_CONSENT
    dissolution: UnionDissolution = UnionDissolution.BY_CUSTOM
    endogamy: PartnerScope = PartnerScope.NONE
    exogamy: PartnerScope = PartnerScope.NONE
    term_epochs: int = Field(default=4, ge=1, le=UNION_TERM_MAX)


class PeopleTarget(Command):
    people_id: int


class PeopleEdit(Edited):
    people_id: int


class AllianceDraft(Command):
    giver_id: int
    taker_id: int
    marriages: int = Field(default=1, ge=0, le=MANY)


class AllianceTarget(Command):
    giver_id: int
    taker_id: int


class AllianceEdit(Edited):
    giver_id: int
    taker_id: int


class ReproductionDraft(Command):
    people_id: int
    system: ReproductiveSystem = ReproductiveSystem.TWO_SEX
    change_age: int = Field(default=30, ge=0, le=MANY)
    breeder_pct: int = Field(default=10, ge=0, le=SPAN)
    soldier_pct: int = Field(default=20, ge=0, le=SPAN)
    worker_pct: int = Field(default=70, ge=0, le=SPAN)


class CasteDraft(Command):
    mortal_id: int
    caste: ReproductiveCaste = ReproductiveCaste.WORKER


class MortalTarget(Command):
    mortal_id: int


class MortalEdit(Edited):
    mortal_id: int


class CampDraft(Command):
    town_id: int
    mode: MobilityMode = MobilityMode.NOMADIC
    herd: int = Field(default=100, ge=0, le=MANY)


class TownTarget(Command):
    town_id: int


class TownEdit(Edited):
    town_id: int


class CampRoute(Command):
    town_id: int
    regions: list[int] = Field(min_length=1)


class ConfederationDraft(Command):
    name: str = Field(min_length=1, max_length=NAME)
    leader_id: int | None = None
    members: list[int] = Field(min_length=2)


class ConfederationTarget(Command):
    confederation_id: int


class ConfederationEdit(Edited):
    confederation_id: int


class ConfederationMembers(Command):
    confederation_id: int
    members: list[int] = Field(min_length=2)


class LegacyDraft(Command):
    people_id: int
    kind: LegacyKind
    key: str = Field(min_length=1, max_length=80)
    predecessor_id: int | None = None


class LegacyTarget(Command):
    people_id: int
    kind: LegacyKind
    key: str = Field(min_length=1, max_length=80)


class LegacyEdit(Edited):
    people_id: int
    kind: LegacyKind
    key: str = Field(min_length=1, max_length=80)


class IndentureDraft(Command):
    community_id: int
    regime: LabourRegime = LabourRegime.INDENTURE
    count: int = Field(default=10, ge=0, le=MANY)
    term_epochs: int = Field(default=3, ge=0, le=10_000)
    debt: int = Field(default=50, ge=0, le=MANY)
    exploitation: int = Field(default=30, ge=0, le=SPAN)
    employer_id: int | None = None
    origin_id: int | None = None


class IndentureTarget(Command):
    indenture_id: int


class IndentureEdit(Edited):
    indenture_id: int


class MarketDraft(Command):
    town_id: int
    price: int = Field(default=20, ge=0, le=MANY)
    open: bool = True


class FreeDraft(Command):
    community_id: int
    share_pct: int = Field(default=50, ge=0, le=SPAN)
    path: ManumissionPath = ManumissionPath.LAW


class ManumissionTarget(Command):
    manumission_id: int


class ManumissionEdit(Edited):
    manumission_id: int


@player_action("stress:set", ActionKind.EDIT_RECORD)
async def stress_set(scope: PlayerScope, command: StressDraft) -> Effect:
    values = {
        "pressure": command.pressure,
        "immiseration": command.immiseration,
        "elite_overproduction": command.elite_overproduction,
        "fiscal_distress": command.fiscal_distress,
        "phase": command.phase.value,
    }
    await control.set_stress(await scope.context("stress_set"), command.polity_id, values)
    return Effect("The realm's strains are set.", command.polity_id)


@player_action("stress:edit", ActionKind.EDIT_RECORD)
async def stress_edit(scope: PlayerScope, command: StressEdit) -> Effect:
    await control.edit_record(await scope.context("stress_edit"), "stress", command.polity_id, command.values, command.release)
    return Effect("The realm's strains are set so.", command.polity_id)


@player_action("stress:delete", ActionKind.EDIT_RECORD)
async def stress_delete(scope: PlayerScope, command: PolityTarget) -> Effect:
    await control.delete_record(await scope.context("stress_delete"), "stress", command.polity_id)
    return Effect("The realm's strains will be read anew.", command.polity_id)


@player_action("stress_reading:set", ActionKind.EDIT_RECORD)
async def stress_reading_set(scope: PlayerScope, command: ReadingDraft) -> Effect:
    await control.set_reading(await scope.context("stress_reading_set"), command.polity_id, command.epoch, {"psi": command.psi, "phase": command.phase.value})
    return Effect("The past reading is written.", command.polity_id)


@player_action("stress_reading:edit", ActionKind.EDIT_RECORD)
async def stress_reading_edit(scope: PlayerScope, command: ReadingEdit) -> Effect:
    await control.edit_record(await scope.context("stress_reading_edit"), "stress_reading", (command.polity_id, command.epoch), command.values, command.release)
    return Effect("The past reading is set so.", command.polity_id)


@player_action("stress_reading:delete", ActionKind.EDIT_RECORD)
async def stress_reading_delete(scope: PlayerScope, command: ReadingTarget) -> Effect:
    await control.delete_record(await scope.context("stress_reading_delete"), "stress_reading", (command.polity_id, command.epoch))
    return Effect("The past reading is struck from the record.", command.polity_id)


@player_action("asabiyya:set", ActionKind.EDIT_RECORD)
async def asabiyya_set(scope: PlayerScope, command: AsabiyyaDraft) -> Effect:
    await control.set_asabiyya(await scope.context("asabiyya_set"), command.holder_id, {"value": command.value, "conflict": command.conflict})
    return Effect("Their solidarity is set.", command.holder_id)


@player_action("asabiyya:edit", ActionKind.EDIT_RECORD)
async def asabiyya_edit(scope: PlayerScope, command: HolderEdit) -> Effect:
    await control.edit_record(await scope.context("asabiyya_edit"), "asabiyya", command.holder_id, command.values, command.release)
    return Effect("Their solidarity is set so.", command.holder_id)


@player_action("asabiyya:delete", ActionKind.EDIT_RECORD)
async def asabiyya_delete(scope: PlayerScope, command: HolderTarget) -> Effect:
    await control.delete_record(await scope.context("asabiyya_delete"), "asabiyya", command.holder_id)
    return Effect("Their solidarity will grow anew.", command.holder_id)


@player_action("challenge:strike", ActionKind.EDIT_RECORD)
async def challenge_strike(scope: PlayerScope, command: ChallengeDraft) -> Effect:
    row = await control.strike_challenge(await scope.context("challenge_strike"), command.polity_id, command.kind, command.severity)
    return Effect(f"The realm is tried; its answer: {row.response.value}.", command.polity_id, values={"response": row.response.value})


@player_action("challenge:edit", ActionKind.EDIT_RECORD)
async def challenge_edit(scope: PlayerScope, command: ChallengeEdit) -> Effect:
    row = await control.edit_record(await scope.context("challenge_edit"), "challenge", command.challenge_id, command.values, command.release)
    return Effect("The challenge is set so.", getattr(row, "holder_entity_id", None))


@player_action("challenge:delete", ActionKind.EDIT_RECORD)
async def challenge_delete(scope: PlayerScope, command: ChallengeTarget) -> Effect:
    await control.delete_record(await scope.context("challenge_delete"), "challenge", command.challenge_id)
    return Effect("The challenge is struck from the record.")


@player_action("plan:create", ActionKind.EDIT_RECORD)
async def plan_create(scope: PlayerScope, command: PlanDraft) -> Effect:
    row = await control.new_plan(
        await scope.context("plan_create"),
        command.holder_id,
        command.kind,
        command.name,
        target_id=command.target_id,
        carrier_id=command.carrier_id,
        steps=command.steps,
        step_cost=command.step_cost,
        secrecy=command.secrecy,
    )
    return Effect(f"{row.name} is set in motion.", command.holder_id, values={"plan_id": row.id})


@player_action("plan:edit", ActionKind.EDIT_RECORD)
async def plan_edit(scope: PlayerScope, command: PlanEdit) -> Effect:
    row = await control.edit_record(await scope.context("plan_edit"), "plan", command.plan_id, command.values, command.release)
    return Effect("The long plan is set so.", getattr(row, "holder_node_id", None))


@player_action("plan:advance", ActionKind.EDIT_RECORD)
async def plan_advance(scope: PlayerScope, command: PlanAdvance) -> Effect:
    row = await control.advance_plan(await scope.context("plan_advance"), command.plan_id, command.steps)
    return Effect(f"{row.name} stands at {row.progress} of {several(row.steps, 'step', 'steps')}.", row.holder_node_id, values={"progress": row.progress})


@player_action("plan:expose", ActionKind.EDIT_RECORD)
async def plan_expose(scope: PlayerScope, command: PlanTarget) -> Effect:
    row = await control.expose_plan(await scope.context("plan_expose"), command.plan_id)
    return Effect(f"{row.name} is laid bare.", row.holder_node_id)


@player_action("plan:delete", ActionKind.EDIT_RECORD)
async def plan_delete(scope: PlayerScope, command: PlanTarget) -> Effect:
    await control.delete_record(await scope.context("plan_delete"), "plan", command.plan_id)
    return Effect("The long plan is struck from the record.")


@player_action("gift:give", ActionKind.EDIT_RECORD)
async def gift_give(scope: PlayerScope, command: GiftDraft) -> Effect:
    ctx = await scope.context("gift_give")
    row = await control.give_gift(ctx, command.giver_id, command.receiver_id, command.value, occasion=command.occasion, item_id=command.item_id)
    return Effect(f"A gift worth {row.value} is given.", command.receiver_id, values={"gift_id": row.id})


@player_action("gift:return", ActionKind.EDIT_RECORD)
async def gift_return(scope: PlayerScope, command: GiftAnswer) -> Effect:
    row = await control.answer_gift(await scope.context("gift_return"), command.gift_id, command.value)
    return Effect(f"The gift is answered with one worth {row.value}.", row.receiver_node_id)


@player_action("gift:refuse", ActionKind.EDIT_RECORD)
async def gift_refuse(scope: PlayerScope, command: GiftTarget) -> Effect:
    row = await control.refuse_gift(await scope.context("gift_refuse"), command.gift_id)
    return Effect("The gift is refused.", row.giver_node_id)


@player_action("gift:edit", ActionKind.EDIT_RECORD)
async def gift_edit(scope: PlayerScope, command: GiftEdit) -> Effect:
    row = await control.edit_record(await scope.context("gift_edit"), "gift", command.gift_id, command.values, command.release)
    return Effect("The gift is set so.", getattr(row, "receiver_node_id", None))


@player_action("gift:delete", ActionKind.EDIT_RECORD)
async def gift_delete(scope: PlayerScope, command: GiftTarget) -> Effect:
    await control.delete_record(await scope.context("gift_delete"), "gift", command.gift_id)
    return Effect("The gift is struck from the ledger.")


@player_action("circuit:create", ActionKind.EDIT_RECORD)
async def circuit_create(scope: PlayerScope, command: CircuitDraft) -> Effect:
    row = await control.new_circuit(await scope.context("circuit_create"), command.name, command.stops, command.item_id)
    return Effect(f"{row.name} begins to turn.", command.stops[0], values={"circuit_id": row.id})


@player_action("circuit:edit", ActionKind.EDIT_RECORD)
async def circuit_edit(scope: PlayerScope, command: CircuitEdit) -> Effect:
    await control.edit_record(await scope.context("circuit_edit"), "circuit", command.circuit_id, command.values, command.release)
    return Effect("The circuit is set so.")


@player_action("circuit:route", ActionKind.EDIT_RECORD)
async def circuit_route(scope: PlayerScope, command: CircuitRoute) -> Effect:
    row = await control.route_circuit(await scope.context("circuit_route"), command.circuit_id, command.stops)
    return Effect(f"{row.name} now turns through {several(len(row.stops), 'stop', 'stops')}.", command.stops[0])


@player_action("circuit:pass", ActionKind.EDIT_RECORD)
async def circuit_pass(scope: PlayerScope, command: CircuitTarget) -> Effect:
    row = await control.turn_circuit(await scope.context("circuit_pass"), command.circuit_id)
    return Effect(f"The treasure of {row.name} moves on.", values={"position": row.position})


@player_action("circuit:delete", ActionKind.EDIT_RECORD)
async def circuit_delete(scope: PlayerScope, command: CircuitTarget) -> Effect:
    await control.delete_record(await scope.context("circuit_delete"), "circuit", command.circuit_id)
    return Effect("The circuit stops turning.")


@player_action("debt:set", ActionKind.EDIT_RECORD)
async def debt_set(scope: PlayerScope, command: DebtDraft) -> Effect:
    values = {"offered": command.offered, "answered": command.answered}
    await control.set_debt(await scope.context("debt_set"), command.god_id, command.community_id, values)
    return Effect("The ledger of offerings is set.", command.community_id)


@player_action("debt:edit", ActionKind.EDIT_RECORD)
async def debt_edit(scope: PlayerScope, command: DebtEdit) -> Effect:
    await control.edit_record(await scope.context("debt_edit"), "debt", (command.god_id, command.community_id), command.values, command.release)
    return Effect("The ledger of offerings is set so.", command.community_id)


@player_action("debt:delete", ActionKind.EDIT_RECORD)
async def debt_delete(scope: PlayerScope, command: DebtTarget) -> Effect:
    await control.delete_record(await scope.context("debt_delete"), "debt", (command.god_id, command.community_id))
    return Effect("The ledger of offerings is cleared.", command.community_id)


@player_action("kinship:set", ActionKind.EDIT_RECORD)
async def kinship_set(scope: PlayerScope, command: KinshipDraft) -> Effect:
    values = {
        "descent": command.descent.value,
        "residence": command.residence.value,
        "descent_group": command.descent_group.value,
        "cousin_terms": command.cousin_terms.value,
        "preference": command.preference.value,
        "payment": command.payment.value,
        "payment_value": command.payment_value,
        "levirate": command.levirate,
        "sororate": command.sororate,
    }
    await control.set_kinship(await scope.context("kinship_set"), command.people_id, values)
    return Effect("Their ways of kin are set.", command.people_id)


@player_action("kinship:edit", ActionKind.EDIT_RECORD)
async def kinship_edit(scope: PlayerScope, command: PeopleEdit) -> Effect:
    await control.edit_record(await scope.context("kinship_edit"), "kinship", command.people_id, command.values, command.release)
    return Effect("Their ways of kin are set so.", command.people_id)


@player_action("kinship:delete", ActionKind.EDIT_RECORD)
async def kinship_delete(scope: PlayerScope, command: PeopleTarget) -> Effect:
    await control.delete_record(await scope.context("kinship_delete"), "kinship", command.people_id)
    return Effect("Their ways of kin will be read anew from their customs.", command.people_id)


@player_action("union:set", ActionKind.EDIT_RECORD)
async def union_set(scope: PlayerScope, command: UnionDraft) -> Effect:
    values = command.model_dump(exclude={"people_id"}, mode="json")
    await control.set_union(await scope.context("union_set"), command.people_id, values)
    return Effect("Their customs of union are set.", command.people_id)


@player_action("union:edit", ActionKind.EDIT_RECORD)
async def union_edit(scope: PlayerScope, command: PeopleEdit) -> Effect:
    await control.edit_record(await scope.context("union_edit"), "union", command.people_id, command.values, command.release)
    return Effect("Their customs of union are set so.", command.people_id)


@player_action("union:delete", ActionKind.EDIT_RECORD)
async def union_delete(scope: PlayerScope, command: PeopleTarget) -> Effect:
    await control.delete_record(await scope.context("union_delete"), "union", command.people_id)
    return Effect("Their customs of union will be read anew from their ways.", command.people_id)


@player_action("alliance:set", ActionKind.EDIT_RECORD)
async def alliance_set(scope: PlayerScope, command: AllianceDraft) -> Effect:
    await control.set_alliance(await scope.context("alliance_set"), command.giver_id, command.taker_id, {"marriages": command.marriages})
    return Effect("The marriage alliance is set.", command.taker_id)


@player_action("alliance:edit", ActionKind.EDIT_RECORD)
async def alliance_edit(scope: PlayerScope, command: AllianceEdit) -> Effect:
    await control.edit_record(await scope.context("alliance_edit"), "alliance", (command.giver_id, command.taker_id), command.values, command.release)
    return Effect("The marriage alliance is set so.", command.taker_id)


@player_action("alliance:delete", ActionKind.EDIT_RECORD)
async def alliance_delete(scope: PlayerScope, command: AllianceTarget) -> Effect:
    await control.delete_record(await scope.context("alliance_delete"), "alliance", (command.giver_id, command.taker_id))
    return Effect("The marriage alliance is struck from the record.", command.taker_id)


@player_action("reproduction:set", ActionKind.EDIT_RECORD)
async def reproduction_set(scope: PlayerScope, command: ReproductionDraft) -> Effect:
    values = {
        "system": command.system.value,
        "change_age": command.change_age,
        "breeder_pct": command.breeder_pct,
        "soldier_pct": command.soldier_pct,
        "worker_pct": command.worker_pct,
    }
    await control.set_reproduction(await scope.context("reproduction_set"), command.people_id, values)
    return Effect("How they bear their young is set.", command.people_id)


@player_action("reproduction:edit", ActionKind.EDIT_RECORD)
async def reproduction_edit(scope: PlayerScope, command: PeopleEdit) -> Effect:
    await control.edit_record(await scope.context("reproduction_edit"), "reproduction", command.people_id, command.values, command.release)
    return Effect("How they bear their young is set so.", command.people_id)


@player_action("reproduction:delete", ActionKind.EDIT_RECORD)
async def reproduction_delete(scope: PlayerScope, command: PeopleTarget) -> Effect:
    await control.delete_record(await scope.context("reproduction_delete"), "reproduction", command.people_id)
    return Effect("How they bear their young will be read anew from their bodies.", command.people_id)


@player_action("caste:set", ActionKind.EDIT_RECORD)
async def caste_set(scope: PlayerScope, command: CasteDraft) -> Effect:
    await control.set_caste(await scope.context("caste_set"), command.mortal_id, command.caste)
    return Effect(f"Their caste is {command.caste.value}.", command.mortal_id)


@player_action("caste:edit", ActionKind.EDIT_RECORD)
async def caste_edit(scope: PlayerScope, command: MortalEdit) -> Effect:
    await control.edit_record(await scope.context("caste_edit"), "caste", command.mortal_id, command.values, command.release)
    return Effect("Their caste is set so.", command.mortal_id)


@player_action("caste:delete", ActionKind.EDIT_RECORD)
async def caste_delete(scope: PlayerScope, command: MortalTarget) -> Effect:
    await control.delete_record(await scope.context("caste_delete"), "caste", command.mortal_id)
    return Effect("Their caste is struck from the record.", command.mortal_id)


@player_action("camp:set", ActionKind.EDIT_RECORD)
async def camp_set(scope: PlayerScope, command: CampDraft) -> Effect:
    await control.set_camp(await scope.context("camp_set"), command.town_id, {"mode": command.mode.value, "herd": command.herd})
    return Effect("The camp follows its pastures.", command.town_id)


@player_action("camp:edit", ActionKind.EDIT_RECORD)
async def camp_edit(scope: PlayerScope, command: TownEdit) -> Effect:
    await control.edit_record(await scope.context("camp_edit"), "camp", command.town_id, command.values, command.release)
    return Effect("The camp is set so.", command.town_id)


@player_action("camp:route", ActionKind.EDIT_RECORD)
async def camp_route(scope: PlayerScope, command: CampRoute) -> Effect:
    row = await control.route_camp(await scope.context("camp_route"), command.town_id, command.regions)
    return Effect(f"The camp now follows {several(len(row.circuit), 'pasture', 'pastures')}.", command.town_id)


@player_action("camp:move", ActionKind.EDIT_RECORD)
async def camp_move(scope: PlayerScope, command: TownTarget) -> Effect:
    row = await control.move_camp(await scope.context("camp_move"), command.town_id)
    return Effect("The camp moves on to its next pasture.", command.town_id, values={"season_index": row.season_index})


@player_action("camp:delete", ActionKind.EDIT_RECORD)
async def camp_delete(scope: PlayerScope, command: TownTarget) -> Effect:
    await control.delete_record(await scope.context("camp_delete"), "camp", command.town_id)
    return Effect("The camp is struck; the settlement stays where it stands.", command.town_id)


@player_action("confederation:create", ActionKind.EDIT_RECORD)
async def confederation_create(scope: PlayerScope, command: ConfederationDraft) -> Effect:
    row = await control.new_confederation(await scope.context("confederation_create"), command.name, command.leader_id, command.members)
    return Effect(f"{row.name} is formed.", command.leader_id, values={"confederation_id": row.id})


@player_action("confederation:edit", ActionKind.EDIT_RECORD)
async def confederation_edit(scope: PlayerScope, command: ConfederationEdit) -> Effect:
    await control.edit_record(await scope.context("confederation_edit"), "confederation", command.confederation_id, command.values, command.release)
    return Effect("The confederation is set so.")


@player_action("confederation:members", ActionKind.EDIT_RECORD)
async def confederation_members(scope: PlayerScope, command: ConfederationMembers) -> Effect:
    row = await control.join_confederation(await scope.context("confederation_members"), command.confederation_id, command.members)
    return Effect(f"{row.name} now joins {several(len(row.members), 'camp', 'camps')}.")


@player_action("confederation:dissolve", ActionKind.EDIT_RECORD)
async def confederation_dissolve(scope: PlayerScope, command: ConfederationTarget) -> Effect:
    row = await control.dissolve_confederation(await scope.context("confederation_dissolve"), command.confederation_id)
    return Effect(f"{row.name} breaks apart.")


@player_action("confederation:delete", ActionKind.EDIT_RECORD)
async def confederation_delete(scope: PlayerScope, command: ConfederationTarget) -> Effect:
    await control.delete_record(await scope.context("confederation_delete"), "confederation", command.confederation_id)
    return Effect("The confederation is struck from the record.")


@player_action("legacy:set", ActionKind.EDIT_RECORD)
async def legacy_set(scope: PlayerScope, command: LegacyDraft) -> Effect:
    await control.set_legacy(await scope.context("legacy_set"), command.people_id, command.kind, command.key, command.predecessor_id)
    return Effect("The legacy is kept.", command.people_id)


@player_action("legacy:edit", ActionKind.EDIT_RECORD)
async def legacy_edit(scope: PlayerScope, command: LegacyEdit) -> Effect:
    await control.edit_record(await scope.context("legacy_edit"), "legacy", (command.people_id, command.kind, command.key), command.values, command.release)
    return Effect("The legacy is set so.", command.people_id)


@player_action("legacy:delete", ActionKind.EDIT_RECORD)
async def legacy_delete(scope: PlayerScope, command: LegacyTarget) -> Effect:
    await control.delete_record(await scope.context("legacy_delete"), "legacy", (command.people_id, command.kind, command.key))
    return Effect("The legacy is struck from the record.", command.people_id)


@player_action("indenture:create", ActionKind.EDIT_RECORD)
async def indenture_create(scope: PlayerScope, command: IndentureDraft) -> Effect:
    row = await control.new_indenture(
        await scope.context("indenture_create"),
        command.community_id,
        command.regime,
        count=command.count,
        term_epochs=command.term_epochs,
        debt=command.debt,
        exploitation=command.exploitation,
        employer_id=command.employer_id,
        origin_id=command.origin_id,
    )
    return Effect(f"{several(row.count, 'is', 'are')} bound in labour.", command.community_id, values={"indenture_id": row.id})


@player_action("indenture:edit", ActionKind.EDIT_RECORD)
async def indenture_edit(scope: PlayerScope, command: IndentureEdit) -> Effect:
    row = await control.edit_record(await scope.context("indenture_edit"), "indenture", command.indenture_id, command.values, command.release)
    return Effect("The bond of labour is set so.", getattr(row, "community_entity_id", None))


@player_action("indenture:release", ActionKind.EDIT_RECORD)
async def indenture_release(scope: PlayerScope, command: IndentureTarget) -> Effect:
    community = await control.release_indenture(await scope.context("indenture_release"), command.indenture_id)
    return Effect("The bound labourers go free.", community)


@player_action("indenture:delete", ActionKind.EDIT_RECORD)
async def indenture_delete(scope: PlayerScope, command: IndentureTarget) -> Effect:
    await control.delete_record(await scope.context("indenture_delete"), "indenture", command.indenture_id)
    return Effect("The bond of labour is struck from the record.")


@player_action("slave_market:set", ActionKind.EDIT_RECORD)
async def slave_market_set(scope: PlayerScope, command: MarketDraft) -> Effect:
    await control.set_market(await scope.context("slave_market_set"), command.town_id, {"price": command.price, "open": command.open})
    return Effect("The market in bound folk is set.", command.town_id)


@player_action("slave_market:edit", ActionKind.EDIT_RECORD)
async def slave_market_edit(scope: PlayerScope, command: TownEdit) -> Effect:
    await control.edit_record(await scope.context("slave_market_edit"), "slave_market", command.town_id, command.values, command.release)
    return Effect("The market in bound folk is set so.", command.town_id)


@player_action("slave_market:delete", ActionKind.EDIT_RECORD)
async def slave_market_delete(scope: PlayerScope, command: TownTarget) -> Effect:
    await control.delete_record(await scope.context("slave_market_delete"), "slave_market", command.town_id)
    return Effect("The market in bound folk is closed.", command.town_id)


@player_action("manumission:free", ActionKind.EDIT_RECORD)
async def manumission_free(scope: PlayerScope, command: FreeDraft) -> Effect:
    row = await control.free_bound(await scope.context("manumission_free"), command.community_id, command.share_pct, command.path)
    freed = row.count if row is not None else 0
    return Effect(f"{freed} of the bound go free.", command.community_id, values={"freed": freed})


@player_action("manumission:edit", ActionKind.EDIT_RECORD)
async def manumission_edit(scope: PlayerScope, command: ManumissionEdit) -> Effect:
    row = await control.edit_record(await scope.context("manumission_edit"), "manumission", command.manumission_id, command.values, command.release)
    return Effect("The freeing is set so.", getattr(row, "community_entity_id", None))


@player_action("manumission:delete", ActionKind.EDIT_RECORD)
async def manumission_delete(scope: PlayerScope, command: ManumissionTarget) -> Effect:
    await control.delete_record(await scope.context("manumission_delete"), "manumission", command.manumission_id)
    return Effect("The freeing is struck from the record.")
