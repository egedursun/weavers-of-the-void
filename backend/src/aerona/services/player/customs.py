from aerona.core.grammar import several
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.customs import (
    AgeGrade,
    CoopPurpose,
    EvidenceKind,
    Intoxicant,
    IntoxicantUse,
    MarkKind,
    MarkMeaning,
    MemberRight,
    Membership,
    NameForm,
    NamingPattern,
    Naturalisation,
    ReliefKind,
    RevivalAim,
    RevivalGoal,
)
from aerona.domain.enums.mortal import LifeStage
from aerona.domain.enums.society import SocialClass
from aerona.engine.customs import control
from aerona.services.player.cosmography import Edited
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class RightGrant(Command):
    polity_id: int
    category: Membership = Membership.CITIZEN
    right: MemberRight = MemberRight.OFFICE
    granted: bool = True


class RunNow(Command):
    pass


class RevivalDraft(Command):
    people_entity_id: int
    aim: RevivalAim = RevivalAim.RESTORE
    goal: RevivalGoal = RevivalGoal.REVIVE_LANGUAGE


class RevivalTarget(Command):
    record_id: int


class RevivalEdit(Edited):
    record_id: int


class IntoxicantCustomDraft(Command):
    people_id: int
    intoxicant: Intoxicant
    use: IntoxicantUse = IntoxicantUse.FEAST
    acceptance: int = 50


class IntoxicantCustomTarget(Command):
    people_id: int
    intoxicant: Intoxicant


class IntoxicantCustomEdit(Edited):
    people_id: int
    intoxicant: Intoxicant


class MarkCustomDraft(Command):
    people_id: int
    kind: MarkKind
    meaning: MarkMeaning = MarkMeaning.STATUS


class MarkCustomTarget(Command):
    people_id: int
    kind: MarkKind


class MarkCustomEdit(Edited):
    people_id: int
    kind: MarkKind


class BodyMarkDraft(Command):
    holder_node_id: int
    kind: MarkKind = MarkKind.TATTOO
    meaning: MarkMeaning = MarkMeaning.DEED


class BodyMarkTarget(Command):
    record_id: int


class BodyMarkEdit(Edited):
    record_id: int


class TimeBudgetDraft(Command):
    people_id: int
    social_class: SocialClass
    life_stage: LifeStage = LifeStage.ADULT
    work: int = 55
    rest: int = 20
    worship: int = 10
    leisure: int = 10
    travel: int = 3
    service: int = 2
    learning: int = 0
    care: int = 0
    art: int = 0
    housework: int = 0
    sleep: int = 0


class TimeBudgetTarget(Command):
    people_id: int
    social_class: SocialClass
    life_stage: LifeStage = LifeStage.ADULT


class TimeBudgetEdit(Edited):
    people_id: int
    social_class: SocialClass
    life_stage: LifeStage = LifeStage.ADULT


class NamingCustomDraft(Command):
    people_id: int
    pattern: NamingPattern = NamingPattern.GIVEN
    secret_names: bool = False
    taboo_epochs: int = 0


class NamingCustomTarget(Command):
    people_id: int


class NamingCustomEdit(Edited):
    people_id: int


class NameFormDraft(Command):
    holder_id: int
    form: NameForm
    name: str


class NameFormTarget(Command):
    holder_id: int
    form: NameForm


class NameFormEdit(Edited):
    holder_id: int
    form: NameForm


class AgeSetDraft(Command):
    people_entity_id: int
    name: str
    grade: AgeGrade = AgeGrade.YOUTHS


class AgeSetTarget(Command):
    record_id: int


class AgeSetEdit(Edited):
    record_id: int


class AgeSetMemberDraft(Command):
    mortal_id: int
    age_set_id: int


class AgeSetMemberTarget(Command):
    mortal_id: int


class AgeSetMemberEdit(Edited):
    mortal_id: int


class TavernDraft(Command):
    structure_id: int
    keeper_node_id: int | None = None


class TavernTarget(Command):
    structure_id: int


class TavernEdit(Edited):
    structure_id: int


class WelfareHouseDraft(Command):
    structure_id: int
    patron_node_id: int | None = None


class WelfareHouseTarget(Command):
    structure_id: int


class WelfareHouseEdit(Edited):
    structure_id: int


class CommuteDraft(Command):
    settlement_id: int
    distance: int = 10


class CommuteTarget(Command):
    settlement_id: int


class CommuteEdit(Edited):
    settlement_id: int


class CooperativeDraft(Command):
    faction_id: int
    purpose: CoopPurpose = CoopPurpose.MILL


class CooperativeTarget(Command):
    faction_id: int


class CooperativeEdit(Edited):
    faction_id: int


class EvidenceDraft(Command):
    case_id: int
    kind: EvidenceKind = EvidenceKind.TRACE
    points_to_node_id: int | None = None
    reliability: int = 50


class EvidenceTarget(Command):
    record_id: int


class EvidenceEdit(Edited):
    record_id: int


class MembershipCategoryDraft(Command):
    polity_id: int
    category: Membership


class MembershipCategoryTarget(Command):
    polity_id: int
    category: Membership


class MembershipCategoryEdit(Edited):
    polity_id: int
    category: Membership


class MembershipDraft(Command):
    mortal_id: int
    polity_entity_id: int
    category: Membership = Membership.CITIZEN
    path: Naturalisation = Naturalisation.GRANT


class MembershipTarget(Command):
    mortal_id: int


class MembershipEdit(Edited):
    mortal_id: int


class BorderControlDraft(Command):
    polity_id: int
    fee: int = 50
    delay: int = 1
    enforcement: int = 50


class BorderControlTarget(Command):
    polity_id: int


class BorderControlEdit(Edited):
    polity_id: int


class PoorReliefDraft(Command):
    polity_id: int
    kind: ReliefKind = ReliefKind.ALMS
    budget: int = 50
    reach: int = 40


class PoorReliefTarget(Command):
    polity_id: int


class PoorReliefEdit(Edited):
    polity_id: int


class MeasureStandardDraft(Command):
    polity_id: int
    standard: bool = True
    fraud: int = 10


class MeasureStandardTarget(Command):
    polity_id: int


class MeasureStandardEdit(Edited):
    polity_id: int


@player_action("revival:create", ActionKind.EDIT_RECORD)
async def revival_create(scope: PlayerScope, command: RevivalDraft) -> Effect:
    row = await control.set_record(
        await scope.context("revival_create"), "revival", {}, {"people_entity_id": command.people_entity_id, "aim": command.aim, "goal": command.goal}
    )
    return Effect("A movement rises among the people.", values={"record_id": getattr(row, "id", 0)})


@player_action("revival:edit", ActionKind.EDIT_RECORD)
async def revival_edit(scope: PlayerScope, command: RevivalEdit) -> Effect:
    await control.edit_record(await scope.context("revival_edit"), "revival", command.record_id, command.values, command.release)
    return Effect("The movement is set so.")


@player_action("revival:delete", ActionKind.EDIT_RECORD)
async def revival_delete(scope: PlayerScope, command: RevivalTarget) -> Effect:
    await control.delete_record(await scope.context("revival_delete"), "revival", command.record_id)
    return Effect("The movement is struck from the record.")


@player_action("intoxicant_custom:set", ActionKind.EDIT_RECORD)
async def intoxicant_custom_set(scope: PlayerScope, command: IntoxicantCustomDraft) -> Effect:
    row = await control.set_record(
        await scope.context("intoxicant_custom_set"),
        "intoxicant_custom",
        {"people_entity_id": command.people_id, "intoxicant": command.intoxicant},
        {"use": command.use, "acceptance": command.acceptance},
    )
    return Effect("The people take it so.", values={"record_id": getattr(row, "id", 0)})


@player_action("intoxicant_custom:edit", ActionKind.EDIT_RECORD)
async def intoxicant_custom_edit(scope: PlayerScope, command: IntoxicantCustomEdit) -> Effect:
    await control.edit_record(
        await scope.context("intoxicant_custom_edit"), "intoxicant_custom", (command.people_id, command.intoxicant), command.values, command.release
    )
    return Effect("The custom is set so.")


@player_action("intoxicant_custom:delete", ActionKind.EDIT_RECORD)
async def intoxicant_custom_delete(scope: PlayerScope, command: IntoxicantCustomTarget) -> Effect:
    await control.delete_record(await scope.context("intoxicant_custom_delete"), "intoxicant_custom", (command.people_id, command.intoxicant))
    return Effect("The custom is struck.")


@player_action("mark_custom:set", ActionKind.EDIT_RECORD)
async def mark_custom_set(scope: PlayerScope, command: MarkCustomDraft) -> Effect:
    row = await control.set_record(
        await scope.context("mark_custom_set"), "mark_custom", {"people_entity_id": command.people_id, "kind": command.kind}, {"meaning": command.meaning}
    )
    return Effect("The people read the mark so.", values={"record_id": getattr(row, "id", 0)})


@player_action("mark_custom:edit", ActionKind.EDIT_RECORD)
async def mark_custom_edit(scope: PlayerScope, command: MarkCustomEdit) -> Effect:
    await control.edit_record(await scope.context("mark_custom_edit"), "mark_custom", (command.people_id, command.kind), command.values, command.release)
    return Effect("The mark custom is set so.")


@player_action("mark_custom:delete", ActionKind.EDIT_RECORD)
async def mark_custom_delete(scope: PlayerScope, command: MarkCustomTarget) -> Effect:
    await control.delete_record(await scope.context("mark_custom_delete"), "mark_custom", (command.people_id, command.kind))
    return Effect("The mark custom is struck.")


@player_action("body_mark:create", ActionKind.EDIT_RECORD)
async def body_mark_create(scope: PlayerScope, command: BodyMarkDraft) -> Effect:
    row = await control.set_record(
        await scope.context("body_mark_create"), "body_mark", {}, {"holder_node_id": command.holder_node_id, "kind": command.kind, "meaning": command.meaning}
    )
    return Effect("The body is marked.", values={"record_id": getattr(row, "id", 0)})


@player_action("body_mark:edit", ActionKind.EDIT_RECORD)
async def body_mark_edit(scope: PlayerScope, command: BodyMarkEdit) -> Effect:
    await control.edit_record(await scope.context("body_mark_edit"), "body_mark", command.record_id, command.values, command.release)
    return Effect("The mark is set so.")


@player_action("body_mark:delete", ActionKind.EDIT_RECORD)
async def body_mark_delete(scope: PlayerScope, command: BodyMarkTarget) -> Effect:
    await control.delete_record(await scope.context("body_mark_delete"), "body_mark", command.record_id)
    return Effect("The mark is taken away.")


@player_action("time_budget:set", ActionKind.EDIT_RECORD)
async def time_budget_set(scope: PlayerScope, command: TimeBudgetDraft) -> Effect:
    row = await control.set_record(
        await scope.context("time_budget_set"),
        "time_budget",
        {"people_entity_id": command.people_id, "social_class": command.social_class, "life_stage": command.life_stage},
        {
            "work": command.work,
            "rest": command.rest,
            "worship": command.worship,
            "leisure": command.leisure,
            "travel": command.travel,
            "service": command.service,
            "learning": command.learning,
            "care": command.care,
            "art": command.art,
            "housework": command.housework,
            "sleep": command.sleep,
        },
    )
    return Effect("The year of the class is set.", values={"record_id": getattr(row, "id", 0)})


@player_action("time_budget:edit", ActionKind.EDIT_RECORD)
async def time_budget_edit(scope: PlayerScope, command: TimeBudgetEdit) -> Effect:
    await control.edit_record(
        await scope.context("time_budget_edit"), "time_budget", (command.people_id, command.social_class, command.life_stage), command.values, command.release
    )
    return Effect("The time budget is set so.")


@player_action("time_budget:delete", ActionKind.EDIT_RECORD)
async def time_budget_delete(scope: PlayerScope, command: TimeBudgetTarget) -> Effect:
    await control.delete_record(await scope.context("time_budget_delete"), "time_budget", (command.people_id, command.social_class, command.life_stage))
    return Effect("The time budget is struck.")


@player_action("naming_custom:set", ActionKind.EDIT_RECORD)
async def naming_custom_set(scope: PlayerScope, command: NamingCustomDraft) -> Effect:
    row = await control.set_record(
        await scope.context("naming_custom_set"),
        "naming_custom",
        {"people_entity_id": command.people_id},
        {"pattern": command.pattern, "secret_names": command.secret_names, "taboo_epochs": command.taboo_epochs},
    )
    return Effect("The people name so.", values={"record_id": getattr(row, "id", 0)})


@player_action("naming_custom:edit", ActionKind.EDIT_RECORD)
async def naming_custom_edit(scope: PlayerScope, command: NamingCustomEdit) -> Effect:
    await control.edit_record(await scope.context("naming_custom_edit"), "naming_custom", command.people_id, command.values, command.release)
    return Effect("The naming custom is set so.")


@player_action("naming_custom:delete", ActionKind.EDIT_RECORD)
async def naming_custom_delete(scope: PlayerScope, command: NamingCustomTarget) -> Effect:
    await control.delete_record(await scope.context("naming_custom_delete"), "naming_custom", command.people_id)
    return Effect("The naming custom is struck.")


@player_action("name_form:set", ActionKind.EDIT_RECORD)
async def name_form_set(scope: PlayerScope, command: NameFormDraft) -> Effect:
    row = await control.set_record(
        await scope.context("name_form_set"), "name_form", {"holder_node_id": command.holder_id, "form": command.form}, {"name": command.name}
    )
    return Effect("The name is given.", values={"record_id": getattr(row, "id", 0)})


@player_action("name_form:edit", ActionKind.EDIT_RECORD)
async def name_form_edit(scope: PlayerScope, command: NameFormEdit) -> Effect:
    await control.edit_record(await scope.context("name_form_edit"), "name_form", (command.holder_id, command.form), command.values, command.release)
    return Effect("The name is set so.")


@player_action("name_form:delete", ActionKind.EDIT_RECORD)
async def name_form_delete(scope: PlayerScope, command: NameFormTarget) -> Effect:
    await control.delete_record(await scope.context("name_form_delete"), "name_form", (command.holder_id, command.form))
    return Effect("The name is struck.")


@player_action("age_set:create", ActionKind.EDIT_RECORD)
async def age_set_create(scope: PlayerScope, command: AgeSetDraft) -> Effect:
    row = await control.set_record(
        await scope.context("age_set_create"), "age_set", {}, {"people_entity_id": command.people_entity_id, "name": command.name, "grade": command.grade}
    )
    return Effect("An age-set is opened.", values={"record_id": getattr(row, "id", 0)})


@player_action("age_set:edit", ActionKind.EDIT_RECORD)
async def age_set_edit(scope: PlayerScope, command: AgeSetEdit) -> Effect:
    await control.edit_record(await scope.context("age_set_edit"), "age_set", command.record_id, command.values, command.release)
    return Effect("The age-set is set so.")


@player_action("age_set:delete", ActionKind.EDIT_RECORD)
async def age_set_delete(scope: PlayerScope, command: AgeSetTarget) -> Effect:
    await control.delete_record(await scope.context("age_set_delete"), "age_set", command.record_id)
    return Effect("The age-set is struck.")


@player_action("age_set_member:set", ActionKind.EDIT_RECORD)
async def age_set_member_set(scope: PlayerScope, command: AgeSetMemberDraft) -> Effect:
    row = await control.set_record(
        await scope.context("age_set_member_set"), "age_set_member", {"mortal_entity_id": command.mortal_id}, {"age_set_id": command.age_set_id}
    )
    return Effect("The mortal joins the age-set.", values={"record_id": getattr(row, "id", 0)})


@player_action("age_set_member:edit", ActionKind.EDIT_RECORD)
async def age_set_member_edit(scope: PlayerScope, command: AgeSetMemberEdit) -> Effect:
    await control.edit_record(await scope.context("age_set_member_edit"), "age_set_member", command.mortal_id, command.values, command.release)
    return Effect("The membership is set so.")


@player_action("age_set_member:delete", ActionKind.EDIT_RECORD)
async def age_set_member_delete(scope: PlayerScope, command: AgeSetMemberTarget) -> Effect:
    await control.delete_record(await scope.context("age_set_member_delete"), "age_set_member", command.mortal_id)
    return Effect("The mortal leaves the age-set.")


@player_action("tavern:set", ActionKind.EDIT_RECORD)
async def tavern_set(scope: PlayerScope, command: TavernDraft) -> Effect:
    row = await control.set_record(
        await scope.context("tavern_set"), "tavern", {"structure_entity_id": command.structure_id}, {"keeper_node_id": command.keeper_node_id}
    )
    return Effect("The house keeps its tavern.", values={"record_id": getattr(row, "id", 0)})


@player_action("tavern:edit", ActionKind.EDIT_RECORD)
async def tavern_edit(scope: PlayerScope, command: TavernEdit) -> Effect:
    await control.edit_record(await scope.context("tavern_edit"), "tavern", command.structure_id, command.values, command.release)
    return Effect("The tavern is set so.")


@player_action("tavern:delete", ActionKind.EDIT_RECORD)
async def tavern_delete(scope: PlayerScope, command: TavernTarget) -> Effect:
    await control.delete_record(await scope.context("tavern_delete"), "tavern", command.structure_id)
    return Effect("The tavern is struck.")


@player_action("welfare_house:set", ActionKind.EDIT_RECORD)
async def welfare_house_set(scope: PlayerScope, command: WelfareHouseDraft) -> Effect:
    row = await control.set_record(
        await scope.context("welfare_house_set"), "welfare_house", {"structure_entity_id": command.structure_id}, {"patron_node_id": command.patron_node_id}
    )
    return Effect("The house takes in the poor.", values={"record_id": getattr(row, "id", 0)})


@player_action("welfare_house:edit", ActionKind.EDIT_RECORD)
async def welfare_house_edit(scope: PlayerScope, command: WelfareHouseEdit) -> Effect:
    await control.edit_record(await scope.context("welfare_house_edit"), "welfare_house", command.structure_id, command.values, command.release)
    return Effect("The house of welfare is set so.")


@player_action("welfare_house:delete", ActionKind.EDIT_RECORD)
async def welfare_house_delete(scope: PlayerScope, command: WelfareHouseTarget) -> Effect:
    await control.delete_record(await scope.context("welfare_house_delete"), "welfare_house", command.structure_id)
    return Effect("The house of welfare is struck.")


@player_action("commute:set", ActionKind.EDIT_RECORD)
async def commute_set(scope: PlayerScope, command: CommuteDraft) -> Effect:
    row = await control.set_record(
        await scope.context("commute_set"), "commute", {"settlement_entity_id": command.settlement_id}, {"distance": command.distance}
    )
    return Effect("The way to work is set.", values={"record_id": getattr(row, "id", 0)})


@player_action("commute:edit", ActionKind.EDIT_RECORD)
async def commute_edit(scope: PlayerScope, command: CommuteEdit) -> Effect:
    await control.edit_record(await scope.context("commute_edit"), "commute", command.settlement_id, command.values, command.release)
    return Effect("The way to work is set so.")


@player_action("commute:delete", ActionKind.EDIT_RECORD)
async def commute_delete(scope: PlayerScope, command: CommuteTarget) -> Effect:
    await control.delete_record(await scope.context("commute_delete"), "commute", command.settlement_id)
    return Effect("The way to work is forgotten.")


@player_action("cooperative:set", ActionKind.EDIT_RECORD)
async def cooperative_set(scope: PlayerScope, command: CooperativeDraft) -> Effect:
    row = await control.set_record(
        await scope.context("cooperative_set"), "cooperative", {"faction_entity_id": command.faction_id}, {"purpose": command.purpose}
    )
    return Effect("The members pool their means.", values={"record_id": getattr(row, "id", 0)})


@player_action("cooperative:edit", ActionKind.EDIT_RECORD)
async def cooperative_edit(scope: PlayerScope, command: CooperativeEdit) -> Effect:
    await control.edit_record(await scope.context("cooperative_edit"), "cooperative", command.faction_id, command.values, command.release)
    return Effect("The cooperative is set so.")


@player_action("cooperative:delete", ActionKind.EDIT_RECORD)
async def cooperative_delete(scope: PlayerScope, command: CooperativeTarget) -> Effect:
    await control.delete_record(await scope.context("cooperative_delete"), "cooperative", command.faction_id)
    return Effect("The cooperative is undone.")


@player_action("evidence:create", ActionKind.EDIT_RECORD)
async def evidence_create(scope: PlayerScope, command: EvidenceDraft) -> Effect:
    row = await control.set_record(
        await scope.context("evidence_create"),
        "evidence",
        {},
        {"case_id": command.case_id, "kind": command.kind, "points_to_node_id": command.points_to_node_id, "reliability": command.reliability},
    )
    return Effect("The evidence is laid before the court.", values={"record_id": getattr(row, "id", 0)})


@player_action("evidence:edit", ActionKind.EDIT_RECORD)
async def evidence_edit(scope: PlayerScope, command: EvidenceEdit) -> Effect:
    await control.edit_record(await scope.context("evidence_edit"), "evidence", command.record_id, command.values, command.release)
    return Effect("The evidence is set so.")


@player_action("evidence:delete", ActionKind.EDIT_RECORD)
async def evidence_delete(scope: PlayerScope, command: EvidenceTarget) -> Effect:
    await control.delete_record(await scope.context("evidence_delete"), "evidence", command.record_id)
    return Effect("The evidence is struck.")


@player_action("membership_category:set", ActionKind.EDIT_RECORD)
async def membership_category_set(scope: PlayerScope, command: MembershipCategoryDraft) -> Effect:
    row = await control.set_record(
        await scope.context("membership_category_set"), "membership_category", {"polity_entity_id": command.polity_id, "category": command.category}, {}
    )
    return Effect("The realm keeps the category.", values={"record_id": getattr(row, "id", 0)})


@player_action("membership_category:edit", ActionKind.EDIT_RECORD)
async def membership_category_edit(scope: PlayerScope, command: MembershipCategoryEdit) -> Effect:
    await control.edit_category(await scope.context("membership_category_edit"), command.polity_id, command.category, command.values, command.release)
    return Effect("The category is set so.")


@player_action("membership_category:delete", ActionKind.EDIT_RECORD)
async def membership_category_delete(scope: PlayerScope, command: MembershipCategoryTarget) -> Effect:
    await control.delete_record(await scope.context("membership_category_delete"), "membership_category", (command.polity_id, command.category))
    return Effect("The category is struck.")


@player_action("membership:set", ActionKind.EDIT_RECORD)
async def membership_set(scope: PlayerScope, command: MembershipDraft) -> Effect:
    row = await control.set_record(
        await scope.context("membership_set"),
        "membership",
        {"mortal_entity_id": command.mortal_id},
        {"polity_entity_id": command.polity_entity_id, "category": command.category, "path": command.path},
    )
    return Effect("The mortal belongs to the realm so.", values={"record_id": getattr(row, "id", 0)})


@player_action("membership:edit", ActionKind.EDIT_RECORD)
async def membership_edit(scope: PlayerScope, command: MembershipEdit) -> Effect:
    await control.edit_record(await scope.context("membership_edit"), "membership", command.mortal_id, command.values, command.release)
    return Effect("The membership is set so.")


@player_action("membership:delete", ActionKind.EDIT_RECORD)
async def membership_delete(scope: PlayerScope, command: MembershipTarget) -> Effect:
    await control.delete_record(await scope.context("membership_delete"), "membership", command.mortal_id)
    return Effect("The membership is struck.")


@player_action("border_control:set", ActionKind.EDIT_RECORD)
async def border_control_set(scope: PlayerScope, command: BorderControlDraft) -> Effect:
    row = await control.set_record(
        await scope.context("border_control_set"),
        "border_control",
        {"polity_entity_id": command.polity_id},
        {"fee": command.fee, "delay": command.delay, "enforcement": command.enforcement},
    )
    return Effect("The realm guards its border.", values={"record_id": getattr(row, "id", 0)})


@player_action("border_control:edit", ActionKind.EDIT_RECORD)
async def border_control_edit(scope: PlayerScope, command: BorderControlEdit) -> Effect:
    await control.edit_record(await scope.context("border_control_edit"), "border_control", command.polity_id, command.values, command.release)
    return Effect("The border is set so.")


@player_action("border_control:delete", ActionKind.EDIT_RECORD)
async def border_control_delete(scope: PlayerScope, command: BorderControlTarget) -> Effect:
    await control.delete_record(await scope.context("border_control_delete"), "border_control", command.polity_id)
    return Effect("The border is opened.")


@player_action("poor_relief:set", ActionKind.EDIT_RECORD)
async def poor_relief_set(scope: PlayerScope, command: PoorReliefDraft) -> Effect:
    row = await control.set_record(
        await scope.context("poor_relief_set"),
        "poor_relief",
        {"polity_entity_id": command.polity_id},
        {"kind": command.kind, "budget": command.budget, "reach": command.reach},
    )
    return Effect("The realm relieves its poor.", values={"record_id": getattr(row, "id", 0)})


@player_action("poor_relief:edit", ActionKind.EDIT_RECORD)
async def poor_relief_edit(scope: PlayerScope, command: PoorReliefEdit) -> Effect:
    await control.edit_record(await scope.context("poor_relief_edit"), "poor_relief", command.polity_id, command.values, command.release)
    return Effect("The relief is set so.")


@player_action("poor_relief:delete", ActionKind.EDIT_RECORD)
async def poor_relief_delete(scope: PlayerScope, command: PoorReliefTarget) -> Effect:
    await control.delete_record(await scope.context("poor_relief_delete"), "poor_relief", command.polity_id)
    return Effect("The relief is ended.")


@player_action("measure_standard:set", ActionKind.EDIT_RECORD)
async def measure_standard_set(scope: PlayerScope, command: MeasureStandardDraft) -> Effect:
    row = await control.set_record(
        await scope.context("measure_standard_set"),
        "measure_standard",
        {"polity_entity_id": command.polity_id},
        {"standard": command.standard, "fraud": command.fraud},
    )
    return Effect("The realm sets its measures.", values={"record_id": getattr(row, "id", 0)})


@player_action("measure_standard:edit", ActionKind.EDIT_RECORD)
async def measure_standard_edit(scope: PlayerScope, command: MeasureStandardEdit) -> Effect:
    await control.edit_record(await scope.context("measure_standard_edit"), "measure_standard", command.polity_id, command.values, command.release)
    return Effect("The standard is set so.")


@player_action("measure_standard:delete", ActionKind.EDIT_RECORD)
async def measure_standard_delete(scope: PlayerScope, command: MeasureStandardTarget) -> Effect:
    await control.delete_record(await scope.context("measure_standard_delete"), "measure_standard", command.polity_id)
    return Effect("The standard is struck.")


@player_action("membership_category:right", ActionKind.EDIT_RECORD)
async def membership_category_right(scope: PlayerScope, command: RightGrant) -> Effect:
    await control.grant_right(await scope.context("membership_category_right"), command.polity_id, command.category, command.right, granted=command.granted)
    return Effect("The realm grants that right." if command.granted else "The realm takes that right away.", command.polity_id)


@player_action("town_life:run", ActionKind.EDIT_RECORD)
async def town_life_run(scope: PlayerScope, command: RunNow) -> Effect:
    tally = await control.run_town_life(await scope.context("town_life_run"))
    houses = several(tally.houses, "house of welfare", "houses of welfare")
    return Effect(f"Tended {several(tally.taverns, 'tavern', 'taverns')}, {houses} and {several(tally.cooperatives, 'cooperative', 'cooperatives')}.")


@player_action("civics:run", ActionKind.EDIT_RECORD)
async def civics_run(scope: PlayerScope, command: RunNow) -> Effect:
    tally = await control.run_civics(await scope.context("civics_run"))
    found = several(tally.evidence, "piece of evidence", "pieces of evidence")
    return Effect(f"Found {found} and naturalised {several(tally.naturalised, 'foreigner', 'foreigners')}.")


@player_action("age_set:run", ActionKind.EDIT_RECORD)
async def age_set_run(scope: PlayerScope, command: RunNow) -> Effect:
    tally = await control.run_age_sets(await scope.context("age_set_run"))
    return Effect(f"Initiated {several(tally.initiated, 'youth', 'youths')} and promoted {several(tally.promoted, 'age-set', 'age-sets')}.")
