from pydantic import Field

from aerona.core.grammar import spoken
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.body import BodyPart
from aerona.domain.enums.constructs import MindWill
from aerona.domain.enums.made import (
    AugmentKind,
    AugmentMake,
    AugmentSlot,
    Authenticity,
    CompanyHoldingKind,
    DataContent,
    EffectTarget,
    IntrusionAim,
    IntrusionApproach,
    IntrusionTarget,
    RealmAwareness,
    RealmEntry,
    RealmPurpose,
    ReplicatorOutput,
    ReplicatorScale,
)
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.minds import MindAffect, MindMaking, MindPurpose, MindSeat, MindUpkeep, StateMedium
from aerona.domain.enums.networks import NetworkCarrier, NetworkRole, OutageCause
from aerona.domain.enums.society import Commodity
from aerona.engine import augments
from aerona.engine.made import control
from aerona.engine.made.intrusion import Attempt, intrude
from aerona.engine.minds import continuity, law
from aerona.engine.minds.making import Making, make_mind
from aerona.services.player.cosmography import Edited
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

PERCENT = 100
MANY = 1_000_000
NAME = Field(min_length=1, max_length=120)


class MindTarget(Command):
    mind_id: int


class MindPlace(Command):
    mind_id: int
    seat: MindSeat = MindSeat.BODY
    seat_node_id: int | None = None


class MindMade(Command):
    mind_id: int
    maker_id: int | None = None
    method: MindMaking = MindMaking.CRAFT
    seat: MindSeat = MindSeat.BODY
    seat_node_id: int | None = None
    will: MindWill = MindWill.INSTRUCTED
    purpose: MindPurpose = MindPurpose.SERVANT
    affect: MindAffect = MindAffect.NONE
    upkeep: MindUpkeep = MindUpkeep.MAINTENANCE
    skill: int = Field(default=0, ge=0, le=PERCENT)


class MindSave(Command):
    mind_id: int
    holder_id: int | None = None
    owner_id: int | None = None
    medium: StateMedium = StateMedium.RECORD


class StateRestore(Command):
    state_id: int
    seat: MindSeat = MindSeat.BODY
    seat_node_id: int | None = None


class MindPair(Command):
    first_id: int
    second_id: int


class MindSoul(Command):
    mind_id: int
    grant: bool = True


class NetworkDraft(Command):
    name: str = NAME
    carrier: NetworkCarrier = NetworkCarrier.RELAY
    owner_id: int | None = None
    place_id: int | None = None


class NetworkJoin(Command):
    network_id: int
    member_id: int
    role: NetworkRole = NetworkRole.END


class NetworkLink(Command):
    first_id: int
    second_id: int
    toll: int = Field(default=0, ge=0, le=MANY)
    filter_pct: int = Field(default=0, ge=0, le=PERCENT)
    owner_id: int | None = None


class NetworkCut(Command):
    network_id: int
    cause: OutageCause = OutageCause.SABOTAGE
    epochs: int = Field(default=1, ge=1, le=PERCENT)
    severity: int = Field(default=60, ge=0, le=PERCENT)


class EffectDraft(Command):
    target: EffectTarget = EffectTarget.SKILL
    key: str = Field(min_length=1, max_length=60)
    amount: int = Field(default=10, ge=-PERCENT, le=PERCENT)


class AugmentDraft(Command):
    bearer_id: int
    slot: AugmentSlot = AugmentSlot.PART
    part: BodyPart | None = None
    kind: AugmentKind = AugmentKind.ENHANCEMENT
    make: AugmentMake = AugmentMake.MADE
    quality: int = Field(default=50, ge=0, le=PERCENT)
    surgeon_id: int | None = None
    effects: list[EffectDraft] = Field(default_factory=list, max_length=12)


class AugmentTarget(Command):
    augment_id: int


class AugmentEffect(EffectDraft):
    augment_id: int


class EffectPick(Command):
    effect_id: int


class EffectEdit(Edited):
    effect_id: int


class RealmDraft(Command):
    name: str = NAME
    keeper_id: int | None = None
    host_id: int | None = None
    purpose: RealmPurpose = RealmPurpose.DWELLING
    time_ratio_pct: int = Field(default=100, ge=1, le=10000)
    entry: RealmEntry = RealmEntry.INTERFACE
    aware: RealmAwareness = RealmAwareness.KNOWS
    upkeep: MindUpkeep = MindUpkeep.MAINTENANCE


class IntrusionDraft(Command):
    actor_id: int | None = None
    target: IntrusionTarget = IntrusionTarget.NETWORK
    target_id: int | None = None
    approach: IntrusionApproach = IntrusionApproach.TECHNICAL
    aim: IntrusionAim = IntrusionAim.READ
    blamed_id: int | None = None


class StoreDraft(Command):
    holder_id: int
    owner_id: int | None = None
    security: int = Field(default=30, ge=0, le=PERCENT)


class ContentDraft(Command):
    store_id: int
    content: DataContent = DataContent.SECRET
    subject_id: int | None = None
    reference: int | None = None


class ContentTarget(Command):
    content_id: int


class RecordMark(Command):
    account_id: int
    authenticity: Authenticity = Authenticity.FORGED


class HoldingDraft(Command):
    company_id: int
    holding_id: int
    kind: CompanyHoldingKind = CompanyHoldingKind.STRUCTURE


class LineDraft(Command):
    name: str = NAME
    scale: ReplicatorScale = ReplicatorScale.MACHINE
    feedstock: MaterialKind = MaterialKind.IRON
    output: ReplicatorOutput = ReplicatorOutput.GOODS
    growth_pct: int = Field(default=10, ge=0, le=PERCENT)
    error_pct: int = Field(default=5, ge=0, le=PERCENT)
    containment: int = Field(default=80, ge=0, le=PERCENT)
    kill_switch: bool = True
    owner_id: int | None = None
    maker_id: int | None = None
    place_id: int
    mass: int = Field(default=10, ge=1, le=MANY)


class LineTarget(Command):
    line_id: int


class LineSeed(Command):
    line_id: int
    place_id: int
    mass: int = Field(default=10, ge=1, le=MANY)


class PresenceTarget(Command):
    presence_id: int


class PatternDraft(Command):
    commodity: Commodity = Commodity.GOODS
    holder_id: int | None = None
    fee: int = Field(default=5, ge=0, le=MANY)
    open: bool = False


class RelicDraft(Command):
    thing_id: int
    make_knowledge: int = Field(default=5, ge=0, le=PERCENT)
    repair_knowledge: int = Field(default=4, ge=0, le=PERCENT)


class SalvageDraft(Command):
    site_id: int
    holder_id: int | None = None
    yield_left: int = Field(default=50, ge=0, le=MANY)


@player_action("mind:make", ActionKind.EDIT_RECORD)
async def mind_make(scope: PlayerScope, command: MindMade) -> Effect:
    making = Making(command.method, command.seat, command.seat_node_id, command.will, command.purpose, command.affect, command.upkeep, skill=command.skill)
    await make_mind(await scope.context("mind_make"), command.mind_id, command.maker_id, making)
    return Effect("A mind is made in that seat.", command.mind_id)


@player_action("mind:copy", ActionKind.EDIT_RECORD)
async def mind_copy(scope: PlayerScope, command: MindPlace) -> Effect:
    copy = await continuity.copy_mind(await scope.context("mind_copy"), command.mind_id, command.seat, command.seat_node_id, forced=True)
    return Effect("The mind is copied.", command.mind_id, created_ids=(copy.id,))


@player_action("mind:save", ActionKind.EDIT_RECORD)
async def mind_save(scope: PlayerScope, command: MindSave) -> Effect:
    row = await continuity.save_mind(await scope.context("mind_save"), command.mind_id, command.holder_id, command.owner_id, command.medium, forced=True)
    return Effect("The mind's state is saved.", command.mind_id, values={"state_id": row.id})


@player_action("mind:restore", ActionKind.EDIT_RECORD)
async def mind_restore(scope: PlayerScope, command: StateRestore) -> Effect:
    entity = await continuity.restore_mind(await scope.context("mind_restore"), command.state_id, command.seat, command.seat_node_id)
    return Effect("The mind is restored from what was saved.", entity.id)


@player_action("mind:transfer", ActionKind.EDIT_RECORD)
async def mind_transfer(scope: PlayerScope, command: MindPlace) -> Effect:
    await continuity.transfer_mind(await scope.context("mind_transfer"), command.mind_id, command.seat, command.seat_node_id, forced=True)
    return Effect("The mind moves to its new seat.", command.mind_id)


@player_action("mind:merge", ActionKind.EDIT_RECORD)
async def mind_merge(scope: PlayerScope, command: MindPair) -> Effect:
    await continuity.merge_minds(await scope.context("mind_merge"), command.first_id, command.second_id, forced=True)
    return Effect("The two minds become one.", command.first_id)


@player_action("mind:divide", ActionKind.EDIT_RECORD)
async def mind_divide(scope: PlayerScope, command: MindPlace) -> Effect:
    part = await continuity.divide_mind(await scope.context("mind_divide"), command.mind_id, command.seat, command.seat_node_id)
    return Effect("The mind divides in two.", command.mind_id, created_ids=(part.id,))


@player_action("mind:soul", ActionKind.EDIT_RECORD)
async def mind_soul(scope: PlayerScope, command: MindSoul) -> Effect:
    ctx = await scope.context("mind_soul")
    if command.grant:
        await law.grant_soul(ctx, command.mind_id)
        return Effect("The mind is given a soul.", command.mind_id)
    await law.withhold_soul(ctx, command.mind_id)
    return Effect("The mind's soul is withheld.", command.mind_id)


@player_action("mind:reset", ActionKind.EDIT_RECORD)
async def mind_reset(scope: PlayerScope, command: MindTarget) -> Effect:
    await control.reset_mind(await scope.context("mind_reset"), command.mind_id)
    return Effect("The mind is set back to what its kind is born with.", command.mind_id)


@player_action("network:found", ActionKind.EDIT_RECORD)
async def network_found(scope: PlayerScope, command: NetworkDraft) -> Effect:
    row = await control.found_network(await scope.context("network_found"), command.owner_id, command.name, command.carrier, command.place_id)
    return Effect("A network is founded.", row.network_entity_id, created_ids=(row.network_entity_id,))


@player_action("network:join", ActionKind.EDIT_RECORD)
async def network_join(scope: PlayerScope, command: NetworkJoin) -> Effect:
    row = await control.join_network(await scope.context("network_join"), command.network_id, command.member_id, command.role)
    return Effect("The member joins the network.", command.network_id, values={"node_id": row.id})


@player_action("network:link", ActionKind.EDIT_RECORD)
async def network_link(scope: PlayerScope, command: NetworkLink) -> Effect:
    row = await control.link_networks(
        await scope.context("network_link"), command.first_id, command.second_id, toll=command.toll, filter_pct=command.filter_pct, owner_id=command.owner_id
    )
    return Effect("A gateway joins the two networks.", command.first_id, values={"gateway_id": row.id})


@player_action("network:cut", ActionKind.EDIT_RECORD)
async def network_cut(scope: PlayerScope, command: NetworkCut) -> Effect:
    await control.cut_network(await scope.context("network_cut"), command.network_id, command.cause, command.epochs, command.severity)
    return Effect("The network goes down.", command.network_id)


@player_action("augment:install", ActionKind.EDIT_RECORD)
async def augment_install(scope: PlayerScope, command: AugmentDraft) -> Effect:
    row = await augments.install(
        await scope.context("augment_install"),
        command.bearer_id,
        slot=command.slot,
        part=command.part,
        kind=command.kind,
        make=command.make,
        quality=command.quality,
        surgeon_id=command.surgeon_id,
        effects=[(effect.target, effect.key, effect.amount) for effect in command.effects],
        forced=True,
    )
    return Effect("The augment is installed.", command.bearer_id, values={"augment_id": row.id})


@player_action("augment:remove", ActionKind.EDIT_RECORD)
async def augment_remove(scope: PlayerScope, command: AugmentTarget) -> Effect:
    bearer = await augments.remove(await scope.context("augment_remove"), command.augment_id)
    return Effect("The augment is taken out.", bearer)


@player_action("augment:effect", ActionKind.EDIT_RECORD)
async def augment_effect(scope: PlayerScope, command: AugmentEffect) -> Effect:
    row = await control.add_effect(await scope.context("augment_effect"), command.augment_id, command.target, command.key, command.amount)
    return Effect("The augment gains an effect.", values={"effect_id": row.id})


@player_action("augment:edit_effect", ActionKind.EDIT_RECORD)
async def augment_edit_effect(scope: PlayerScope, command: EffectEdit) -> Effect:
    await control.edit_effect(await scope.context("augment_edit_effect"), command.effect_id, command.values, command.release)
    return Effect("The effect is set so.", values={"effect_id": command.effect_id})


@player_action("augment:drop_effect", ActionKind.EDIT_RECORD)
async def augment_drop_effect(scope: PlayerScope, command: EffectPick) -> Effect:
    augment = await control.drop_effect(await scope.context("augment_drop_effect"), command.effect_id)
    return Effect("The augment loses that effect.", values={"augment_id": augment})


@player_action("realm:make", ActionKind.EDIT_RECORD)
async def realm_make(scope: PlayerScope, command: RealmDraft) -> Effect:
    draft = control.RealmDraft(
        command.name, command.keeper_id, command.host_id, command.purpose, command.time_ratio_pct, command.entry, command.aware, command.upkeep
    )
    row = await control.make_realm(await scope.context("realm_make"), draft)
    return Effect("A made realm opens.", row.dimension_id, created_ids=(row.dimension_id,))


@player_action("intrusion:make", ActionKind.EDIT_RECORD)
async def intrusion_make(scope: PlayerScope, command: IntrusionDraft) -> Effect:
    attempt = Attempt(command.actor_id, command.target, command.target_id, command.approach, command.aim, command.blamed_id)
    row = await intrude(await scope.context("intrusion_make"), attempt)
    return Effect(f"The intrusion {spoken(row.outcome)}.", command.target_id, values={"intrusion_id": row.id})


@player_action("data_store:open", ActionKind.EDIT_RECORD)
async def data_store_open(scope: PlayerScope, command: StoreDraft) -> Effect:
    row = await control.open_store(await scope.context("data_store_open"), command.holder_id, command.owner_id, command.security)
    return Effect("A store of records is opened.", command.holder_id, values={"store_id": row.id})


@player_action("data_store:put", ActionKind.EDIT_RECORD)
async def data_store_put(scope: PlayerScope, command: ContentDraft) -> Effect:
    row = await control.put_content(await scope.context("data_store_put"), command.store_id, command.content, command.subject_id, command.reference)
    return Effect("The store holds it now.", command.subject_id, values={"content_id": row.id})


@player_action("data_store:take", ActionKind.EDIT_RECORD)
async def data_store_take(scope: PlayerScope, command: ContentTarget) -> Effect:
    store = await control.take_content(await scope.context("data_store_take"), command.content_id)
    return Effect("The store no longer holds it.", values={"store_id": store})


@player_action("record:authenticity", ActionKind.EDIT_RECORD)
async def record_authenticity(scope: PlayerScope, command: RecordMark) -> Effect:
    row = await control.mark_record(await scope.context("record_authenticity"), command.account_id, command.authenticity)
    return Effect("The record is marked so.", row.holder_entity_id)


@player_action("company:hold", ActionKind.EDIT_RECORD)
async def company_hold(scope: PlayerScope, command: HoldingDraft) -> Effect:
    row = await control.hold_for(await scope.context("company_hold"), command.company_id, command.holding_id, command.kind)
    return Effect("The company holds it now.", command.company_id, values={"holding_id": row.id})


@player_action("replicator:found", ActionKind.EDIT_RECORD)
async def replicator_found(scope: PlayerScope, command: LineDraft) -> Effect:
    draft = control.LineDraft(
        command.name,
        command.scale,
        command.feedstock,
        command.output,
        command.growth_pct,
        command.error_pct,
        command.containment,
        command.kill_switch,
        command.owner_id,
        command.maker_id,
        command.place_id,
        command.mass,
    )
    row = await control.found_line(await scope.context("replicator_found"), draft)
    return Effect("A self-making line begins.", command.place_id, values={"line_id": row.id})


@player_action("replicator:stop", ActionKind.EDIT_RECORD)
async def replicator_stop(scope: PlayerScope, command: LineTarget) -> Effect:
    await control.stop_line(await scope.context("replicator_stop"), command.line_id)
    return Effect("The line is stopped.", values={"line_id": command.line_id})


@player_action("replicator:seed", ActionKind.EDIT_RECORD)
async def replicator_seed(scope: PlayerScope, command: LineSeed) -> Effect:
    row = await control.seed_line(await scope.context("replicator_seed"), command.line_id, command.place_id, command.mass)
    return Effect("The line takes hold there.", command.place_id, values={"presence_id": row.id})


@player_action("replicator:lift", ActionKind.EDIT_RECORD)
async def replicator_lift(scope: PlayerScope, command: PresenceTarget) -> Effect:
    line = await control.lift_presence(await scope.context("replicator_lift"), command.presence_id)
    return Effect("The line is gone from there.", values={"line_id": line})


@player_action("pattern:grant", ActionKind.EDIT_RECORD)
async def pattern_grant(scope: PlayerScope, command: PatternDraft) -> Effect:
    row = await control.grant_pattern(await scope.context("pattern_grant"), command.commodity, command.holder_id, command.fee, command.open)
    return Effect("The pattern right is set.", command.holder_id, values={"pattern_id": row.id})


@player_action("relic:mark", ActionKind.EDIT_RECORD)
async def relic_mark(scope: PlayerScope, command: RelicDraft) -> Effect:
    await control.mark_relic(await scope.context("relic_mark"), command.thing_id, command.make_knowledge, command.repair_knowledge)
    return Effect("The thing is a relic now.", command.thing_id)


@player_action("salvage:open", ActionKind.EDIT_RECORD)
async def salvage_open(scope: PlayerScope, command: SalvageDraft) -> Effect:
    await control.open_salvage(await scope.context("salvage_open"), command.site_id, command.holder_id, command.yield_left)
    return Effect("The site may be salvaged.", command.site_id)
