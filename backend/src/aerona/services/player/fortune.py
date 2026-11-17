from pydantic import Field

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import spoken
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.folkways import MishapRow
from aerona.db.tables.fortune import FortuneLawRow, FortuneSourceRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.folkways import MishapKind
from aerona.domain.enums.fortune import FortuneLaw, FortuneSourceKind
from aerona.engine.fortune.everyday import trigger
from aerona.engine.fortune.profiles import profile_of
from aerona.engine.powers.control import edit_fields
from aerona.services.player.cosmography import Edited
from aerona.services.player.powers import typed
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

CAP = 100
PROFILE_FIELDS = {"fortune", "streak"}
SOURCE_FIELDS = {"kind", "strength", "giver_node_id", "until_epoch"}


class FortuneEdit(Edited):
    node_id: int
    hold: bool = True


class SourceCreate(Command):
    holder_id: int
    kind: FortuneSourceKind = FortuneSourceKind.BLESSING
    strength: int = Field(default=10, ge=-CAP, le=CAP)
    giver_id: int | None = None
    epochs: int | None = Field(default=None, ge=0, le=10000)


class SourceTarget(Command):
    source_id: int


class SourceEdit(Edited):
    source_id: int
    hold: bool = False


class LawSet(Command):
    world_id: int
    law: FortuneLaw = FortuneLaw.PERSONAL


class MishapTrigger(Command):
    victim_id: int
    kind: MishapKind = MishapKind.FALL
    level: int = Field(default=1, ge=1, le=3)


async def source_of(scope: PlayerScope, source_id: int) -> FortuneSourceRow:
    row = await (await scope.context("fortune_source")).session.get(FortuneSourceRow, source_id)
    if row is None:
        raise NotFoundError("No such source of fortune.")
    return row


@player_action("fortune:edit", ActionKind.EDIT_RECORD)
async def fortune_edit(scope: PlayerScope, command: FortuneEdit) -> Effect:
    ctx = await scope.context("fortune_edit")
    row = await profile_of(ctx, command.node_id)
    changed = await edit_fields(row, typed(type(row), command.values), command.hold, command.release, PROFILE_FIELDS)
    return Effect(f"Its fortune: {', '.join(changed) or 'nothing'} set.", command.node_id)


@player_action("fortune_source:create", ActionKind.EDIT_RECORD)
async def source_create(scope: PlayerScope, command: SourceCreate) -> Effect:
    ctx = await scope.context("fortune_source_create")
    if await ctx.session.get(EntityRow, command.holder_id) is None and await ctx.session.get(WorldRow, command.holder_id) is None:
        raise NotFoundError("There is no one there to give fortune to.")
    row = FortuneSourceRow(
        holder_node_id=command.holder_id,
        kind=command.kind,
        strength=command.strength,
        giver_node_id=command.giver_id,
        until_epoch=ctx.epoch + command.epochs if command.epochs is not None else None,
        since_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return Effect("Fortune turns for it.", command.holder_id, values={"source_id": row.id})


@player_action("fortune_source:edit", ActionKind.EDIT_RECORD)
async def source_edit(scope: PlayerScope, command: SourceEdit) -> Effect:
    row = await source_of(scope, command.source_id)
    changed = await edit_fields(row, typed(type(row), command.values), command.hold, command.release, SOURCE_FIELDS)
    return Effect(f"The source of fortune: {', '.join(changed) or 'nothing'} set.", row.holder_node_id)


@player_action("fortune_source:delete", ActionKind.EDIT_RECORD)
async def source_delete(scope: PlayerScope, command: SourceTarget) -> Effect:
    ctx = await scope.context("fortune_source_delete")
    row = await source_of(scope, command.source_id)
    await ctx.session.delete(row)
    return Effect("The source of fortune is gone.", row.holder_node_id)


@player_action("fortune_law:set", ActionKind.EDIT_RECORD)
async def law_set(scope: PlayerScope, command: LawSet) -> Effect:
    ctx = await scope.context("fortune_law_set")
    if await ctx.session.get(WorldRow, command.world_id) is None:
        raise NotFoundError("No such world.")
    row = await ctx.session.get(FortuneLawRow, command.world_id)
    if row is None:
        row = FortuneLawRow(world_id=command.world_id, law=command.law, locked=[])
        ctx.session.add(row)
    row.law = command.law
    await ctx.session.flush()
    return Effect(f"Fortune in this world now runs by {spoken(command.law)}.", command.world_id)


@player_action("mishap:trigger", ActionKind.EDIT_RECORD)
async def mishap_trigger(scope: PlayerScope, command: MishapTrigger) -> Effect:
    ctx = await scope.context("mishap_trigger")
    victim = await ctx.session.get(EntityRow, command.victim_id)
    if victim is None or victim.status is not EntityStatus.CANON:
        raise NotFoundError("There is no one there for a mishap to befall.")
    town = victim.location_id if victim.entity_type is not EntityType.SETTLEMENT else victim.id
    if town is None:
        raise ValidationFailedError("A mishap needs a place to befall in.")
    happened = await trigger(ctx, victim, command.kind, command.level)
    row = MishapRow(
        settlement_entity_id=town,
        victim_node_id=victim.id,
        kind=command.kind,
        true_cause=happened.cause,
        explained=False,
        severity=happened.severity,
        died=happened.died,
        witnesses=[],
        epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return Effect(f"A mishap befell {victim.name}.", victim.id, values={"mishap_id": row.id})
