from typing import Any

from pydantic import Field

from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.faith import BindingKind, ClergyOffice, HoldingKind, SpiritAlignment, StratumKind, TenetKind
from aerona.domain.models.faith import StratumCriteria
from aerona.engine.faith import control
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class EditDoctrine(Command):
    cult_id: int
    values: dict[str, Any] = Field(default_factory=dict)
    release: list[str] = Field(default_factory=list)


class CultTarget(Command):
    cult_id: int


class SetTenet(Command):
    cult_id: int
    tenet: TenetKind
    held: bool = True
    target: str | None = None
    son_id: int | None = None
    name: str | None = None


class SetOffice(Command):
    cult_id: int
    kind: ClergyOffice
    holder_id: int | None = None
    locked: bool | None = None
    remove: bool = False


class SetHolding(Command):
    cult_id: int
    entity_id: int
    kind: HoldingKind = HoldingKind.LAND
    remove: bool = False


class DeclareHeresy(Command):
    heresy_id: int
    parent_id: int


class JudgeHeresy(Command):
    heresy_id: int
    suppressed: bool


class EditHeresy(Command):
    heresy_id: int
    values: dict[str, Any] = Field(default_factory=dict)
    release: list[str] = Field(default_factory=list)


class HeresyTarget(Command):
    heresy_id: int


class Canonise(Command):
    cult_id: int
    saint_id: int
    item_id: int | None = None


class EditRelic(Command):
    item_id: int
    values: dict[str, Any] = Field(default_factory=dict)
    release: list[str] = Field(default_factory=list)


class RelicTarget(Command):
    item_id: int


class RaiseSoul(Command):
    mortal_id: int
    alignment: SpiritAlignment = SpiritAlignment.NEUTRAL
    place_id: int | None = None


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
    strength: int | None = Field(default=None, ge=0, le=100)


class Reincarnate(Command):
    spirit_id: int
    community_id: int | None = None


class EditSpirit(Command):
    spirit_id: int
    values: dict[str, Any] = Field(default_factory=dict)
    release: list[str] = Field(default_factory=list)


class Possess(Command):
    spirit_id: int
    host_id: int


class EditPossession(Command):
    host_id: int
    values: dict[str, Any] = Field(default_factory=dict)
    release: list[str] = Field(default_factory=list)


class HostTarget(Command):
    host_id: int


class SetStratum(Command):
    realm_id: int
    kind: StratumKind
    stratum_id: int | None = None
    name: str | None = None
    criteria: StratumCriteria | None = None
    son_id: int | None = None
    cult_id: int | None = None
    closed: bool | None = None
    clear_links: bool = False
    remove: bool = False


@player_action("cult:doctrine", ActionKind.EDIT_RECORD)
async def edit_doctrine(scope: PlayerScope, command: EditDoctrine) -> Effect:
    row = await control.edit_doctrine(await scope.context("cult_doctrine"), command.cult_id, command.values, release=command.release)
    return Effect(f"The doctrine stands: orthodoxy {row.orthodoxy}, tithe {row.tithe_rate}%, judgement by {row.judgement.value}.", command.cult_id)


@player_action("cult:reset_doctrine", ActionKind.EDIT_RECORD)
async def reset_doctrine(scope: PlayerScope, command: CultTarget) -> Effect:
    row = await control.reset_doctrine(await scope.context("cult_doctrine"), command.cult_id)
    return Effect(f"The doctrine is unwritten and taught anew: judgement by {row.judgement.value}.", command.cult_id)


@player_action("cult:tenet", ActionKind.EDIT_RECORD)
async def set_tenet(scope: PlayerScope, command: SetTenet) -> Effect:
    ctx = await scope.context("cult_tenet")
    row = await control.set_tenet(ctx, command.cult_id, command.tenet, held=command.held, target=command.target, son_id=command.son_id, name=command.name)
    label = (row.name if row is not None and row.name else None) or command.tenet.value.replace("_", " ")
    return Effect(f"The faith now holds to {label}." if row is not None else f"The faith casts off {label}.", command.cult_id)


@player_action("cult:office", ActionKind.EDIT_RECORD)
async def set_office(scope: PlayerScope, command: SetOffice) -> Effect:
    ctx = await scope.context("cult_office")
    row = await control.set_office(ctx, command.cult_id, command.kind, holder_id=command.holder_id, locked=command.locked, remove=command.remove)
    label = command.kind.value.replace("_", " ")
    return Effect(f"The office of {label} is struck." if row is None else f"The office of {label} is set.", command.cult_id)


@player_action("cult:holding", ActionKind.EDIT_RECORD)
async def set_holding(scope: PlayerScope, command: SetHolding) -> Effect:
    row = await control.set_holding(await scope.context("cult_holding"), command.cult_id, command.entity_id, command.kind, remove=command.remove)
    return Effect("The holding is given up." if row is None else f"The faith now holds it as {command.kind.value.replace('_', ' ')}.", command.cult_id)


@player_action("cult:heresy", ActionKind.OTHER)
async def declare_heresy(scope: PlayerScope, command: DeclareHeresy) -> Effect:
    row = await control.declare_heresy(await scope.context("cult_heresy"), command.heresy_id, command.parent_id)
    return Effect("The heresy is named and " + ("hunted." if row.suppressed else "tolerated."), command.heresy_id)


@player_action("cult:judge_heresy", ActionKind.EDIT_RECORD)
async def judge_heresy(scope: PlayerScope, command: JudgeHeresy) -> Effect:
    row = await control.judge_heresy(await scope.context("cult_heresy"), command.heresy_id, suppressed=command.suppressed)
    return Effect("The heresy is to be stamped out." if row.suppressed else "The heresy is to be suffered.", command.heresy_id)


@player_action("cult:edit_heresy", ActionKind.EDIT_RECORD)
async def edit_heresy(scope: PlayerScope, command: EditHeresy) -> Effect:
    row = await control.edit_heresy(await scope.context("cult_heresy"), command.heresy_id, command.values, release=command.release)
    return Effect(f"The heresy stands {row.distance} from its mother church.", command.heresy_id)


@player_action("cult:undeclare_heresy", ActionKind.OTHER)
async def undeclare_heresy(scope: PlayerScope, command: HeresyTarget) -> Effect:
    parent = await control.undeclare_heresy(await scope.context("cult_heresy"), command.heresy_id)
    return Effect("The heresy is forgiven; it is no longer named.", parent)


@player_action("cult:canonise", ActionKind.OTHER)
async def canonise(scope: PlayerScope, command: Canonise) -> Effect:
    row = await control.canonise_saint(await scope.context("cult_saint"), command.cult_id, command.saint_id, command.item_id)
    return Effect("A saint is named; the relic draws pilgrims.", row.saint_entity_id, created_ids=(row.item_entity_id,))


@player_action("relic:edit", ActionKind.EDIT_RECORD)
async def edit_relic(scope: PlayerScope, command: EditRelic) -> Effect:
    row = await control.edit_relic(await scope.context("relic_edit"), command.item_id, command.values, release=command.release)
    return Effect(f"The relic is holy {row.sanctity} and draws {row.pilgrims} pilgrims.", command.item_id)


@player_action("relic:remove", ActionKind.OTHER)
async def remove_relic(scope: PlayerScope, command: RelicTarget) -> Effect:
    cult = await control.remove_relic(await scope.context("relic_remove"), command.item_id)
    return Effect("The relic is no longer holy.", cult or command.item_id)


@player_action("soul:raise", ActionKind.CREATE_ENTITY)
async def raise_soul(scope: PlayerScope, command: RaiseSoul) -> Effect:
    spirit = await control.raise_soul(await scope.context("soul_raise"), command.mortal_id, alignment=command.alignment, place_id=command.place_id)
    return Effect(f"{spirit.name} walks again.", spirit.id, created_ids=(spirit.id,))


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
    return Effect("The spirit is loosed." if command.binding is BindingKind.NONE else "The spirit is bound.", command.spirit_id)


@player_action("soul:seal", ActionKind.EDIT_RECORD)
async def seal_soul(scope: PlayerScope, command: SealSoul) -> Effect:
    row = await control.seal_soul(await scope.context("soul_seal"), command.spirit_id, sealed=command.sealed, strength=command.strength)
    return Effect(f"The soul is sealed against return ({row.seal_strength})." if row.sealed else "The seal on the soul is broken.", command.spirit_id)


@player_action("soul:reincarnate", ActionKind.OTHER)
async def reincarnate(scope: PlayerScope, command: Reincarnate) -> Effect:
    child = await control.reincarnate_soul(await scope.context("soul_reincarnate"), command.spirit_id, command.community_id)
    return Effect(f"The soul is born again as {child.name}.", child.id, created_ids=(child.id,))


@player_action("soul:edit", ActionKind.EDIT_RECORD)
async def edit_spirit(scope: PlayerScope, command: EditSpirit) -> Effect:
    row = await control.edit_spirit(await scope.context("soul_edit"), command.spirit_id, command.values, release=command.release)
    return Effect(f"The spirit remembers {row.memory_strength}% and is honoured {row.veneration}%.", command.spirit_id)


@player_action("soul:reread_deeds", ActionKind.EDIT_RECORD)
async def reread_deeds(scope: PlayerScope, command: SpiritTarget) -> Effect:
    await control.refresh_ledger(await scope.context("soul_edit"), command.spirit_id)
    return Effect("The soul's deeds are read again from its life.", command.spirit_id)


@player_action("soul:possess", ActionKind.OTHER)
async def possess(scope: PlayerScope, command: Possess) -> Effect:
    await control.possess_host(await scope.context("soul_possess"), command.spirit_id, command.host_id)
    return Effect("The spirit takes hold of its host.", command.host_id)


@player_action("soul:possession", ActionKind.EDIT_RECORD)
async def edit_possession(scope: PlayerScope, command: EditPossession) -> Effect:
    row = await control.edit_possession(await scope.context("soul_possess"), command.host_id, command.values, release=command.release)
    return Effect(f"The host bears stress {row.stress}.", command.host_id)


@player_action("soul:exorcise", ActionKind.OTHER)
async def exorcise(scope: PlayerScope, command: HostTarget) -> Effect:
    await control.exorcise_host(await scope.context("soul_exorcise"), command.host_id)
    return Effect("The spirit is driven out.", command.host_id)


@player_action("afterlife:stratum", ActionKind.EDIT_RECORD)
async def set_stratum(scope: PlayerScope, command: SetStratum) -> Effect:
    ctx = await scope.context("afterlife_stratum")
    row = await control.set_stratum(
        ctx,
        command.realm_id,
        command.kind,
        name=command.name,
        criteria=command.criteria,
        remove=command.remove,
        stratum_id=command.stratum_id,
        son_id=command.son_id,
        cult_id=command.cult_id,
        closed=command.closed,
        clear_links=command.clear_links,
    )
    return Effect(f"{row.name} is set." if row is not None else "The stratum is unmade.", command.realm_id)
