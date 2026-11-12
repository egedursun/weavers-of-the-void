from pydantic import Field

from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.regime import ClientRole, CredentialKind, LeadershipMode, SegmentLevel, SelectorateKind
from aerona.engine.regime import control
from aerona.services.player.cosmography import Edited
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

SPAN = 100
MANY = 1_000_000_000
NAME = 200


class RegimeDraft(Command):
    polity_id: int
    selectorate: SelectorateKind = SelectorateKind.NOBLES
    public_share: int = Field(default=50, ge=0, le=SPAN)
    traditional: int = Field(default=40, ge=0, le=SPAN)
    charismatic: int = Field(default=20, ge=0, le=SPAN)
    rational: int = Field(default=10, ge=0, le=SPAN)
    leadership: LeadershipMode = LeadershipMode.STATE


class PolityTarget(Command):
    polity_id: int


class RegimeEdit(Edited):
    polity_id: int


class MemberDraft(Command):
    polity_id: int
    mortal_id: int
    reward: int = Field(default=20, ge=0, le=SPAN)
    loyalty: int = Field(default=60, ge=0, le=SPAN)


class MemberTarget(Command):
    polity_id: int
    mortal_id: int


class MemberEdit(Edited):
    polity_id: int
    mortal_id: int


class TieDraft(Command):
    patron_id: int
    client_id: int
    role: ClientRole = ClientRole.RETAINER
    strength: int = Field(default=40, ge=0, le=SPAN)


class TieTarget(Command):
    tie_id: int


class TieEdit(Edited):
    tie_id: int


class SaleDraft(Command):
    office_id: int
    buyer_id: int
    price: int = Field(default=300, ge=0, le=MANY)


class SinecureDraft(Command):
    office_id: int
    holder_id: int


class OfficeTarget(Command):
    office_id: int


class OfficeEdit(Edited):
    office_id: int


class BaseDraft(Command):
    mortal_id: int
    polity_id: int
    threat: int = Field(default=0, ge=0, le=SPAN)


class MortalTarget(Command):
    mortal_id: int


class MortalEdit(Edited):
    mortal_id: int


class LineageDraft(Command):
    house_id: int
    level: SegmentLevel = SegmentLevel.LINEAGE
    tribe_id: int | None = None


class HouseTarget(Command):
    house_id: int


class HouseEdit(Edited):
    house_id: int


class BreedingDraft(Command):
    holder_id: int
    house_id: int
    name: str = Field(min_length=1, max_length=NAME)
    locus: str | None = Field(default=None, max_length=NAME)
    allele: str | None = Field(default=None, max_length=NAME)
    claim_polity_id: int | None = None
    target_share: int = Field(default=60, ge=1, le=SPAN)
    steps: int = Field(default=10, ge=1, le=10_000)


class PlanTarget(Command):
    plan_id: int


class PlanEdit(Edited):
    plan_id: int


class ExamDraft(Command):
    polity_id: int
    interval: int = Field(default=2, ge=1, le=SPAN)
    quota: int = Field(default=20, ge=0, le=MANY)
    pass_mark: int = Field(default=50, ge=0, le=SPAN)


class SittingTarget(Command):
    sitting_id: int


class SittingEdit(Edited):
    sitting_id: int


class CredentialDraft(Command):
    mortal_id: int
    kind: CredentialKind = CredentialKind.MASTER
    granter_id: int | None = None
    skill: SkillKind | None = None


class CredentialTarget(Command):
    credential_id: int


class CredentialEdit(Edited):
    credential_id: int


class FreedomDraft(Command):
    structure_id: int
    level: int = Field(default=50, ge=0, le=SPAN)


class StructureTarget(Command):
    structure_id: int


class StructureEdit(Edited):
    structure_id: int


class SchoolDraft(Command):
    founder_id: int
    name: str = Field(min_length=1, max_length=NAME)
    doctrine_id: int | None = None


class SchoolTarget(Command):
    school_id: int


class SchoolEdit(Edited):
    school_id: int


class DiscipleDraft(Command):
    school_id: int
    mortal_id: int
    master_id: int | None = None


class DiscipleTarget(Command):
    school_id: int
    mortal_id: int


class DiscipleEdit(Edited):
    school_id: int
    mortal_id: int


@player_action("regime:set", ActionKind.EDIT_RECORD)
async def regime_set(scope: PlayerScope, command: RegimeDraft) -> Effect:
    values = {
        "selectorate": command.selectorate.value,
        "public_share": command.public_share,
        "traditional": command.traditional,
        "charismatic": command.charismatic,
        "rational": command.rational,
        "leadership": command.leadership.value,
    }
    await control.set_regime(await scope.context("regime_set"), command.polity_id, values)
    return Effect("The realm's rule is set.", command.polity_id)


@player_action("regime:edit", ActionKind.EDIT_RECORD)
async def regime_edit(scope: PlayerScope, command: RegimeEdit) -> Effect:
    await control.edit_record(await scope.context("regime_edit"), "regime", command.polity_id, command.values, command.release)
    return Effect("The realm's rule is set so.", command.polity_id)


@player_action("regime:delete", ActionKind.EDIT_RECORD)
async def regime_delete(scope: PlayerScope, command: PolityTarget) -> Effect:
    await control.delete_record(await scope.context("regime_delete"), "regime", command.polity_id)
    return Effect("The realm's rule will be read anew.", command.polity_id)


@player_action("coalition:enrol", ActionKind.EDIT_RECORD)
async def coalition_enrol(scope: PlayerScope, command: MemberDraft) -> Effect:
    values = {"reward": command.reward, "loyalty": command.loyalty}
    await control.enrol(await scope.context("coalition_enrol"), command.polity_id, command.mortal_id, values)
    return Effect("They join the ruling circle.", command.polity_id)


@player_action("coalition:edit", ActionKind.EDIT_RECORD)
async def coalition_edit(scope: PlayerScope, command: MemberEdit) -> Effect:
    key = (command.polity_id, command.mortal_id)
    await control.edit_record(await scope.context("coalition_edit"), "coalition_member", key, command.values, command.release)
    return Effect("The member of the ruling circle is set so.", command.polity_id)


@player_action("coalition:purge", ActionKind.EDIT_RECORD)
async def coalition_purge(scope: PlayerScope, command: MemberTarget) -> Effect:
    await control.purge(await scope.context("coalition_purge"), command.polity_id, command.mortal_id)
    return Effect("They are cast out of the ruling circle and their seats.", command.polity_id)


@player_action("coalition:delete", ActionKind.EDIT_RECORD)
async def coalition_delete(scope: PlayerScope, command: MemberTarget) -> Effect:
    await control.delete_record(await scope.context("coalition_delete"), "coalition_member", (command.polity_id, command.mortal_id))
    return Effect("They are struck from the ruling circle.", command.polity_id)


@player_action("patronage:bind", ActionKind.EDIT_RECORD)
async def patronage_bind(scope: PlayerScope, command: TieDraft) -> Effect:
    row = await control.bind_client(await scope.context("patronage_bind"), command.patron_id, command.client_id, command.role, command.strength)
    return Effect("A patron takes a client.", command.client_id, values={"tie_id": row.id})


@player_action("patronage:edit", ActionKind.EDIT_RECORD)
async def patronage_edit(scope: PlayerScope, command: TieEdit) -> Effect:
    row = await control.edit_record(await scope.context("patronage_edit"), "patronage", command.tie_id, command.values, command.release)
    return Effect("The tie of patronage is set so.", getattr(row, "client_entity_id", None))


@player_action("patronage:delete", ActionKind.EDIT_RECORD)
async def patronage_delete(scope: PlayerScope, command: TieTarget) -> Effect:
    await control.delete_record(await scope.context("patronage_delete"), "patronage", command.tie_id)
    return Effect("The tie of patronage is cut.")


@player_action("venal_office:sell", ActionKind.EDIT_RECORD)
async def venal_office_sell(scope: PlayerScope, command: SaleDraft) -> Effect:
    await control.sell(await scope.context("venal_office_sell"), command.office_id, command.buyer_id, command.price)
    return Effect("The seat is sold.", command.buyer_id)


@player_action("venal_office:sinecure", ActionKind.EDIT_RECORD)
async def venal_office_sinecure(scope: PlayerScope, command: SinecureDraft) -> Effect:
    await control.sinecure(await scope.context("venal_office_sinecure"), command.office_id, command.holder_id)
    return Effect("The seat becomes a sinecure.", command.holder_id)


@player_action("venal_office:edit", ActionKind.EDIT_RECORD)
async def venal_office_edit(scope: PlayerScope, command: OfficeEdit) -> Effect:
    await control.edit_record(await scope.context("venal_office_edit"), "venal_office", command.office_id, command.values, command.release)
    return Effect("The bought seat is set so.")


@player_action("venal_office:delete", ActionKind.EDIT_RECORD)
async def venal_office_delete(scope: PlayerScope, command: OfficeTarget) -> Effect:
    await control.delete_record(await scope.context("venal_office_delete"), "venal_office", command.office_id)
    return Effect("The seat is no longer held by purchase.")


@player_action("power_base:measure", ActionKind.EDIT_RECORD)
async def power_base_measure(scope: PlayerScope, command: PolityTarget) -> Effect:
    await control.weigh_base(await scope.context("power_base_measure"), command.polity_id)
    return Effect("The power of the realm's great subjects is weighed.", command.polity_id)


@player_action("power_base:set", ActionKind.EDIT_RECORD)
async def power_base_set(scope: PlayerScope, command: BaseDraft) -> Effect:
    await control.set_base(await scope.context("power_base_set"), command.mortal_id, command.polity_id, {"threat": command.threat})
    return Effect("The power base is set.", command.mortal_id)


@player_action("power_base:edit", ActionKind.EDIT_RECORD)
async def power_base_edit(scope: PlayerScope, command: MortalEdit) -> Effect:
    await control.edit_record(await scope.context("power_base_edit"), "power_base", command.mortal_id, command.values, command.release)
    return Effect("The power base is set so.", command.mortal_id)


@player_action("power_base:delete", ActionKind.EDIT_RECORD)
async def power_base_delete(scope: PlayerScope, command: MortalTarget) -> Effect:
    await control.delete_record(await scope.context("power_base_delete"), "power_base", command.mortal_id)
    return Effect("The power base will be weighed anew.", command.mortal_id)


@player_action("kin_segment:set", ActionKind.EDIT_RECORD)
async def kin_segment_set(scope: PlayerScope, command: LineageDraft) -> Effect:
    await control.set_segment(await scope.context("kin_segment_set"), command.house_id, command.level, command.tribe_id)
    return Effect("The house takes its place among the lines of its tribe.", command.house_id)


@player_action("kin_segment:edit", ActionKind.EDIT_RECORD)
async def kin_segment_edit(scope: PlayerScope, command: HouseEdit) -> Effect:
    await control.edit_record(await scope.context("kin_segment_edit"), "lineage", command.house_id, command.values, command.release)
    return Effect("The lineage is set so.", command.house_id)


@player_action("kin_segment:delete", ActionKind.EDIT_RECORD)
async def kin_segment_delete(scope: PlayerScope, command: HouseTarget) -> Effect:
    await control.delete_record(await scope.context("kin_segment_delete"), "lineage", command.house_id)
    return Effect("The lineage will be read anew.", command.house_id)


@player_action("breeding:create", ActionKind.EDIT_RECORD)
async def breeding_create(scope: PlayerScope, command: BreedingDraft) -> Effect:
    row = await control.new_breeding(
        await scope.context("breeding_create"),
        command.holder_id,
        command.house_id,
        command.name,
        locus=command.locus,
        allele=command.allele,
        claim_polity_id=command.claim_polity_id,
        target_share=command.target_share,
        steps=command.steps,
    )
    return Effect("The long design begins to steer the house's marriages.", command.house_id, values={"plan_id": row.plan_id})


@player_action("breeding:edit", ActionKind.EDIT_RECORD)
async def breeding_edit(scope: PlayerScope, command: PlanEdit) -> Effect:
    row = await control.edit_record(await scope.context("breeding_edit"), "breeding", command.plan_id, command.values, command.release)
    return Effect("The breeding plan is set so.", getattr(row, "house_entity_id", None))


@player_action("breeding:delete", ActionKind.EDIT_RECORD)
async def breeding_delete(scope: PlayerScope, command: PlanTarget) -> Effect:
    await control.delete_record(await scope.context("breeding_delete"), "breeding", command.plan_id)
    return Effect("The marriages of the house are left to themselves again.")


@player_action("examination:set", ActionKind.EDIT_RECORD)
async def examination_set(scope: PlayerScope, command: ExamDraft) -> Effect:
    values = {"interval": command.interval, "quota": command.quota, "pass_mark": command.pass_mark}
    await control.set_examinations(await scope.context("examination_set"), command.polity_id, values)
    return Effect("The realm chooses its officials by examination.", command.polity_id)


@player_action("examination:sit", ActionKind.EDIT_RECORD)
async def examination_sit(scope: PlayerScope, command: PolityTarget) -> Effect:
    row = await control.sit_now(await scope.context("examination_sit"), command.polity_id)
    return Effect(f"{row.passed} of {row.candidates} candidates passed.", command.polity_id, values={"sitting_id": row.id})


@player_action("examination:edit", ActionKind.EDIT_RECORD)
async def examination_edit(scope: PlayerScope, command: RegimeEdit) -> Effect:
    await control.edit_record(await scope.context("examination_edit"), "examination", command.polity_id, command.values, command.release)
    return Effect("The examinations are set so.", command.polity_id)


@player_action("examination:delete", ActionKind.EDIT_RECORD)
async def examination_delete(scope: PlayerScope, command: PolityTarget) -> Effect:
    await control.delete_record(await scope.context("examination_delete"), "examination", command.polity_id)
    return Effect("The realm no longer examines its officials.", command.polity_id)


@player_action("exam_sitting:edit", ActionKind.EDIT_RECORD)
async def exam_sitting_edit(scope: PlayerScope, command: SittingEdit) -> Effect:
    row = await control.edit_record(await scope.context("exam_sitting_edit"), "exam_sitting", command.sitting_id, command.values, command.release)
    return Effect("The sitting is set so.", getattr(row, "polity_entity_id", None))


@player_action("exam_sitting:delete", ActionKind.EDIT_RECORD)
async def exam_sitting_delete(scope: PlayerScope, command: SittingTarget) -> Effect:
    await control.delete_record(await scope.context("exam_sitting_delete"), "exam_sitting", command.sitting_id)
    return Effect("The sitting is struck from the record.")


@player_action("credential:grant", ActionKind.EDIT_RECORD)
async def credential_grant(scope: PlayerScope, command: CredentialDraft) -> Effect:
    row = await control.confer(await scope.context("credential_grant"), command.mortal_id, command.kind, command.granter_id, command.skill)
    return Effect("The credential is granted.", command.mortal_id, values={"credential_id": row.id})


@player_action("credential:edit", ActionKind.EDIT_RECORD)
async def credential_edit(scope: PlayerScope, command: CredentialEdit) -> Effect:
    row = await control.edit_record(await scope.context("credential_edit"), "credential", command.credential_id, command.values, command.release)
    return Effect("The credential is set so.", getattr(row, "mortal_entity_id", None))


@player_action("credential:delete", ActionKind.EDIT_RECORD)
async def credential_delete(scope: PlayerScope, command: CredentialTarget) -> Effect:
    await control.delete_record(await scope.context("credential_delete"), "credential", command.credential_id)
    return Effect("The credential is revoked.")


@player_action("academic_freedom:set", ActionKind.EDIT_RECORD)
async def academic_freedom_set(scope: PlayerScope, command: FreedomDraft) -> Effect:
    await control.set_freedom(await scope.context("academic_freedom_set"), command.structure_id, {"level": command.level})
    return Effect("The freedom of the house of learning is set.", command.structure_id)


@player_action("academic_freedom:edit", ActionKind.EDIT_RECORD)
async def academic_freedom_edit(scope: PlayerScope, command: StructureEdit) -> Effect:
    await control.edit_record(await scope.context("academic_freedom_edit"), "academic_freedom", command.structure_id, command.values, command.release)
    return Effect("The freedom of learning is set so.", command.structure_id)


@player_action("academic_freedom:delete", ActionKind.EDIT_RECORD)
async def academic_freedom_delete(scope: PlayerScope, command: StructureTarget) -> Effect:
    await control.delete_record(await scope.context("academic_freedom_delete"), "academic_freedom", command.structure_id)
    return Effect("The freedom of learning will be read anew.", command.structure_id)


@player_action("school:found", ActionKind.EDIT_RECORD)
async def school_found(scope: PlayerScope, command: SchoolDraft) -> Effect:
    row = await control.found_school(await scope.context("school_found"), command.founder_id, command.name, command.doctrine_id)
    return Effect(f"The {row.name} is founded.", command.founder_id, values={"school_id": row.id})


@player_action("school:edit", ActionKind.EDIT_RECORD)
async def school_edit(scope: PlayerScope, command: SchoolEdit) -> Effect:
    row = await control.edit_record(await scope.context("school_edit"), "school", command.school_id, command.values, command.release)
    return Effect("The school is set so.", getattr(row, "founder_entity_id", None))


@player_action("school:delete", ActionKind.EDIT_RECORD)
async def school_delete(scope: PlayerScope, command: SchoolTarget) -> Effect:
    await control.delete_record(await scope.context("school_delete"), "school", command.school_id)
    return Effect("The school is dissolved.")


@player_action("disciple:admit", ActionKind.EDIT_RECORD)
async def disciple_admit(scope: PlayerScope, command: DiscipleDraft) -> Effect:
    await control.admit(await scope.context("disciple_admit"), command.school_id, command.mortal_id, command.master_id)
    return Effect("A disciple joins the school.", command.mortal_id)


@player_action("disciple:edit", ActionKind.EDIT_RECORD)
async def disciple_edit(scope: PlayerScope, command: DiscipleEdit) -> Effect:
    key = (command.school_id, command.mortal_id)
    await control.edit_record(await scope.context("disciple_edit"), "disciple", key, command.values, command.release)
    return Effect("The disciple is set so.", command.mortal_id)


@player_action("disciple:delete", ActionKind.EDIT_RECORD)
async def disciple_delete(scope: PlayerScope, command: DiscipleTarget) -> Effect:
    await control.delete_record(await scope.context("disciple_delete"), "disciple", (command.school_id, command.mortal_id))
    return Effect("The disciple leaves the school.", command.mortal_id)
