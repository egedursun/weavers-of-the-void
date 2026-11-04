from pydantic import Field

from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.faith import BindingKind, StratumKind, TenetKind
from aerona.engine.faith import control
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class EditDoctrine(Command):
    cult_id: int
    values: dict[str, int | str | bool | None] = Field(default_factory=dict)
    release: list[str] = Field(default_factory=list)


class SetTenet(Command):
    cult_id: int
    tenet: TenetKind
    held: bool = True
    target: str | None = None
    son_id: int | None = None


class DeclareHeresy(Command):
    heresy_id: int
    parent_id: int


class JudgeHeresy(Command):
    heresy_id: int
    suppressed: bool


class Canonise(Command):
    cult_id: int
    saint_id: int
    item_id: int | None = None


class JudgeSoul(Command):
    spirit_id: int
    stratum_id: int
    reason: str = ""


class SpiritTarget(Command):
    spirit_id: int


class BindSpirit(Command):
    spirit_id: int
    target_id: int
    binding: BindingKind = BindingKind.PLACE


class SealSoul(Command):
    spirit_id: int
    sealed: bool = True


class Reincarnate(Command):
    spirit_id: int
    community_id: int | None = None


class EditSpirit(Command):
    spirit_id: int
    values: dict[str, int | str | bool | None] = Field(default_factory=dict)


class SetStratum(Command):
    realm_id: int
    kind: StratumKind
    name: str | None = None
    criteria: dict[str, int | str] | None = None
    remove: bool = False


@player_action("cult:doctrine", ActionKind.EDIT_RECORD)
async def edit_doctrine(scope: PlayerScope, command: EditDoctrine) -> Effect:
    row = await control.edit_doctrine(await scope.context("cult_doctrine"), command.cult_id, command.values, release=command.release)
    return Effect(f"The doctrine stands: orthodoxy {row.orthodoxy}, tithe {row.tithe_rate}%, judgement by {row.judgement.value}.", command.cult_id)


@player_action("cult:tenet", ActionKind.EDIT_RECORD)
async def set_tenet(scope: PlayerScope, command: SetTenet) -> Effect:
    ctx = await scope.context("cult_tenet")
    row = await control.set_tenet(ctx, command.cult_id, command.tenet, held=command.held, target=command.target, son_id=command.son_id)
    label = command.tenet.value.replace("_", " ")
    return Effect(f"The faith now holds to {label}." if row is not None else f"The faith casts off {label}.", command.cult_id)


@player_action("cult:heresy", ActionKind.OTHER)
async def declare_heresy(scope: PlayerScope, command: DeclareHeresy) -> Effect:
    row = await control.declare_heresy(await scope.context("cult_heresy"), command.heresy_id, command.parent_id)
    return Effect("The heresy is named and " + ("hunted." if row.suppressed else "tolerated."), command.heresy_id)


@player_action("cult:judge_heresy", ActionKind.EDIT_RECORD)
async def judge_heresy(scope: PlayerScope, command: JudgeHeresy) -> Effect:
    row = await control.judge_heresy(await scope.context("cult_heresy"), command.heresy_id, suppressed=command.suppressed)
    return Effect("The heresy is to be stamped out." if row.suppressed else "The heresy is to be suffered.", command.heresy_id)


@player_action("cult:canonise", ActionKind.OTHER)
async def canonise(scope: PlayerScope, command: Canonise) -> Effect:
    row = await control.canonise_saint(await scope.context("cult_saint"), command.cult_id, command.saint_id, command.item_id)
    return Effect("A saint is named; the relic draws pilgrims.", row.saint_entity_id)


@player_action("soul:judge", ActionKind.OTHER)
async def judge_soul(scope: PlayerScope, command: JudgeSoul) -> Effect:
    await control.judge_soul(await scope.context("soul_judge"), command.spirit_id, command.stratum_id, command.reason)
    return Effect("The soul is judged.", command.spirit_id)


@player_action("soul:release", ActionKind.OTHER)
async def release_soul(scope: PlayerScope, command: SpiritTarget) -> Effect:
    await control.release_soul(await scope.context("soul_release"), command.spirit_id)
    return Effect("The soul is released.", command.spirit_id)


@player_action("soul:bind", ActionKind.OTHER)
async def bind_spirit(scope: PlayerScope, command: BindSpirit) -> Effect:
    await control.bind_spirit(await scope.context("soul_bind"), command.spirit_id, command.target_id, command.binding)
    return Effect("The spirit is bound.", command.spirit_id)


@player_action("soul:seal", ActionKind.EDIT_RECORD)
async def seal_soul(scope: PlayerScope, command: SealSoul) -> Effect:
    await control.seal_soul(await scope.context("soul_seal"), command.spirit_id, sealed=command.sealed)
    return Effect("The soul is sealed against return." if command.sealed else "The seal on the soul is broken.", command.spirit_id)


@player_action("soul:reincarnate", ActionKind.OTHER)
async def reincarnate(scope: PlayerScope, command: Reincarnate) -> Effect:
    child = await control.reincarnate_soul(await scope.context("soul_reincarnate"), command.spirit_id, command.community_id)
    return Effect(f"The soul is born again as {child.name}.", child.id, created_ids=(child.id,))


@player_action("soul:edit", ActionKind.EDIT_RECORD)
async def edit_spirit(scope: PlayerScope, command: EditSpirit) -> Effect:
    row = await control.edit_spirit(await scope.context("soul_edit"), command.spirit_id, command.values)
    return Effect(f"The spirit remembers {row.memory_strength}% and is honoured {row.veneration}%.", command.spirit_id)


@player_action("afterlife:stratum", ActionKind.EDIT_RECORD)
async def set_stratum(scope: PlayerScope, command: SetStratum) -> Effect:
    ctx = await scope.context("afterlife_stratum")
    row = await control.set_stratum(ctx, command.realm_id, command.kind, name=command.name, criteria=command.criteria, remove=command.remove)
    return Effect(f"{row.name} is set." if row is not None else "The stratum is unmade.", command.realm_id)
