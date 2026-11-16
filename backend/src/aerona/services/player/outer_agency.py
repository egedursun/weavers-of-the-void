from pydantic import Field
from sqlalchemy import select

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.cosmography import RiftRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.outer_agency import (
    HERALD_FIELDS,
    INCURSION_FIELDS,
    PACT_FIELDS,
    PLAN_FIELDS,
    RELATION_FIELDS,
    SEAL_FIELDS,
    OuterHeraldRow,
    OuterIncursionRow,
    OuterPactRow,
    OuterPlanRow,
    OuterRelationRow,
    OuterSealRow,
)
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.outer import IncursionStage, OuterFate, OuterGoal, OuterPlanState, OuterPrice, OuterRelation, OuterSealKind
from aerona.engine.divine.outer import outer_profile
from aerona.engine.divine.outer_agency import end_being, open_incursion, seal_being, strike_bargain
from aerona.engine.powers.control import edit_fields
from aerona.engine.primitives.queries import living_entity
from aerona.services.player import guards
from aerona.services.player.cosmography import Edited
from aerona.services.player.powers import typed
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class PlanSet(Command):
    being_id: int
    goal: OuterGoal
    target_id: int | None = None
    progress: int = Field(default=0, ge=0, le=100)


class PlanEdit(Edited):
    plan_id: int
    hold: bool = True


class PlanTarget(Command):
    plan_id: int


class HeraldBind(Command):
    being_id: int
    herald_id: int
    zeal: int = Field(default=50, ge=0, le=100)


class HeraldEdit(Edited):
    herald_id: int
    hold: bool = True


class HeraldTarget(Command):
    herald_id: int


class IncursionOpen(Command):
    being_id: int
    rift_id: int | None = None
    region_id: int | None = None


class IncursionEdit(Edited):
    incursion_id: int
    hold: bool = True


class IncursionTarget(Command):
    incursion_id: int


class PactStrike(Command):
    being_id: int
    holder_id: int
    price: OuterPrice = OuterPrice.SANITY


class PactEdit(Edited):
    pact_id: int
    hold: bool = True


class PactTarget(Command):
    pact_id: int


class RelationSet(Command):
    being_id: int
    other_id: int
    relation: OuterRelation = OuterRelation.RIVAL


class RelationEdit(Edited):
    being_id: int
    other_id: int
    hold: bool = True


class RelationTarget(Command):
    being_id: int
    other_id: int


class SealSet(Command):
    being_id: int
    kind: OuterSealKind = OuterSealKind.SEAL
    strength: int = Field(default=60, ge=1, le=100)
    sealer_id: int | None = None


class SealEdit(Edited):
    seal_id: int
    hold: bool = True


class SealTarget(Command):
    seal_id: int


class BeingTarget(Command):
    being_id: int


async def being_of(scope: PlayerScope, being_id: int) -> EntityRow:
    being = await living_entity(scope.session, being_id)
    if being is None or being.entity_type is not EntityType.OUTER_BEING:
        raise NotFoundError("No such outer being.")
    return being


async def row_of[Row](scope: PlayerScope, table: type[Row], key: object, missing: str) -> Row:
    row = await scope.session.get(table, key)
    if row is None:
        raise NotFoundError(missing)
    return row


@player_action("outer_plan:set", ActionKind.EDIT_RECORD)
async def plan_set(scope: PlayerScope, command: PlanSet) -> Effect:
    being = await being_of(scope, command.being_id)
    if command.target_id is not None and await scope.session.get(NodeRow, command.target_id) is None:
        raise NotFoundError("No such target for the plan.")
    ctx = await scope.context("outer_plan_set")
    for old in list(
        await ctx.session.scalars(select(OuterPlanRow).where(OuterPlanRow.outer_entity_id == being.id, OuterPlanRow.state == OuterPlanState.ACTIVE))
    ):
        old.state = OuterPlanState.THWARTED
    plan = OuterPlanRow(
        outer_entity_id=being.id, goal=command.goal, target_node_id=command.target_id, progress=command.progress, started_epoch=ctx.epoch, locked=["goal"]
    )
    ctx.session.add(plan)
    await ctx.session.flush()
    return Effect(f"{being.name} now works toward a new aim.", being.id, values={"plan_id": plan.id})


@player_action("outer_plan:edit", ActionKind.EDIT_RECORD)
async def plan_edit(scope: PlayerScope, command: PlanEdit) -> Effect:
    row = await row_of(scope, OuterPlanRow, command.plan_id, "No such plan.")
    changed = await edit_fields(row, typed(OuterPlanRow, command.values), command.hold, command.release, set(PLAN_FIELDS))
    return Effect(f"The plan: {', '.join(changed) or 'nothing'} set.", row.outer_entity_id)


@player_action("outer_plan:delete", ActionKind.EDIT_RECORD)
async def plan_delete(scope: PlayerScope, command: PlanTarget) -> Effect:
    row = await row_of(scope, OuterPlanRow, command.plan_id, "No such plan.")
    await scope.session.delete(row)
    return Effect("The plan is undone.", row.outer_entity_id)


@player_action("outer_herald:bind", ActionKind.EDIT_RECORD)
async def herald_bind(scope: PlayerScope, command: HeraldBind) -> Effect:
    being = await being_of(scope, command.being_id)
    if await scope.session.get(NodeRow, command.herald_id) is None or command.herald_id == being.id:
        raise NotFoundError("No such herald.")
    ctx = await scope.context("outer_herald_bind")
    row = await ctx.session.get(OuterHeraldRow, command.herald_id)
    if row is None:
        row = OuterHeraldRow(herald_node_id=command.herald_id, outer_entity_id=being.id, bound_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    row.outer_entity_id, row.zeal = being.id, command.zeal
    return Effect(f"A herald now serves {being.name}.", command.herald_id)


@player_action("outer_herald:edit", ActionKind.EDIT_RECORD)
async def herald_edit(scope: PlayerScope, command: HeraldEdit) -> Effect:
    row = await row_of(scope, OuterHeraldRow, command.herald_id, "No such herald.")
    changed = await edit_fields(row, typed(OuterHeraldRow, command.values), command.hold, command.release, set(HERALD_FIELDS))
    return Effect(f"The herald: {', '.join(changed) or 'nothing'} set.", row.herald_node_id)


@player_action("outer_herald:release", ActionKind.EDIT_RECORD)
async def herald_release(scope: PlayerScope, command: HeraldTarget) -> Effect:
    row = await row_of(scope, OuterHeraldRow, command.herald_id, "No such herald.")
    await scope.session.delete(row)
    return Effect("The herald is freed.", row.herald_node_id)


@player_action("outer_incursion:open", ActionKind.EDIT_RECORD)
async def incursion_open(scope: PlayerScope, command: IncursionOpen) -> Effect:
    being = await being_of(scope, command.being_id)
    rift = await scope.session.get(RiftRow, command.rift_id) if command.rift_id is not None else None
    if command.rift_id is not None and rift is None:
        raise NotFoundError("No such rift.")
    region = command.region_id if command.region_id is not None else rift.region_entity_id if rift is not None else None
    ctx = await scope.context("outer_incursion_open")
    row = await open_incursion(ctx, being, command.rift_id, region)
    return Effect(f"{being.name} presses into the cosmos.", being.id, values={"incursion_id": row.id})


@player_action("outer_incursion:edit", ActionKind.EDIT_RECORD)
async def incursion_edit(scope: PlayerScope, command: IncursionEdit) -> Effect:
    row = await row_of(scope, OuterIncursionRow, command.incursion_id, "No such incursion.")
    changed = await edit_fields(row, typed(OuterIncursionRow, command.values), command.hold, command.release, set(INCURSION_FIELDS))
    return Effect(f"The incursion: {', '.join(changed) or 'nothing'} set.", row.outer_entity_id)


@player_action("outer_incursion:end", ActionKind.EDIT_RECORD)
async def incursion_end(scope: PlayerScope, command: IncursionTarget) -> Effect:
    row = await row_of(scope, OuterIncursionRow, command.incursion_id, "No such incursion.")
    ctx = await scope.context("outer_incursion_end")
    row.stage, row.strength, row.ended_epoch = IncursionStage.RECEDING, 0, ctx.epoch
    return Effect("The incursion is driven back.", row.outer_entity_id)


@player_action("outer_pact:strike", ActionKind.EDIT_RECORD)
async def pact_strike(scope: PlayerScope, command: PactStrike) -> Effect:
    being = await being_of(scope, command.being_id)
    holder = await living_entity(scope.session, command.holder_id)
    if holder is None or holder.entity_type is EntityType.OUTER_BEING:
        raise NotFoundError("No such one to strike a bargain with.")
    ctx = await scope.context("outer_pact_strike")
    row = await strike_bargain(ctx, being, holder, command.price)
    return Effect(f"{holder.name} struck a bargain with {being.name}.", holder.id, values={"pact_id": row.id})


@player_action("outer_pact:edit", ActionKind.EDIT_RECORD)
async def pact_edit(scope: PlayerScope, command: PactEdit) -> Effect:
    row = await row_of(scope, OuterPactRow, command.pact_id, "No such bargain.")
    changed = await edit_fields(row, typed(OuterPactRow, command.values), command.hold, command.release, set(PACT_FIELDS))
    return Effect(f"The bargain: {', '.join(changed) or 'nothing'} set.", row.holder_node_id)


@player_action("outer_pact:void", ActionKind.EDIT_RECORD)
async def pact_void(scope: PlayerScope, command: PactTarget) -> Effect:
    row = await row_of(scope, OuterPactRow, command.pact_id, "No such bargain.")
    await scope.session.delete(row)
    return Effect("The bargain is voided.", row.holder_node_id)


@player_action("outer_relation:set", ActionKind.EDIT_RECORD)
async def relation_set(scope: PlayerScope, command: RelationSet) -> Effect:
    if command.being_id == command.other_id:
        raise ValidationFailedError("An outer being holds no relation to itself.")
    being = await being_of(scope, command.being_id)
    await being_of(scope, command.other_id)
    ctx = await scope.context("outer_relation_set")
    row = await ctx.session.get(OuterRelationRow, (command.being_id, command.other_id))
    if row is None:
        row = OuterRelationRow(outer_entity_id=command.being_id, other_entity_id=command.other_id, since_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    row.relation, row.locked = command.relation, sorted({*row.locked, "relation"})
    return Effect(f"{being.name} now stands toward the other as set.", being.id)


@player_action("outer_relation:edit", ActionKind.EDIT_RECORD)
async def relation_edit(scope: PlayerScope, command: RelationEdit) -> Effect:
    row = await row_of(scope, OuterRelationRow, (command.being_id, command.other_id), "No such relation.")
    changed = await edit_fields(row, typed(OuterRelationRow, command.values), command.hold, command.release, set(RELATION_FIELDS))
    return Effect(f"The relation: {', '.join(changed) or 'nothing'} set.", row.outer_entity_id)


@player_action("outer_relation:delete", ActionKind.EDIT_RECORD)
async def relation_delete(scope: PlayerScope, command: RelationTarget) -> Effect:
    row = await row_of(scope, OuterRelationRow, (command.being_id, command.other_id), "No such relation.")
    await scope.session.delete(row)
    return Effect("The relation is undone.", row.outer_entity_id)


@player_action("outer_seal:set", ActionKind.EDIT_RECORD)
async def seal_set(scope: PlayerScope, command: SealSet) -> Effect:
    being = await being_of(scope, command.being_id)
    if command.sealer_id is not None and await scope.session.get(NodeRow, command.sealer_id) is None:
        raise NotFoundError("No such sealer.")
    ctx = await scope.context("outer_seal_set")
    row = await seal_being(ctx, being, command.sealer_id, command.kind, command.strength)
    return Effect(f"{being.name} is {'banished' if command.kind is OuterSealKind.BANISH else 'sealed'}.", being.id, values={"seal_id": row.id})


@player_action("outer_seal:edit", ActionKind.EDIT_RECORD)
async def seal_edit(scope: PlayerScope, command: SealEdit) -> Effect:
    row = await row_of(scope, OuterSealRow, command.seal_id, "No such seal.")
    changed = await edit_fields(row, typed(OuterSealRow, command.values), command.hold, command.release, set(SEAL_FIELDS))
    return Effect(f"The seal: {', '.join(changed) or 'nothing'} set.", row.outer_entity_id)


@player_action("outer_seal:break", ActionKind.EDIT_RECORD)
async def seal_break(scope: PlayerScope, command: SealTarget) -> Effect:
    row = await row_of(scope, OuterSealRow, command.seal_id, "No such seal.")
    ctx = await scope.context("outer_seal_break")
    row.broken_epoch = ctx.epoch
    being = await ctx.session.get(EntityRow, row.outer_entity_id)
    if being is not None:
        profile = await outer_profile(ctx, being)
        if profile.fate in {OuterFate.SEALED, OuterFate.BANISHED}:
            profile.fate = OuterFate.ACTIVE
    return Effect("The seal is broken.", row.outer_entity_id)


@player_action("outer:destroy", ActionKind.EDIT_RECORD)
async def destroy(scope: PlayerScope, command: BeingTarget) -> Effect:
    being = await being_of(scope, command.being_id)
    ctx = await scope.context("outer_destroy")
    creator = await scope.creator()
    spent = guards.charge(creator, scope.rules.outer_beings.destroy_essence, "outer_beings.destroy_essence")
    await end_being(ctx, being, await outer_profile(ctx, being), OuterFate.DESTROYED)
    return Effect(f"The Creator destroyed {being.name}.", being.id, essence_spent=spent)
