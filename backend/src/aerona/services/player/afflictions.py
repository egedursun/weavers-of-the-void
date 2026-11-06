from pydantic import Field

from aerona.catalog.effect_packages import PACKAGES
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.afflictions import AfflictionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.affliction import CureKind, PackageKind, Transmission
from aerona.engine.body.afflictions import STAGE_HOLD, active, afflict, bearable, cure, enter_stage, revert, spec_of
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class GiveAffliction(Command):
    bearer_id: int
    package: PackageKind
    transmission: Transmission
    source_id: int | None = None
    stage: int | None = Field(default=None, ge=0)


class AfflictionTarget(Command):
    affliction_id: int


class EditAffliction(AfflictionTarget):
    stage: int | None = Field(default=None, ge=0)
    transmission: Transmission | None = None
    source_id: int | None = None
    clear_source: bool = False
    since_epoch: int | None = Field(default=None, ge=0)
    stage_since_epoch: int | None = Field(default=None, ge=0)


class HoldAffliction(AfflictionTarget):
    hold: bool = True


class CureAffliction(AfflictionTarget):
    how: CureKind | None = None


async def bearer_of(scope: PlayerScope, node_id: int) -> EntityRow:
    found = await scope.session.get(EntityRow, node_id)
    if found is None:
        raise NotFoundError("No such bearer.")
    if not bearable(found):
        raise ValidationFailedError(f"{found.name} cannot bear an affliction.")
    return found


async def affliction_of(scope: PlayerScope, affliction_id: int) -> AfflictionRow:
    row = await scope.session.get(AfflictionRow, affliction_id)
    if row is None:
        raise NotFoundError("No such affliction.")
    return row


async def source_of(scope: PlayerScope, node_id: int | None) -> int | None:
    if node_id is None:
        return None
    if await scope.session.get(NodeRow, node_id) is None:
        raise NotFoundError("No such source.")
    return node_id


def checked_stage(package: PackageKind, stage: int) -> int:
    count = len(PACKAGES[package].stages)
    if stage > count:
        raise ValidationFailedError(f"{PACKAGES[package].label} has only {count} stages.")
    return stage


@player_action("affliction:give", ActionKind.OTHER)
async def give(scope: PlayerScope, command: GiveAffliction) -> Effect:
    bearer = await bearer_of(scope, command.bearer_id)
    if any(row.package is command.package for row in await active(scope.session, bearer.id)):
        raise ValidationFailedError(f"{bearer.name} already bears {PACKAGES[command.package].label.lower()}.")
    ctx = await scope.context("affliction_give")
    row = await afflict(ctx, bearer, command.package, command.transmission, source_node_id=await source_of(scope, command.source_id))
    if row is None:
        raise ValidationFailedError(f"{bearer.name} is shielded from afflictions.")
    if command.stage is not None and command.stage != row.stage:
        await enter_stage(ctx, bearer, row, checked_stage(row.package, command.stage))
    return Effect(f"{bearer.name} now bears {spec_of(row).label.lower()}.", target_node_id=bearer.id, values={"affliction_id": row.id})


@player_action("affliction:edit", ActionKind.OTHER)
async def edit(scope: PlayerScope, command: EditAffliction) -> Effect:
    row = await affliction_of(scope, command.affliction_id)
    bearer = await bearer_of(scope, row.bearer_node_id)
    ctx = await scope.context("affliction_edit")
    if command.transmission is not None:
        row.transmission = command.transmission
    if command.clear_source:
        row.source_node_id = None
    elif command.source_id is not None:
        row.source_node_id = await source_of(scope, command.source_id)
    if command.since_epoch is not None:
        row.since_epoch = command.since_epoch
    if command.stage is not None and command.stage != row.stage:
        if row.cured_epoch is not None:
            raise ValidationFailedError("A cured affliction has no stage to move; give it again instead.")
        await enter_stage(ctx, bearer, row, checked_stage(row.package, command.stage))
    if command.stage_since_epoch is not None:
        row.stage_since_epoch = command.stage_since_epoch
    return Effect(f"{bearer.name}'s {spec_of(row).label.lower()} was reshaped.", target_node_id=bearer.id)


@player_action("affliction:hold", ActionKind.OTHER)
async def hold(scope: PlayerScope, command: HoldAffliction) -> Effect:
    row = await affliction_of(scope, command.affliction_id)
    bearer = await bearer_of(scope, row.bearer_node_id)
    locked = set(row.locked)
    if command.hold:
        locked.add(STAGE_HOLD)
    else:
        locked.discard(STAGE_HOLD)
    row.locked = sorted(locked)
    verb = "is held at its stage" if command.hold else "runs its course again"
    return Effect(f"{bearer.name}'s {spec_of(row).label.lower()} {verb}.", target_node_id=bearer.id)


@player_action("affliction:cure", ActionKind.OTHER)
async def cure_action(scope: PlayerScope, command: CureAffliction) -> Effect:
    row = await affliction_of(scope, command.affliction_id)
    if row.cured_epoch is not None:
        raise ValidationFailedError("That affliction is already cured.")
    bearer = await bearer_of(scope, row.bearer_node_id)
    await cure(await scope.context("affliction_cure"), bearer, row, command.how)
    return Effect(f"{bearer.name} is freed of {spec_of(row).label.lower()}.", target_node_id=bearer.id)


@player_action("affliction:delete", ActionKind.OTHER)
async def delete(scope: PlayerScope, command: AfflictionTarget) -> Effect:
    row = await affliction_of(scope, command.affliction_id)
    bearer = await scope.session.get(EntityRow, row.bearer_node_id)
    label = spec_of(row).label.lower()
    if bearer is not None and row.cured_epoch is None:
        await revert(await scope.context("affliction_delete"), bearer, row)
    await scope.session.delete(row)
    await scope.session.flush()
    name = bearer.name if bearer is not None else "The bearer"
    return Effect(f"{name}'s {label} was unmade, as if it never was.", target_node_id=row.bearer_node_id)
