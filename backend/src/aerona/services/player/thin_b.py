from pydantic import BaseModel, Field

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import several
from aerona.db.tables.belief_depth import SOURCE_TRUST_FIELDS, SourceTrustRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmography import RiftRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.rift_control import RIFT_CONTROL_FIELDS, RiftControlRow
from aerona.db.tables.storyteller import StorytellerRow
from aerona.db.tables.storyteller_depth import REGION_TENSION_FIELDS, SUBSYSTEM_TENSION_FIELDS, RegionalTensionRow, SubsystemTensionRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.cosmography import RiftWork
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.intrigue import BeliefSource
from aerona.engine.powers.control import edit_fields
from aerona.services.player.cosmography import Edited
from aerona.services.player.powers import typed
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

SPAN = 100
EPOCH_SPAN = 100000


class TargetPoint(BaseModel):
    epoch: int = Field(ge=0, le=EPOCH_SPAN)
    target: int = Field(ge=0, le=SPAN)


class TargetPoints(Command):
    world_id: int
    points: list[TargetPoint] = Field(default_factory=list, max_length=64)


class RegionTensionSet(Command):
    region_id: int
    tension: int = Field(ge=0, le=SPAN)
    hold: bool = True


class RegionTensionEdit(Edited):
    region_id: int
    hold: bool = True


class RegionTarget(Command):
    region_id: int


class SubsystemTensionEdit(Edited):
    world_id: int
    subsystem: str = Field(min_length=1, max_length=64)
    hold: bool = True


class SubsystemTarget(Command):
    world_id: int
    subsystem: str = Field(min_length=1, max_length=64)


class TrustSet(Command):
    holder_id: int
    source: BeliefSource
    trust: int = Field(ge=0, le=SPAN)
    hold: bool = True


class TrustEdit(Edited):
    holder_id: int
    source: BeliefSource
    hold: bool = True


class TrustTarget(Command):
    holder_id: int
    source: BeliefSource


class RiftControlSet(Command):
    rift_id: int
    work: RiftWork = RiftWork.NONE
    claimant_id: int | None = None
    toll: int = Field(default=0, ge=0, le=EPOCH_SPAN)


class RiftControlEdit(Edited):
    rift_id: int
    hold: bool = True


class RiftTarget(Command):
    rift_id: int


async def world_of(scope: PlayerScope, world_id: int) -> WorldRow:
    world = await scope.session.get(WorldRow, world_id)
    if world is None:
        raise NotFoundError("No such world.")
    return world


@player_action("storyteller_points:set", ActionKind.EDIT_RECORD)
async def points_set(scope: PlayerScope, command: TargetPoints) -> Effect:
    world = await world_of(scope, command.world_id)
    row = await scope.session.get(StorytellerRow, world.id)
    if row is None:
        row = StorytellerRow(world_id=world.id, recent_kinds={}, locked=[])
        scope.session.add(row)
    row.target_points = [[point.epoch, point.target] for point in sorted(command.points, key=lambda point: point.epoch)]
    told = f"follows {several(len(row.target_points), 'set point', 'set points')} of tension" if row.target_points else "follows its profile again"
    return Effect(f"The storyteller of {world.name} {told}.", world.id)


async def region_of(scope: PlayerScope, region_id: int) -> EntityRow:
    region = await scope.session.get(EntityRow, region_id)
    if region is None or region.entity_type is not EntityType.REGION:
        raise NotFoundError("No such region.")
    return region


@player_action("regional_tension:set", ActionKind.EDIT_RECORD)
async def region_tension_set(scope: PlayerScope, command: RegionTensionSet) -> Effect:
    region = await region_of(scope, command.region_id)
    row = await scope.session.get(RegionalTensionRow, region.id)
    if row is None:
        row = RegionalTensionRow(region_entity_id=region.id, world_id=region.world_id, locked=[])
        scope.session.add(row)
    await edit_fields(row, {"tension": command.tension}, command.hold, [], set(REGION_TENSION_FIELDS))
    return Effect(f"The tension of {region.name} is set to {command.tension}.", region.id)


async def regional(scope: PlayerScope, region_id: int) -> RegionalTensionRow:
    row = await scope.session.get(RegionalTensionRow, region_id)
    if row is None:
        raise NotFoundError("No tension is measured for that region.")
    return row


@player_action("regional_tension:edit", ActionKind.EDIT_RECORD)
async def region_tension_edit(scope: PlayerScope, command: RegionTensionEdit) -> Effect:
    row = await regional(scope, command.region_id)
    changed = await edit_fields(row, typed(type(row), command.values), command.hold, command.release, set(REGION_TENSION_FIELDS))
    return Effect(f"The region's tension: {', '.join(changed) or 'nothing'} set.", row.region_entity_id)


@player_action("regional_tension:delete", ActionKind.EDIT_RECORD)
async def region_tension_delete(scope: PlayerScope, command: RegionTarget) -> Effect:
    row = await regional(scope, command.region_id)
    await scope.session.delete(row)
    return Effect("The region's tension is measured afresh.", row.region_entity_id)


async def subsystem_of(scope: PlayerScope, world_id: int, subsystem: str) -> SubsystemTensionRow:
    row = await scope.session.get(SubsystemTensionRow, (world_id, subsystem))
    if row is None:
        raise NotFoundError("No tension is measured for that part of the world.")
    return row


@player_action("subsystem_tension:edit", ActionKind.EDIT_RECORD)
async def subsystem_tension_edit(scope: PlayerScope, command: SubsystemTensionEdit) -> Effect:
    await world_of(scope, command.world_id)
    row = await scope.session.get(SubsystemTensionRow, (command.world_id, command.subsystem))
    if row is None:
        row = SubsystemTensionRow(world_id=command.world_id, subsystem=command.subsystem, locked=[])
        scope.session.add(row)
    changed = await edit_fields(row, typed(type(row), command.values), command.hold, command.release, set(SUBSYSTEM_TENSION_FIELDS))
    return Effect(f"The tension of {command.subsystem.replace('_', ' ')}: {', '.join(changed) or 'nothing'} set.", command.world_id)


@player_action("subsystem_tension:delete", ActionKind.EDIT_RECORD)
async def subsystem_tension_delete(scope: PlayerScope, command: SubsystemTarget) -> Effect:
    row = await subsystem_of(scope, command.world_id, command.subsystem)
    await scope.session.delete(row)
    return Effect("That part of the world is measured afresh.", command.world_id)


async def holder_of(scope: PlayerScope, holder_id: int) -> NodeRow:
    node = await scope.session.get(NodeRow, holder_id)
    if node is None:
        raise NotFoundError("No such thing.")
    return node


@player_action("source_trust:set", ActionKind.EDIT_RECORD)
async def trust_set(scope: PlayerScope, command: TrustSet) -> Effect:
    holder = await holder_of(scope, command.holder_id)
    row = await scope.session.get(SourceTrustRow, (holder.id, command.source))
    if row is None:
        row = SourceTrustRow(holder_node_id=holder.id, source=command.source, locked=[])
        scope.session.add(row)
    await edit_fields(row, {"trust": command.trust}, command.hold, [], set(SOURCE_TRUST_FIELDS))
    return Effect(f"{holder.name} trusts {command.source.value.replace('_', ' ')} at {command.trust}.", holder.id)


async def trust_of(scope: PlayerScope, holder_id: int, source: BeliefSource) -> SourceTrustRow:
    row = await scope.session.get(SourceTrustRow, (holder_id, source))
    if row is None:
        raise NotFoundError("No trust is kept for that source.")
    return row


@player_action("source_trust:edit", ActionKind.EDIT_RECORD)
async def trust_edit(scope: PlayerScope, command: TrustEdit) -> Effect:
    row = await trust_of(scope, command.holder_id, command.source)
    changed = await edit_fields(row, typed(type(row), command.values), command.hold, command.release, set(SOURCE_TRUST_FIELDS))
    return Effect(f"Trust in {command.source.value.replace('_', ' ')}: {', '.join(changed) or 'nothing'} set.", command.holder_id)


@player_action("source_trust:delete", ActionKind.EDIT_RECORD)
async def trust_delete(scope: PlayerScope, command: TrustTarget) -> Effect:
    row = await trust_of(scope, command.holder_id, command.source)
    await scope.session.delete(row)
    return Effect("Trust in that source starts afresh.", command.holder_id)


async def rift_of(scope: PlayerScope, rift_id: int) -> RiftRow:
    rift = await scope.session.get(RiftRow, rift_id)
    if rift is None:
        raise NotFoundError("No such rift.")
    return rift


@player_action("rift_control:set", ActionKind.EDIT_RECORD)
async def rift_control_set(scope: PlayerScope, command: RiftControlSet) -> Effect:
    rift = await rift_of(scope, command.rift_id)
    if command.claimant_id is not None:
        claimant = await scope.session.get(EntityRow, command.claimant_id)
        if claimant is None or claimant.entity_type is not EntityType.POLITY:
            raise ValidationFailedError("Only a realm can claim a rift.")
    row = await scope.session.get(RiftControlRow, rift.id)
    if row is None:
        row = RiftControlRow(rift_id=rift.id, locked=[])
        scope.session.add(row)
    values = {"work": command.work, "toll": command.toll, "claimant_entity_id": command.claimant_id}
    await edit_fields(row, values, True, [], set(RIFT_CONTROL_FIELDS))
    row.claimed_epoch = await scope.epoch() if command.claimant_id is not None else row.claimed_epoch
    return Effect(f"The rift is held to {command.work.value.replace('_', ' ')}.", rift.region_entity_id)


async def control_of(scope: PlayerScope, rift_id: int) -> RiftControlRow:
    row = await scope.session.get(RiftControlRow, rift_id)
    if row is None:
        raise NotFoundError("No one holds that rift.")
    return row


@player_action("rift_control:edit", ActionKind.EDIT_RECORD)
async def rift_control_edit(scope: PlayerScope, command: RiftControlEdit) -> Effect:
    row = await control_of(scope, command.rift_id)
    changed = await edit_fields(row, typed(type(row), command.values), command.hold, command.release, set(RIFT_CONTROL_FIELDS))
    return Effect(f"The hold on the rift: {', '.join(changed) or 'nothing'} set.")


@player_action("rift_control:delete", ActionKind.EDIT_RECORD)
async def rift_control_delete(scope: PlayerScope, command: RiftTarget) -> Effect:
    row = await control_of(scope, command.rift_id)
    await scope.session.delete(row)
    return Effect("The rift is held by no one.")
