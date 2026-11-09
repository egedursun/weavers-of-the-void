from sqlalchemy import select

from aerona.agents.celestial_deepener import SCALE_DEPTH_KINDS, scale_row
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.models.profiles import EntityDepth, Saying
from aerona.services.player.chronicle import hand
from aerona.services.player.lines import CELESTIAL_DEPTH_EDITED
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class SayingInput(Command):
    form: str
    text: str


class DepthEdit(Command):
    history: str | None = None
    rumours: list[str] | None = None
    sayings: list[SayingInput] | None = None
    details: list[str] | None = None
    hidden_truth: str | None = None
    specifics: dict[str, str] | None = None


class WorldDepth(DepthEdit):
    world_id: int


class StarDepth(DepthEdit):
    star_id: int


def _cleaned(items: list[str]) -> tuple[str, ...]:
    return tuple(item.strip() for item in items if item.strip())


def edited_depth(current: EntityDepth | None, command: DepthEdit, epoch: int) -> tuple[EntityDepth, list[str]]:
    updates: dict[str, object] = {}
    if command.history is not None:
        updates["history"] = command.history.strip()
    if command.rumours is not None:
        updates["rumours"] = _cleaned(command.rumours)
    if command.details is not None:
        updates["details"] = _cleaned(command.details)
    if command.sayings is not None:
        updates["sayings"] = tuple(Saying(form=item.form.strip(), text=item.text.strip()) for item in command.sayings if item.text.strip())
    if command.hidden_truth is not None:
        updates["hidden_truth"] = command.hidden_truth.strip()
    if command.specifics is not None:
        updates["specifics"] = {key.strip(): value.strip() for key, value in command.specifics.items() if key.strip() and value.strip()}
    if not updates:
        raise ValidationFailedError("Change at least one part of the depth.")
    base = current or EntityDepth(epoch=epoch)
    return base.model_copy(update=updates), sorted(updates)


@player_action("world:depth", ActionKind.EDIT_RECORD)
async def edit_world_depth(scope: PlayerScope, command: WorldDepth) -> Effect:
    world = await scope.session.get(WorldRow, command.world_id)
    if world is None:
        raise NotFoundError("No such world.")
    world.depth, fields = edited_depth(world.depth, command, await scope.epoch())
    message = await hand(await scope.context("world_depth"), await scope.creator(), CELESTIAL_DEPTH_EDITED, name=world.name, fields=", ".join(fields))
    return Effect(message, values={"world_id": world.id})


@player_action("star:depth", ActionKind.EDIT_RECORD)
async def edit_star_depth(scope: PlayerScope, command: StarDepth) -> Effect:
    star = await scope.session.get(StarRow, command.star_id)
    if star is None:
        raise NotFoundError("No such star.")
    star.depth, fields = edited_depth(star.depth, command, await scope.epoch())
    message = await hand(await scope.context("star_depth"), await scope.creator(), CELESTIAL_DEPTH_EDITED, name=star.name, fields=", ".join(fields))
    return Effect(message, values={"star_id": star.id})


class ScaleDepth(DepthEdit):
    node_id: int


@player_action("scale:depth", ActionKind.EDIT_RECORD)
async def edit_scale_depth(scope: PlayerScope, command: ScaleDepth) -> Effect:
    kind = await scope.session.scalar(select(NodeRow.kind).where(NodeRow.id == command.node_id))
    node = await scale_row(scope.session, SCALE_DEPTH_KINDS[kind], command.node_id) if kind in SCALE_DEPTH_KINDS else None
    if node is None:
        raise NotFoundError("No such galaxy, cluster or dimension.")
    node.depth, fields = edited_depth(node.depth, command, await scope.epoch())
    message = await hand(await scope.context("scale_depth"), await scope.creator(), CELESTIAL_DEPTH_EDITED, name=node.name, fields=", ".join(fields))
    return Effect(message, values={"node_id": node.id})
