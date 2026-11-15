from aerona.core.grammar import several
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.means import ContainerKind, LockKind, NavigationAid, WaterLift, WritingMedium
from aerona.engine.means import control
from aerona.services.player.cosmography import Edited
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class RunNow(Command):
    pass


class WritingCustomDraft(Command):
    people_id: int
    medium: WritingMedium = WritingMedium.CLAY_TABLET


class WritingCustomTarget(Command):
    people_id: int


class WritingCustomEdit(Edited):
    people_id: int


class WrittenWorkDraft(Command):
    work_id: int
    medium: WritingMedium = WritingMedium.PAPER
    condition: int = 100
    copies: int = 1


class WrittenWorkTarget(Command):
    work_id: int


class WrittenWorkEdit(Edited):
    work_id: int


class SecurityDraft(Command):
    holder_id: int
    lock: LockKind | None = LockKind.BAR
    lock_quality: int = 30
    sealed: bool = False
    guards: int = 0
    traps: bool = False


class SecurityTarget(Command):
    holder_id: int


class SecurityEdit(Edited):
    holder_id: int


class WaterLiftDraft(Command):
    settlement_id: int
    device: WaterLift = WaterLift.SHADUF
    count: int = 1


class WaterLiftTarget(Command):
    settlement_id: int
    device: WaterLift


class WaterLiftEdit(Edited):
    settlement_id: int
    device: WaterLift


class NavigationKitDraft(Command):
    holder_id: int
    aid: NavigationAid = NavigationAid.COMPASS
    quality: int = 30


class NavigationKitTarget(Command):
    holder_id: int
    aid: NavigationAid


class NavigationKitEdit(Edited):
    holder_id: int
    aid: NavigationAid


class ContainerStockDraft(Command):
    community_id: int
    kind: ContainerKind = ContainerKind.AMPHORA
    count: int = 10
    broken: int = 0


class ContainerStockTarget(Command):
    community_id: int
    kind: ContainerKind


class ContainerStockEdit(Edited):
    community_id: int
    kind: ContainerKind


@player_action("writing_custom:set", ActionKind.EDIT_RECORD)
async def writing_custom_set(scope: PlayerScope, command: WritingCustomDraft) -> Effect:
    row = await control.set_record(
        await scope.context("writing_custom_set"), "writing_custom", {"people_entity_id": command.people_id}, {"medium": command.medium}
    )
    return Effect("The people write on it now.", values={"record_id": getattr(row, "id", 0)})


@player_action("writing_custom:edit", ActionKind.EDIT_RECORD)
async def writing_custom_edit(scope: PlayerScope, command: WritingCustomEdit) -> Effect:
    await control.edit_record(await scope.context("writing_custom_edit"), "writing_custom", command.people_id, command.values, command.release)
    return Effect("The custom of writing is set so.")


@player_action("writing_custom:delete", ActionKind.EDIT_RECORD)
async def writing_custom_delete(scope: PlayerScope, command: WritingCustomTarget) -> Effect:
    await control.delete_record(await scope.context("writing_custom_delete"), "writing_custom", command.people_id)
    return Effect("The custom of writing is struck.")


@player_action("written_work:set", ActionKind.EDIT_RECORD)
async def written_work_set(scope: PlayerScope, command: WrittenWorkDraft) -> Effect:
    row = await control.set_record(
        await scope.context("written_work_set"),
        "written_work",
        {"work_entity_id": command.work_id},
        {"medium": command.medium, "condition": command.condition, "copies": command.copies},
    )
    return Effect("The work is set down on it.", values={"record_id": getattr(row, "id", 0)})


@player_action("written_work:edit", ActionKind.EDIT_RECORD)
async def written_work_edit(scope: PlayerScope, command: WrittenWorkEdit) -> Effect:
    await control.edit_record(await scope.context("written_work_edit"), "written_work", command.work_id, command.values, command.release)
    return Effect("The written work is set so.")


@player_action("written_work:delete", ActionKind.EDIT_RECORD)
async def written_work_delete(scope: PlayerScope, command: WrittenWorkTarget) -> Effect:
    await control.delete_record(await scope.context("written_work_delete"), "written_work", command.work_id)
    return Effect("The written work forgets its medium.")


@player_action("security:set", ActionKind.EDIT_RECORD)
async def security_set(scope: PlayerScope, command: SecurityDraft) -> Effect:
    row = await control.set_record(
        await scope.context("security_set"),
        "security",
        {"holder_entity_id": command.holder_id},
        {"lock": command.lock, "lock_quality": command.lock_quality, "sealed": command.sealed, "guards": command.guards, "traps": command.traps},
    )
    return Effect("The vault is secured.", values={"record_id": getattr(row, "id", 0)})


@player_action("security:edit", ActionKind.EDIT_RECORD)
async def security_edit(scope: PlayerScope, command: SecurityEdit) -> Effect:
    await control.edit_record(await scope.context("security_edit"), "security", command.holder_id, command.values, command.release)
    return Effect("The vault is set so.")


@player_action("security:delete", ActionKind.EDIT_RECORD)
async def security_delete(scope: PlayerScope, command: SecurityTarget) -> Effect:
    await control.delete_record(await scope.context("security_delete"), "security", command.holder_id)
    return Effect("The vault lies open.")


@player_action("water_lift:set", ActionKind.EDIT_RECORD)
async def water_lift_set(scope: PlayerScope, command: WaterLiftDraft) -> Effect:
    row = await control.set_record(
        await scope.context("water_lift_set"), "water_lift", {"settlement_entity_id": command.settlement_id, "device": command.device}, {"count": command.count}
    )
    return Effect("The devices lift water.", values={"record_id": getattr(row, "id", 0)})


@player_action("water_lift:edit", ActionKind.EDIT_RECORD)
async def water_lift_edit(scope: PlayerScope, command: WaterLiftEdit) -> Effect:
    await control.edit_record(await scope.context("water_lift_edit"), "water_lift", (command.settlement_id, command.device), command.values, command.release)
    return Effect("The devices are set so.")


@player_action("water_lift:delete", ActionKind.EDIT_RECORD)
async def water_lift_delete(scope: PlayerScope, command: WaterLiftTarget) -> Effect:
    await control.delete_record(await scope.context("water_lift_delete"), "water_lift", (command.settlement_id, command.device))
    return Effect("The devices are taken down.")


@player_action("navigation_kit:set", ActionKind.EDIT_RECORD)
async def navigation_kit_set(scope: PlayerScope, command: NavigationKitDraft) -> Effect:
    row = await control.set_record(
        await scope.context("navigation_kit_set"), "navigation_kit", {"holder_entity_id": command.holder_id, "aid": command.aid}, {"quality": command.quality}
    )
    return Effect("The pilots take up the instrument.", values={"record_id": getattr(row, "id", 0)})


@player_action("navigation_kit:edit", ActionKind.EDIT_RECORD)
async def navigation_kit_edit(scope: PlayerScope, command: NavigationKitEdit) -> Effect:
    await control.edit_record(await scope.context("navigation_kit_edit"), "navigation_kit", (command.holder_id, command.aid), command.values, command.release)
    return Effect("The instrument is set so.")


@player_action("navigation_kit:delete", ActionKind.EDIT_RECORD)
async def navigation_kit_delete(scope: PlayerScope, command: NavigationKitTarget) -> Effect:
    await control.delete_record(await scope.context("navigation_kit_delete"), "navigation_kit", (command.holder_id, command.aid))
    return Effect("The instrument is lost.")


@player_action("container_stock:set", ActionKind.EDIT_RECORD)
async def container_stock_set(scope: PlayerScope, command: ContainerStockDraft) -> Effect:
    row = await control.set_record(
        await scope.context("container_stock_set"),
        "container_stock",
        {"community_entity_id": command.community_id, "kind": command.kind},
        {"count": command.count, "broken": command.broken},
    )
    return Effect("The containers are stocked.", values={"record_id": getattr(row, "id", 0)})


@player_action("container_stock:edit", ActionKind.EDIT_RECORD)
async def container_stock_edit(scope: PlayerScope, command: ContainerStockEdit) -> Effect:
    await control.edit_record(
        await scope.context("container_stock_edit"), "container_stock", (command.community_id, command.kind), command.values, command.release
    )
    return Effect("The containers are set so.")


@player_action("container_stock:delete", ActionKind.EDIT_RECORD)
async def container_stock_delete(scope: PlayerScope, command: ContainerStockTarget) -> Effect:
    await control.delete_record(await scope.context("container_stock_delete"), "container_stock", (command.community_id, command.kind))
    return Effect("The containers are gone.")


@player_action("means:run", ActionKind.EDIT_RECORD)
async def means_run(scope: PlayerScope, command: RunNow) -> Effect:
    tally = await control.run_means(await scope.context("means_run"))
    told = [
        several(tally.media.works, "work", "works") + " given a medium",
        several(tally.security.secured, "store", "stores") + " secured",
        several(tally.water.built, "device", "devices") + " raised to lift water",
        several(tally.navigation.equipped, "instrument", "instruments") + " taken up by pilots",
        several(tally.containers.made, "container", "containers") + " made",
    ]
    return Effect("; ".join(told) + ".")
