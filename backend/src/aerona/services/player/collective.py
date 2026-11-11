from pydantic import Field

from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.collective import (
    AccountKind,
    AccountMedium,
    AccountStance,
    ArmsRim,
    ChargeArrangement,
    CollectiveActKind,
    CollectiveTrigger,
    DatingSystemKind,
    DesignComponentKind,
    DesignKind,
    FormativeKind,
    HeraldicCharge,
    HeraldicDivision,
    HeraldryHolderKind,
    MobEnd,
    MobTarget,
    NormBehaviour,
    NormSituation,
    PartitionLine,
    RoleEligibility,
    RoleKind,
    ShieldShape,
    StoryletId,
    SupporterPose,
    Tincture,
)
from aerona.domain.enums.military import HullClass
from aerona.domain.enums.mind import EthicalStance, ValueAxis
from aerona.domain.enums.society import SocialClass
from aerona.engine.collective import control
from aerona.services.player.cosmography import Edited
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

SPAN = 100
CROWD = 1_000_000
YEARS = 100_000
NAME = 200


class MoodDraft(Command):
    town_id: int
    anger: int = Field(default=0, ge=0, le=SPAN)
    anxiety: int = Field(default=0, ge=0, le=SPAN)
    fervour: int = Field(default=0, ge=0, le=SPAN)
    deterrence: int = Field(default=0, ge=0, le=SPAN)
    agitation: int = Field(default=0, ge=0, le=SPAN)


class TownTarget(Command):
    town_id: int


class MoodEdit(Edited):
    town_id: int


class SparkDraft(Command):
    town_id: int
    trigger: CollectiveTrigger


class CascadeTarget(Command):
    cascade_id: int


class MobDraft(Command):
    town_id: int
    act: CollectiveActKind = CollectiveActKind.RIOT
    target: MobTarget = MobTarget.DISTRICT
    size: int = Field(default=100, ge=0, le=CROWD)
    anger: int = Field(default=50, ge=0, le=SPAN)
    target_id: int | None = None


class MobTargetCommand(Command):
    mob_id: int


class MobEdit(Edited):
    mob_id: int


class MobDisperse(Command):
    mob_id: int
    by: MobEnd = MobEnd.CONCESSION


class MovementDraft(Command):
    town_id: int
    act: CollectiveActKind = CollectiveActKind.REVIVAL
    trigger: CollectiveTrigger = CollectiveTrigger.SERMON
    members: int = Field(default=100, ge=0, le=CROWD)
    strength: int = Field(default=40, ge=0, le=SPAN)


class MovementTarget(Command):
    movement_id: int


class MovementEdit(Edited):
    movement_id: int


class AccountDraft(Command):
    holder_id: int
    kind: AccountKind = AccountKind.OFFICIAL_CHRONICLE
    medium: AccountMedium = AccountMedium.BOOK
    collection_id: int | None = None
    subject_id: int | None = None
    fidelity: int = Field(default=60, ge=0, le=SPAN)
    credence: int = Field(default=60, ge=0, le=SPAN)


class AccountTarget(Command):
    account_id: int


class AccountEdit(Edited):
    account_id: int


class AccountRevision(Command):
    account_id: int
    ousted_ids: list[int] = Field(default_factory=list, max_length=20)
    new_ruler_id: int | None = None


class StanceDraft(Command):
    account_id: int
    node_id: int
    stance: AccountStance


class StanceTarget(Command):
    account_id: int
    node_id: int


class StrikeDraft(Command):
    by_id: int
    node_id: int


class StrikeEdit(Edited):
    by_id: int
    node_id: int


class MythDraft(Command):
    holder_id: int
    credence: int = Field(default=70, ge=0, le=SPAN)


class HolderTarget(Command):
    holder_id: int


class HolderEdit(Edited):
    holder_id: int


class CommemorationDraft(Command):
    holder_id: int
    collection_id: int
    pride: bool = True
    strength: int = Field(default=60, ge=0, le=SPAN)


class CommemorationTarget(Command):
    holder_id: int
    collection_id: int


class CommemorationEdit(Edited):
    holder_id: int
    collection_id: int


class LostLandDraft(Command):
    claimant_id: int
    region_id: int
    strength: int = Field(default=60, ge=0, le=SPAN)


class LostLandTarget(Command):
    claimant_id: int
    region_id: int


class LostLandEdit(Edited):
    claimant_id: int
    region_id: int


class StoryletDraft(Command):
    storylet: StoryletId
    world_id: int


class StoryletTarget(Command):
    run_id: int


class StoryletEdit(Edited):
    run_id: int


class StoryletChoice(Command):
    run_id: int
    choice: int = Field(ge=0, le=3)


class NormDraft(Command):
    holder_id: int
    situation: NormSituation
    behaviour: NormBehaviour
    stance: EthicalStance


class NormTarget(Command):
    holder_id: int
    situation: NormSituation
    behaviour: NormBehaviour


class NormEdit(Edited):
    holder_id: int
    situation: NormSituation
    behaviour: NormBehaviour


class ChangeTarget(Command):
    change_id: int


class BiasDraft(Command):
    holder_id: int
    prestige_pct: int = Field(default=40, ge=0, le=SPAN)
    conformity_pct: int = Field(default=40, ge=0, le=SPAN)
    content_pct: int = Field(default=20, ge=0, le=SPAN)


class LearningTarget(Command):
    event_id: int


class GenerationDraft(Command):
    community_id: int
    generation_epoch: int = Field(ge=0)


class GenerationShape(Command):
    community_id: int
    generation_epoch: int = Field(ge=0)
    formative: list[FormativeKind] = Field(default_factory=list, max_length=7)
    axis: ValueAxis | None = None
    shift: int = Field(default=0, ge=-SPAN, le=SPAN)


class GenerationEdit(Edited):
    community_id: int
    generation_epoch: int


class DiasporaDraft(Command):
    people_id: int
    host_id: int
    population: int = Field(default=100, ge=0, le=CROWD)
    ties: int = Field(default=60, ge=0, le=SPAN)


class DiasporaTarget(Command):
    people_id: int
    host_id: int


class DiasporaEdit(Edited):
    people_id: int
    host_id: int


class TransitionDraft(Command):
    community_id: int
    fertility_pct: int = Field(default=100, ge=0, le=200)
    elder_share: int = Field(default=10, ge=0, le=SPAN)
    urban_share: int = Field(default=20, ge=0, le=SPAN)
    literacy: int = Field(default=10, ge=0, le=SPAN)


class CommunityTarget(Command):
    community_id: int


class CommunityEdit(Edited):
    community_id: int


class SexRatioDraft(Command):
    community_id: int
    males_per_hundred: int = Field(default=100, ge=0, le=1000)
    widows: int = Field(default=0, ge=0, le=CROWD)


class RoleDraft(Command):
    holder_id: int
    role: RoleKind
    eligibility: RoleEligibility = RoleEligibility.ANY
    min_age: int = Field(default=0, ge=0, le=200)
    classes: list[SocialClass] = Field(default_factory=list)
    stance: EthicalStance = EthicalStance.ACCEPTABLE


class RoleTarget(Command):
    holder_id: int
    role: RoleKind


class RoleEdit(Command):
    holder_id: int
    role: RoleKind
    values: dict[str, int | str | bool | list[SocialClass] | None] = Field(default_factory=dict)
    release: list[str] = Field(default_factory=list)


class DatingDraft(Command):
    holder_id: int
    kind: DatingSystemKind
    anchor_year: int = Field(default=0, ge=0, le=YEARS)
    label_id: int | None = None
    cycle_years: int = Field(default=60, ge=0, le=YEARS)


class ArmsDraft(Command):
    holder_id: int
    holder_kind: HeraldryHolderKind
    shape: ShieldShape = ShieldShape.HEATER
    field: Tincture
    division: HeraldicDivision = HeraldicDivision.PLAIN
    line: PartitionLine = PartitionLine.STRAIGHT
    second: Tincture | None = None
    charge: HeraldicCharge = HeraldicCharge.NONE
    charge_tincture: Tincture | None = None
    charge_two: HeraldicCharge = HeraldicCharge.NONE
    charge_two_tincture: Tincture | None = None
    charge_three: HeraldicCharge = HeraldicCharge.NONE
    charge_three_tincture: Tincture | None = None
    arrangement: ChargeArrangement = ChargeArrangement.TWO_AND_ONE
    rim: ArmsRim = ArmsRim.LINE
    rim_line: PartitionLine = PartitionLine.STRAIGHT
    rim_tincture: Tincture | None = None
    supporter: HeraldicCharge = HeraldicCharge.NONE
    supporter_pose: SupporterPose = SupporterPose.CROSSED
    supporter_tincture: Tincture | None = None
    crest: HeraldicCharge = HeraldicCharge.NONE
    crest_tincture: Tincture | None = None
    motto: str | None = Field(default=None, max_length=NAME)


class ArmsQuarter(Command):
    holder_id: int
    other_id: int


class ArmsDifference(Command):
    holder_id: int
    parent_id: int
    border: Tincture = Tincture.SILVER
    line: PartitionLine = PartitionLine.STRAIGHT


class DesignDraft(Command):
    owner_id: int
    kind: DesignKind
    hull: HullClass | None = None
    name: str | None = Field(default=None, max_length=NAME)
    quality: int = Field(default=50, ge=0, le=SPAN)


class DesignTarget(Command):
    design_id: int


class DesignEdit(Edited):
    design_id: int


class ComponentDraft(Command):
    design_id: int
    component: DesignComponentKind
    material_id: int | None = None
    size: int = Field(default=3, ge=0, le=10)
    quality: int = Field(default=50, ge=0, le=SPAN)


class ComponentTarget(Command):
    design_id: int
    component: DesignComponentKind


class FitDraft(Command):
    vessel_id: int
    design_id: int


class WearDraft(Command):
    vessel_id: int
    component: DesignComponentKind
    wear: int = Field(default=0, ge=0, le=SPAN)


class WearTarget(Command):
    vessel_id: int
    component: DesignComponentKind


class WearEdit(Edited):
    vessel_id: int
    component: DesignComponentKind


def mood_values(command: MoodDraft) -> dict[str, int]:
    return {"anger": command.anger, "anxiety": command.anxiety, "fervour": command.fervour, "deterrence": command.deterrence, "agitation": command.agitation}


@player_action("crowd_mood:set", ActionKind.EDIT_RECORD)
async def crowd_mood_set(scope: PlayerScope, command: MoodDraft) -> Effect:
    await control.set_mood(await scope.context("crowd_mood_set"), command.town_id, mood_values(command))
    return Effect("The town's mood is set so.", command.town_id)


@player_action("crowd_mood:edit", ActionKind.EDIT_RECORD)
async def crowd_mood_edit(scope: PlayerScope, command: MoodEdit) -> Effect:
    await control.edit_record(await scope.context("crowd_mood_edit"), "crowd_mood", command.town_id, command.values, command.release)
    return Effect("The town's mood is set so.", command.town_id)


@player_action("crowd_mood:delete", ActionKind.EDIT_RECORD)
async def crowd_mood_delete(scope: PlayerScope, command: TownTarget) -> Effect:
    await control.delete_record(await scope.context("crowd_mood_delete"), "crowd_mood", command.town_id)
    return Effect("The town's mood will be read anew.", command.town_id)


@player_action("cascade:spark", ActionKind.EDIT_RECORD)
async def cascade_spark(scope: PlayerScope, command: SparkDraft) -> Effect:
    row = await control.spark_cascade(await scope.context("cascade_spark"), command.town_id, command.trigger)
    return Effect(f"{row.participants} took part; the cascade ended as {row.outcome.value}.", command.town_id)


@player_action("cascade:delete", ActionKind.EDIT_RECORD)
async def cascade_delete(scope: PlayerScope, command: CascadeTarget) -> Effect:
    await control.delete_record(await scope.context("cascade_delete"), "cascade", command.cascade_id)
    return Effect("The cascade is struck from the record.")


@player_action("mob:raise", ActionKind.EDIT_RECORD)
async def mob_raise(scope: PlayerScope, command: MobDraft) -> Effect:
    ctx = await scope.context("mob_raise")
    await control.raise_mob(ctx, command.town_id, command.act, command.target, size=command.size, anger=command.anger, target_id=command.target_id)
    return Effect("A crowd gathers.", command.town_id)


@player_action("mob:edit", ActionKind.EDIT_RECORD)
async def mob_edit(scope: PlayerScope, command: MobEdit) -> Effect:
    await control.edit_record(await scope.context("mob_edit"), "mob", command.mob_id, command.values, command.release)
    return Effect("The crowd is set so.")


@player_action("mob:disperse", ActionKind.EDIT_RECORD)
async def mob_disperse(scope: PlayerScope, command: MobDisperse) -> Effect:
    await control.disperse_mob(await scope.context("mob_disperse"), command.mob_id, command.by)
    return Effect("The crowd disperses.")


@player_action("mob:delete", ActionKind.EDIT_RECORD)
async def mob_delete(scope: PlayerScope, command: MobTargetCommand) -> Effect:
    await control.delete_record(await scope.context("mob_delete"), "mob", command.mob_id)
    return Effect("The crowd is struck from the record.")


@player_action("popular_movement:found", ActionKind.EDIT_RECORD)
async def movement_found(scope: PlayerScope, command: MovementDraft) -> Effect:
    ctx = await scope.context("movement_found")
    await control.found_movement(ctx, command.town_id, command.act, command.trigger, members=command.members, strength=command.strength)
    return Effect("A movement rises.", command.town_id)


@player_action("popular_movement:edit", ActionKind.EDIT_RECORD)
async def movement_edit(scope: PlayerScope, command: MovementEdit) -> Effect:
    await control.edit_record(await scope.context("movement_edit"), "movement", command.movement_id, command.values, command.release)
    return Effect("The movement is set so.")


@player_action("popular_movement:delete", ActionKind.EDIT_RECORD)
async def movement_delete(scope: PlayerScope, command: MovementTarget) -> Effect:
    await control.delete_record(await scope.context("movement_delete"), "movement", command.movement_id)
    return Effect("The movement is struck from the record.")


@player_action("account:write", ActionKind.EDIT_RECORD)
async def account_write(scope: PlayerScope, command: AccountDraft) -> Effect:
    ctx = await scope.context("account_write")
    row = await control.write_account(
        ctx,
        command.holder_id,
        command.kind,
        medium=command.medium,
        collection_id=command.collection_id,
        subject_id=command.subject_id,
        fidelity=command.fidelity,
        credence=command.credence,
    )
    return Effect("The account is written.", command.holder_id, created_ids=(row.id,))


@player_action("account:edit", ActionKind.EDIT_RECORD)
async def account_edit(scope: PlayerScope, command: AccountEdit) -> Effect:
    await control.edit_record(await scope.context("account_edit"), "account", command.account_id, command.values, command.release)
    return Effect("The account is set so.")


@player_action("account:revise", ActionKind.EDIT_RECORD)
async def account_revise(scope: PlayerScope, command: AccountRevision) -> Effect:
    row = await control.revise_account(await scope.context("account_revise"), command.account_id, command.ousted_ids, command.new_ruler_id)
    return Effect("The account is rewritten.", created_ids=(row.id,))


@player_action("account:expose", ActionKind.EDIT_RECORD)
async def account_expose(scope: PlayerScope, command: AccountTarget) -> Effect:
    await control.expose_account(await scope.context("account_expose"), command.account_id)
    return Effect("The older account comes to light.")


@player_action("account:delete", ActionKind.EDIT_RECORD)
async def account_delete(scope: PlayerScope, command: AccountTarget) -> Effect:
    await control.delete_record(await scope.context("account_delete"), "account", command.account_id)
    return Effect("The account is lost.")


@player_action("account_stance:set", ActionKind.EDIT_RECORD)
async def account_stance_set(scope: PlayerScope, command: StanceDraft) -> Effect:
    await control.set_stance(await scope.context("account_stance_set"), command.account_id, command.node_id, command.stance)
    return Effect("The account speaks of them so.", command.node_id)


@player_action("account_stance:delete", ActionKind.EDIT_RECORD)
async def account_stance_delete(scope: PlayerScope, command: StanceTarget) -> Effect:
    await control.delete_record(await scope.context("account_stance_delete"), "account_stance", (command.account_id, command.node_id))
    return Effect("The account no longer speaks of them.", command.node_id)


@player_action("memory_strike:set", ActionKind.EDIT_RECORD)
async def memory_strike_set(scope: PlayerScope, command: StrikeDraft) -> Effect:
    await control.strike_figure(await scope.context("memory_strike_set"), command.by_id, command.node_id)
    return Effect("They are struck from the records.", command.node_id)


@player_action("memory_strike:edit", ActionKind.EDIT_RECORD)
async def memory_strike_edit(scope: PlayerScope, command: StrikeEdit) -> Effect:
    await control.edit_record(await scope.context("memory_strike_edit"), "memory_strike", (command.node_id, command.by_id), command.values, command.release)
    return Effect("The struck memory is set so.", command.node_id)


@player_action("memory_strike:delete", ActionKind.EDIT_RECORD)
async def memory_strike_delete(scope: PlayerScope, command: StrikeDraft) -> Effect:
    await control.delete_record(await scope.context("memory_strike_delete"), "memory_strike", (command.node_id, command.by_id))
    return Effect("Their memory is restored.", command.node_id)


@player_action("founding_myth:set", ActionKind.EDIT_RECORD)
async def founding_myth_set(scope: PlayerScope, command: MythDraft) -> Effect:
    await control.set_myth(await scope.context("founding_myth_set"), command.holder_id, command.credence)
    return Effect("The founding story is believed so.", command.holder_id)


@player_action("founding_myth:edit", ActionKind.EDIT_RECORD)
async def founding_myth_edit(scope: PlayerScope, command: HolderEdit) -> Effect:
    await control.edit_record(await scope.context("founding_myth_edit"), "founding_myth", command.holder_id, command.values, command.release)
    return Effect("The founding myth is set so.", command.holder_id)


@player_action("founding_myth:debunk", ActionKind.EDIT_RECORD)
async def founding_myth_debunk(scope: PlayerScope, command: HolderTarget) -> Effect:
    await control.debunk_myth(await scope.context("founding_myth_debunk"), command.holder_id)
    return Effect("The founding story is shown to be untrue.", command.holder_id)


@player_action("founding_myth:delete", ActionKind.EDIT_RECORD)
async def founding_myth_delete(scope: PlayerScope, command: HolderTarget) -> Effect:
    await control.delete_record(await scope.context("founding_myth_delete"), "founding_myth", command.holder_id)
    return Effect("The founding story will be told anew.", command.holder_id)


@player_action("commemoration:set", ActionKind.EDIT_RECORD)
async def commemoration_set(scope: PlayerScope, command: CommemorationDraft) -> Effect:
    ctx = await scope.context("commemoration_set")
    await control.set_commemoration(ctx, command.holder_id, command.collection_id, pride=command.pride, strength=command.strength)
    return Effect("The anniversary will be kept.", command.holder_id)


@player_action("commemoration:edit", ActionKind.EDIT_RECORD)
async def commemoration_edit(scope: PlayerScope, command: CommemorationEdit) -> Effect:
    ctx = await scope.context("commemoration_edit")
    await control.edit_record(ctx, "commemoration", (command.holder_id, command.collection_id), command.values, command.release)
    return Effect("The anniversary is set so.", command.holder_id)


@player_action("commemoration:relive", ActionKind.EDIT_RECORD)
async def commemoration_relive(scope: PlayerScope, command: CommemorationTarget) -> Effect:
    await control.relive_now(await scope.context("commemoration_relive"), command.holder_id, command.collection_id)
    return Effect("The anniversary is kept now.", command.holder_id)


@player_action("commemoration:delete", ActionKind.EDIT_RECORD)
async def commemoration_delete(scope: PlayerScope, command: CommemorationTarget) -> Effect:
    await control.delete_record(await scope.context("commemoration_delete"), "commemoration", (command.holder_id, command.collection_id))
    return Effect("The anniversary is forgotten.", command.holder_id)


@player_action("lost_land:set", ActionKind.EDIT_RECORD)
async def lost_land_set(scope: PlayerScope, command: LostLandDraft) -> Effect:
    await control.set_lost_land(await scope.context("lost_land_set"), command.claimant_id, command.region_id, command.strength)
    return Effect("The lost land is remembered.", command.claimant_id)


@player_action("lost_land:edit", ActionKind.EDIT_RECORD)
async def lost_land_edit(scope: PlayerScope, command: LostLandEdit) -> Effect:
    await control.edit_record(await scope.context("lost_land_edit"), "lost_land", (command.claimant_id, command.region_id), command.values, command.release)
    return Effect("The memory of the lost land is set so.", command.claimant_id)


@player_action("lost_land:delete", ActionKind.EDIT_RECORD)
async def lost_land_delete(scope: PlayerScope, command: LostLandTarget) -> Effect:
    await control.delete_record(await scope.context("lost_land_delete"), "lost_land", (command.claimant_id, command.region_id))
    return Effect("The lost land is forgotten.", command.claimant_id)


@player_action("storylet:open", ActionKind.EDIT_RECORD)
async def storylet_open(scope: PlayerScope, command: StoryletDraft) -> Effect:
    run = await control.open_storylet(await scope.context("storylet_open"), command.storylet, command.world_id)
    return Effect("The storylet is in motion.", run.chooser_node_id, created_ids=(run.id,))


@player_action("storylet:edit", ActionKind.EDIT_RECORD)
async def storylet_edit(scope: PlayerScope, command: StoryletEdit) -> Effect:
    await control.edit_record(await scope.context("storylet_edit"), "storylet", command.run_id, command.values, command.release)
    return Effect("The storylet is set so.")


@player_action("storylet:choose", ActionKind.EDIT_RECORD)
async def storylet_choose(scope: PlayerScope, command: StoryletChoice) -> Effect:
    run = await control.choose_storylet(await scope.context("storylet_choose"), command.run_id, command.choice)
    return Effect("The choice is made.", run.chooser_node_id)


@player_action("storylet:delete", ActionKind.EDIT_RECORD)
async def storylet_delete(scope: PlayerScope, command: StoryletTarget) -> Effect:
    await control.delete_record(await scope.context("storylet_delete"), "storylet", command.run_id)
    return Effect("The storylet is struck from the record.")


@player_action("social_norm:set", ActionKind.EDIT_RECORD)
async def social_norm_set(scope: PlayerScope, command: NormDraft) -> Effect:
    await control.set_norm(await scope.context("social_norm_set"), command.holder_id, command.situation, command.behaviour, command.stance)
    return Effect("The custom is set so.", command.holder_id)


@player_action("social_norm:edit", ActionKind.EDIT_RECORD)
async def social_norm_edit(scope: PlayerScope, command: NormEdit) -> Effect:
    key = (command.holder_id, command.situation, command.behaviour)
    await control.edit_record(await scope.context("social_norm_edit"), "social_norm", key, command.values, command.release)
    return Effect("The custom is set so.", command.holder_id)


@player_action("social_norm:delete", ActionKind.EDIT_RECORD)
async def social_norm_delete(scope: PlayerScope, command: NormTarget) -> Effect:
    key = (command.holder_id, command.situation, command.behaviour)
    await control.delete_record(await scope.context("social_norm_delete"), "social_norm", key)
    return Effect("The custom lapses into indifference.", command.holder_id)


@player_action("norm_change:delete", ActionKind.EDIT_RECORD)
async def norm_change_delete(scope: PlayerScope, command: ChangeTarget) -> Effect:
    await control.delete_record(await scope.context("norm_change_delete"), "norm_change", command.change_id)
    return Effect("The change of custom is struck from the record.")


@player_action("learning_bias:set", ActionKind.EDIT_RECORD)
async def learning_bias_set(scope: PlayerScope, command: BiasDraft) -> Effect:
    values = {"prestige_pct": command.prestige_pct, "conformity_pct": command.conformity_pct, "content_pct": command.content_pct}
    await control.set_biases(await scope.context("learning_bias_set"), command.holder_id, values)
    return Effect("The people learn so.", command.holder_id)


@player_action("learning_bias:edit", ActionKind.EDIT_RECORD)
async def learning_bias_edit(scope: PlayerScope, command: HolderEdit) -> Effect:
    await control.edit_record(await scope.context("learning_bias_edit"), "learning_bias", command.holder_id, command.values, command.release)
    return Effect("The people learn so.", command.holder_id)


@player_action("learning_bias:delete", ActionKind.EDIT_RECORD)
async def learning_bias_delete(scope: PlayerScope, command: HolderTarget) -> Effect:
    await control.delete_record(await scope.context("learning_bias_delete"), "learning_bias", command.holder_id)
    return Effect("The people's ways of learning will be read anew.", command.holder_id)


@player_action("learning_event:delete", ActionKind.EDIT_RECORD)
async def learning_event_delete(scope: PlayerScope, command: LearningTarget) -> Effect:
    await control.delete_record(await scope.context("learning_event_delete"), "learning_event", command.event_id)
    return Effect("The lesson is struck from the record.")


@player_action("generation:set", ActionKind.EDIT_RECORD)
async def generation_set(scope: PlayerScope, command: GenerationDraft) -> Effect:
    await control.set_generation(await scope.context("generation_set"), command.community_id, command.generation_epoch, {})
    return Effect("The generation is recorded.", command.community_id)


@player_action("generation:shape", ActionKind.EDIT_RECORD)
async def generation_shape(scope: PlayerScope, command: GenerationShape) -> Effect:
    shifts = {command.axis: command.shift} if command.axis is not None else {}
    ctx = await scope.context("generation_shape")
    await control.shape_generation(ctx, command.community_id, command.generation_epoch, command.formative, shifts)
    return Effect("The generation's youth is set so.", command.community_id)


@player_action("generation:edit", ActionKind.EDIT_RECORD)
async def generation_edit(scope: PlayerScope, command: GenerationEdit) -> Effect:
    key = (command.community_id, command.generation_epoch)
    await control.edit_record(await scope.context("generation_edit"), "generation", key, command.values, command.release)
    return Effect("The generation is set so.", command.community_id)


@player_action("generation:delete", ActionKind.EDIT_RECORD)
async def generation_delete(scope: PlayerScope, command: GenerationDraft) -> Effect:
    await control.delete_record(await scope.context("generation_delete"), "generation", (command.community_id, command.generation_epoch))
    return Effect("The generation is struck from the record.", command.community_id)


@player_action("diaspora:set", ActionKind.EDIT_RECORD)
async def diaspora_set(scope: PlayerScope, command: DiasporaDraft) -> Effect:
    values = {"population": command.population, "ties": command.ties}
    await control.set_diaspora(await scope.context("diaspora_set"), command.people_id, command.host_id, values)
    return Effect("The diaspora is settled.", command.host_id)


@player_action("diaspora:edit", ActionKind.EDIT_RECORD)
async def diaspora_edit(scope: PlayerScope, command: DiasporaEdit) -> Effect:
    await control.edit_record(await scope.context("diaspora_edit"), "diaspora", (command.people_id, command.host_id), command.values, command.release)
    return Effect("The diaspora is set so.", command.host_id)


@player_action("diaspora:delete", ActionKind.EDIT_RECORD)
async def diaspora_delete(scope: PlayerScope, command: DiasporaTarget) -> Effect:
    await control.delete_record(await scope.context("diaspora_delete"), "diaspora", (command.people_id, command.host_id))
    return Effect("The diaspora is struck from the record.", command.host_id)


@player_action("transition:set", ActionKind.EDIT_RECORD)
async def transition_set(scope: PlayerScope, command: TransitionDraft) -> Effect:
    values = {"fertility_pct": command.fertility_pct, "elder_share": command.elder_share, "urban_share": command.urban_share, "literacy": command.literacy}
    await control.set_transition(await scope.context("transition_set"), command.community_id, values)
    return Effect("The community's transition is set so.", command.community_id)


@player_action("transition:edit", ActionKind.EDIT_RECORD)
async def transition_edit(scope: PlayerScope, command: CommunityEdit) -> Effect:
    await control.edit_record(await scope.context("transition_edit"), "transition", command.community_id, command.values, command.release)
    return Effect("The community's transition is set so.", command.community_id)


@player_action("transition:delete", ActionKind.EDIT_RECORD)
async def transition_delete(scope: PlayerScope, command: CommunityTarget) -> Effect:
    await control.delete_record(await scope.context("transition_delete"), "transition", command.community_id)
    return Effect("The community's transition will be read anew.", command.community_id)


@player_action("sex_ratio:set", ActionKind.EDIT_RECORD)
async def sex_ratio_set(scope: PlayerScope, command: SexRatioDraft) -> Effect:
    values = {"males_per_hundred": command.males_per_hundred, "widows": command.widows}
    await control.set_sex_ratio(await scope.context("sex_ratio_set"), command.community_id, values)
    return Effect("The community's balance is set so.", command.community_id)


@player_action("sex_ratio:edit", ActionKind.EDIT_RECORD)
async def sex_ratio_edit(scope: PlayerScope, command: CommunityEdit) -> Effect:
    await control.edit_record(await scope.context("sex_ratio_edit"), "sex_ratio", command.community_id, command.values, command.release)
    return Effect("The community's balance is set so.", command.community_id)


@player_action("sex_ratio:delete", ActionKind.EDIT_RECORD)
async def sex_ratio_delete(scope: PlayerScope, command: CommunityTarget) -> Effect:
    await control.delete_record(await scope.context("sex_ratio_delete"), "sex_ratio", command.community_id)
    return Effect("The community's balance will be counted anew.", command.community_id)


@player_action("role_norm:set", ActionKind.EDIT_RECORD)
async def role_norm_set(scope: PlayerScope, command: RoleDraft) -> Effect:
    ctx = await scope.context("role_norm_set")
    await control.set_role(
        ctx, command.holder_id, command.role, eligibility=command.eligibility, min_age=command.min_age, classes=command.classes, stance=command.stance
    )
    return Effect("The role is open so.", command.holder_id)


@player_action("role_norm:edit", ActionKind.EDIT_RECORD)
async def role_norm_edit(scope: PlayerScope, command: RoleEdit) -> Effect:
    await control.edit_record(await scope.context("role_norm_edit"), "role_norm", (command.holder_id, command.role), command.values, command.release)
    return Effect("The role is open so.", command.holder_id)


@player_action("role_norm:delete", ActionKind.EDIT_RECORD)
async def role_norm_delete(scope: PlayerScope, command: RoleTarget) -> Effect:
    await control.delete_record(await scope.context("role_norm_delete"), "role_norm", (command.holder_id, command.role))
    return Effect("The role is open to all.", command.holder_id)


@player_action("dating_system:set", ActionKind.EDIT_RECORD)
async def dating_system_set(scope: PlayerScope, command: DatingDraft) -> Effect:
    ctx = await scope.context("dating_system_set")
    await control.set_dating(ctx, command.holder_id, command.kind, anchor_year=command.anchor_year, label_id=command.label_id, cycle_years=command.cycle_years)
    return Effect("The years are counted so.", command.holder_id)


@player_action("dating_system:edit", ActionKind.EDIT_RECORD)
async def dating_system_edit(scope: PlayerScope, command: HolderEdit) -> Effect:
    await control.edit_record(await scope.context("dating_system_edit"), "dating_system", command.holder_id, command.values, command.release)
    return Effect("The years are counted so.", command.holder_id)


@player_action("dating_system:delete", ActionKind.EDIT_RECORD)
async def dating_system_delete(scope: PlayerScope, command: HolderTarget) -> Effect:
    await control.delete_record(await scope.context("dating_system_delete"), "dating_system", command.holder_id)
    return Effect("The era will be chosen anew.", command.holder_id)


@player_action("arms:set", ActionKind.EDIT_RECORD)
async def arms_set(scope: PlayerScope, command: ArmsDraft) -> Effect:
    await control.set_arms(
        await scope.context("arms_set"),
        command.holder_id,
        command.holder_kind,
        command.model_dump(exclude={"holder_id", "holder_kind"}),
    )
    return Effect("The arms are granted.", command.holder_id)


@player_action("arms:edit", ActionKind.EDIT_RECORD)
async def arms_edit(scope: PlayerScope, command: HolderEdit) -> Effect:
    await control.edit_arms(await scope.context("arms_edit"), command.holder_id, command.values, command.release)
    return Effect("The arms are set so.", command.holder_id)


@player_action("arms:quarter", ActionKind.EDIT_RECORD)
async def arms_quarter(scope: PlayerScope, command: ArmsQuarter) -> Effect:
    await control.quarter_arms(await scope.context("arms_quarter"), command.holder_id, command.other_id)
    return Effect("The arms are quartered.", command.holder_id)


@player_action("arms:difference", ActionKind.EDIT_RECORD)
async def arms_difference(scope: PlayerScope, command: ArmsDifference) -> Effect:
    await control.difference_arms(await scope.context("arms_difference"), command.holder_id, command.parent_id, command.border, command.line)
    return Effect("The cadet arms are drawn within a border.", command.holder_id)


@player_action("arms:delete", ActionKind.EDIT_RECORD)
async def arms_delete(scope: PlayerScope, command: HolderTarget) -> Effect:
    await control.delete_record(await scope.context("arms_delete"), "arms", command.holder_id)
    return Effect("The arms will be granted anew.", command.holder_id)


@player_action("design:draw", ActionKind.EDIT_RECORD)
async def design_draw(scope: PlayerScope, command: DesignDraft) -> Effect:
    ctx = await scope.context("design_draw")
    row = await control.new_design(ctx, command.owner_id, command.kind, hull=command.hull, name=command.name, quality=command.quality)
    return Effect(f"{row.name} is drawn.", command.owner_id, created_ids=(row.id,))


@player_action("design:edit", ActionKind.EDIT_RECORD)
async def design_edit(scope: PlayerScope, command: DesignEdit) -> Effect:
    await control.edit_design(await scope.context("design_edit"), command.design_id, command.values, command.release)
    return Effect("The design is set so.")


@player_action("design:refit", ActionKind.EDIT_RECORD)
async def design_refit(scope: PlayerScope, command: DesignTarget) -> Effect:
    row = await control.refit_design(await scope.context("design_refit"), command.design_id)
    return Effect(f"{row.name} improves on the old design.", created_ids=(row.id,))


@player_action("design:delete", ActionKind.EDIT_RECORD)
async def design_delete(scope: PlayerScope, command: DesignTarget) -> Effect:
    await control.delete_record(await scope.context("design_delete"), "design", command.design_id)
    return Effect("The design is struck.")


@player_action("design_component:set", ActionKind.EDIT_RECORD)
async def design_component_set(scope: PlayerScope, command: ComponentDraft) -> Effect:
    values = {"material_id": command.material_id, "size": command.size, "quality": command.quality}
    await control.set_component(await scope.context("design_component_set"), command.design_id, command.component, values)
    return Effect("The part is set so.")


@player_action("design_component:delete", ActionKind.EDIT_RECORD)
async def design_component_delete(scope: PlayerScope, command: ComponentTarget) -> Effect:
    await control.delete_component(await scope.context("design_component_delete"), command.design_id, command.component)
    return Effect("The part is taken out of the design.")


@player_action("design:fit", ActionKind.EDIT_RECORD)
async def design_fit(scope: PlayerScope, command: FitDraft) -> Effect:
    await control.fit_vessel(await scope.context("design_fit"), command.vessel_id, command.design_id)
    return Effect("The vessel is refitted to the design.", command.vessel_id)


@player_action("component_wear:set", ActionKind.EDIT_RECORD)
async def component_wear_set(scope: PlayerScope, command: WearDraft) -> Effect:
    await control.set_wear(await scope.context("component_wear_set"), command.vessel_id, command.component, command.wear)
    return Effect("The part's wear is set so.", command.vessel_id)


@player_action("component_wear:edit", ActionKind.EDIT_RECORD)
async def component_wear_edit(scope: PlayerScope, command: WearEdit) -> Effect:
    key = (command.vessel_id, command.component)
    await control.edit_record(await scope.context("component_wear_edit"), "component_wear", key, command.values, command.release)
    return Effect("The part's wear is set so.", command.vessel_id)


@player_action("component_wear:delete", ActionKind.EDIT_RECORD)
async def component_wear_delete(scope: PlayerScope, command: WearTarget) -> Effect:
    await control.delete_record(await scope.context("component_wear_delete"), "component_wear", (command.vessel_id, command.component))
    return Effect("The part is as good as new.", command.vessel_id)
