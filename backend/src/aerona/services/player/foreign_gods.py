from pydantic import Field

from aerona.constants.schema import TITLE_MAX_LENGTH
from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.foreign_gods import ForeignGodPowerDraft, ForeignGodRepository
from aerona.db.repositories.names import NameRepository, normalize_name
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.foreign_god import ForeignGodPowerEffect, ForeignGodStatus
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN, RELATION_MAX, RELATION_MIN
from aerona.domain.enums.son import ExistenceMode, Stat
from aerona.domain.models.profiles import ExistenceProfile, GodDepth, Personality
from aerona.engine.cosmos.foreign_gods import clean_stats, wake
from aerona.engine.primitives.renames import rewrite_name
from aerona.rules.registry import Rules
from aerona.services.player import guards
from aerona.services.player.chronicle import hand
from aerona.services.player.lines import FOREIGN_GOD_EDITED, FOREIGN_GOD_STATUS
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

PERSONALITY_FIELDS = ("appearance", "temperament", "obsession", "fear", "speech_style", "secret")
EXISTENCE_FIELDS = ("nature", "manifestation", "true_name")
DEPTH_TEXT_FIELDS = ("history", "desire", "hidden_truth", "view_of_pantheon", "worship")
DEPTH_LIST_FIELDS = ("secrets", "fears", "taboos", "gifts", "rumours")


class ForeignPower(Command):
    name: str
    effect: ForeignGodPowerEffect
    description: str = ""


class ForeignExistence(Command):
    mode: ExistenceMode | None = None
    nature: str | None = None
    manifestation: str | None = None
    true_name: str | None = None


class ForeignDepth(Command):
    history: str | None = None
    desire: str | None = None
    hidden_truth: str | None = None
    view_of_pantheon: str | None = None
    worship: str | None = None
    secrets: tuple[str, ...] | None = None
    fears: tuple[str, ...] | None = None
    taboos: tuple[str, ...] | None = None
    gifts: tuple[str, ...] | None = None
    rumours: tuple[str, ...] | None = None


class EditForeignGod(Command):
    god_id: int
    name: str | None = None
    title: str | None = None
    domain_primary: Domain | None = None
    domain_secondary: Domain | None = None
    description: str | None = None
    image_prompt: str | None = None
    stance: int | None = None
    power: int | None = None
    status: ForeignGodStatus | None = None
    contacted: bool | None = None
    stats: dict[Stat, int] = Field(default_factory=dict)
    personality: dict[str, str] = Field(default_factory=dict)
    existence: ForeignExistence | None = None
    powers: tuple[ForeignPower, ...] | None = None
    depth: ForeignDepth | None = None


async def _rename(scope: PlayerScope, god: ForeignGodRow, requested: str | None) -> list[str]:
    if requested is None or normalize_name(requested) == normalize_name(god.name):
        return []
    if not requested.strip():
        raise ValidationFailedError("A god's name cannot be empty.")
    names = NameRepository(scope.session)
    if await names.is_taken(requested, ignore_node_id=god.id):
        raise ValidationFailedError(f'"{requested}" is already used in the cosmos; choose another name.')
    old = god.name
    await names.rename(god.id, requested)
    await rewrite_name(scope.session, god.id, old, god.name)
    return ["name"]


def _identity(god: ForeignGodRow, command: EditForeignGod) -> list[str]:
    fields: list[str] = []
    if command.title is not None:
        god.title = command.title.strip()[:TITLE_MAX_LENGTH] or None
        fields.append("title")
    if command.domain_primary is not None:
        god.domain_primary = command.domain_primary
        fields.append("domain")
    if command.domain_secondary is not None:
        god.domain_secondary = command.domain_secondary if command.domain_secondary is not god.domain_primary else None
        fields.append("second domain")
    for name in ("description", "image_prompt"):
        value = getattr(command, name)
        if value is not None:
            setattr(god, name, value.strip() or None)
            fields.append(name.replace("_", " "))
    return fields


def _numbers(god: ForeignGodRow, command: EditForeignGod, rules: Rules) -> list[str]:
    fields: list[str] = []
    if command.stance is not None:
        god.stance = max(RELATION_MIN, min(RELATION_MAX, command.stance))
        fields.append("attitude")
    if command.power is not None:
        god.power = max(PERCENT_MIN, min(PERCENT_MAX, command.power))
        fields.append("power")
    if command.contacted is not None:
        god.contacted = command.contacted
        fields.append("contact")
    if command.stats:
        god.apply_stats(clean_stats({item.value: value for item, value in command.stats.items()}, god.stat_block, rules))
        fields.extend(item.value for item in command.stats)
    return fields


async def _nature(scope: PlayerScope, god: ForeignGodRow, command: EditForeignGod) -> list[str]:
    fields: list[str] = []
    if command.personality:
        unknown = sorted(set(command.personality) - set(PERSONALITY_FIELDS))
        if unknown:
            raise ValidationFailedError(f"Unknown personality fields: {', '.join(unknown)}. Must be one of: {', '.join(PERSONALITY_FIELDS)}.")
        god.personality = (god.personality or Personality()).model_copy(update={key: value.strip() for key, value in command.personality.items()})
        fields.append("personality")
    if command.existence is not None:
        existence = command.existence
        updates: dict[str, object] = {key: getattr(existence, key).strip() for key in EXISTENCE_FIELDS if getattr(existence, key) is not None}
        if existence.mode is not None:
            updates["mode"] = existence.mode
        god.existence_profile = (god.existence_profile or ExistenceProfile()).model_copy(update=updates)
        fields.append("existence")
    if command.powers is not None:
        drafts = [ForeignGodPowerDraft(power.name.strip(), power.effect, power.description.strip()) for power in command.powers]
        await ForeignGodRepository(scope.session).set_powers(god.id, drafts)
        fields.append("powers")
    return fields


def _depth(god: ForeignGodRow, depth: ForeignDepth | None, epoch: int) -> list[str]:
    if depth is None:
        return []
    updates: dict[str, object] = {}
    for key in DEPTH_TEXT_FIELDS:
        value = getattr(depth, key)
        if value is not None:
            updates[key] = value.strip()
    for key in DEPTH_LIST_FIELDS:
        items = getattr(depth, key)
        if items is not None:
            updates[key] = tuple(item.strip() for item in items if item.strip())
    if not updates:
        return []
    god.depth = (god.depth or GodDepth(epoch=epoch)).model_copy(update=updates)
    return ["depth"]


def _status(god: ForeignGodRow, status: ForeignGodStatus, epoch: int) -> None:
    if status is ForeignGodStatus.AWAKE:
        wake(god)
        god.defeated_epoch = None
        god.death_epoch = None
        return
    god.status = status
    if status is ForeignGodStatus.DEAD:
        god.awakening_pressure = 0
    god.death_epoch = epoch if status is ForeignGodStatus.DEAD else None
    if status is ForeignGodStatus.DEFEATED:
        god.defeated_epoch = epoch


@player_action("foreign_god:edit", ActionKind.EDIT_RECORD)
async def edit_foreign_god(scope: PlayerScope, command: EditForeignGod) -> Effect:
    god = await guards.foreign_god(scope.session, command.god_id)
    creator = await scope.creator()
    ctx = await scope.context("edit_foreign_god")
    fields = await _rename(scope, god, command.name) + _identity(god, command) + _numbers(god, command, scope.rules) + await _nature(scope, god, command)
    fields += _depth(god, command.depth, ctx.epoch)
    messages: list[str] = []
    if command.status is not None and command.status is not god.status:
        _status(god, command.status, ctx.epoch)
        line = FOREIGN_GOD_STATUS
        messages.append(await hand(ctx, creator, line, world_id=god.world_id, kind=ChronicleKind.FOREIGN_GOD, god=god.name, status=command.status.value))
    if not fields and not messages:
        raise ValidationFailedError(f"Nothing to change on {god.name}.")
    if fields:
        line = FOREIGN_GOD_EDITED
        messages.append(await hand(ctx, creator, line, world_id=god.world_id, kind=ChronicleKind.FOREIGN_GOD, god=god.name, fields=", ".join(fields)))
    return Effect(" ".join(messages), god.id)
