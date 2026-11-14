from aerona.core.grammar import several
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.climes import CirculationBand, OscillationPhase
from aerona.domain.enums.mind import ValueAxis
from aerona.engine.climes import control
from aerona.services.player.cosmography import Edited
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class RunNow(Command):
    pass


class CultureValue(Command):
    culture_id: int
    axis: ValueAxis
    value: int


class RegionWindDraft(Command):
    region_id: int
    band: CirculationBand = CirculationBand.TRADE
    wind_from: int = 2
    strength: int = 50
    windward: bool = False
    shadow: int = 0
    monsoon: int = 0
    upwelling: bool = False


class RegionWindTarget(Command):
    region_id: int


class RegionWindEdit(Edited):
    region_id: int


class MonsoonSeasonDraft(Command):
    world_id: int
    epoch: int
    strength: int = 100
    failed: bool = False


class MonsoonSeasonTarget(Command):
    world_id: int
    epoch: int


class MonsoonSeasonEdit(Edited):
    world_id: int
    epoch: int


class ClimateOscillationDraft(Command):
    world_id: int
    phase: OscillationPhase = OscillationPhase.NEUTRAL
    period: int = 6
    strength: int = 10


class ClimateOscillationTarget(Command):
    world_id: int


class ClimateOscillationEdit(Edited):
    world_id: int


class LaunchWindowDraft(Command):
    from_world_id: int
    to_world_id: int
    synodic: int = 4
    offset: int = 0
    open: bool = False


class LaunchWindowTarget(Command):
    from_world_id: int
    to_world_id: int


class LaunchWindowEdit(Edited):
    from_world_id: int
    to_world_id: int


class CosmopolitanCultureDraft(Command):
    route_id: int | None = None
    name: str
    lingua_franca_entity_id: int | None = None
    strength: int = 20


class CosmopolitanCultureTarget(Command):
    record_id: int


class CosmopolitanCultureEdit(Edited):
    record_id: int


class CosmopolitanMemberDraft(Command):
    culture_id: int
    community_id: int
    share: int = 20


class CosmopolitanMemberTarget(Command):
    culture_id: int
    community_id: int


class CosmopolitanMemberEdit(Edited):
    culture_id: int
    community_id: int


@player_action("region_wind:set", ActionKind.EDIT_RECORD)
async def region_wind_set(scope: PlayerScope, command: RegionWindDraft) -> Effect:
    row = await control.set_record(
        await scope.context("region_wind_set"),
        "region_wind",
        {"region_entity_id": command.region_id},
        {
            "band": command.band,
            "wind_from": command.wind_from,
            "strength": command.strength,
            "windward": command.windward,
            "shadow": command.shadow,
            "monsoon": command.monsoon,
            "upwelling": command.upwelling,
        },
    )
    return Effect("The wind blows so.", values={"record_id": getattr(row, "id", 0)})


@player_action("region_wind:edit", ActionKind.EDIT_RECORD)
async def region_wind_edit(scope: PlayerScope, command: RegionWindEdit) -> Effect:
    await control.edit_record(await scope.context("region_wind_edit"), "region_wind", command.region_id, command.values, command.release)
    return Effect("The wind is set so.")


@player_action("region_wind:delete", ActionKind.EDIT_RECORD)
async def region_wind_delete(scope: PlayerScope, command: RegionWindTarget) -> Effect:
    await control.delete_record(await scope.context("region_wind_delete"), "region_wind", command.region_id)
    return Effect("The wind is read anew.")


@player_action("monsoon_season:set", ActionKind.EDIT_RECORD)
async def monsoon_season_set(scope: PlayerScope, command: MonsoonSeasonDraft) -> Effect:
    row = await control.set_record(
        await scope.context("monsoon_season_set"),
        "monsoon_season",
        {"world_id": command.world_id, "epoch": command.epoch},
        {"strength": command.strength, "failed": command.failed},
    )
    return Effect("The monsoon comes so.", values={"record_id": getattr(row, "id", 0)})


@player_action("monsoon_season:edit", ActionKind.EDIT_RECORD)
async def monsoon_season_edit(scope: PlayerScope, command: MonsoonSeasonEdit) -> Effect:
    await control.edit_record(await scope.context("monsoon_season_edit"), "monsoon_season", (command.world_id, command.epoch), command.values, command.release)
    return Effect("The monsoon is set so.")


@player_action("monsoon_season:delete", ActionKind.EDIT_RECORD)
async def monsoon_season_delete(scope: PlayerScope, command: MonsoonSeasonTarget) -> Effect:
    await control.delete_record(await scope.context("monsoon_season_delete"), "monsoon_season", (command.world_id, command.epoch))
    return Effect("The monsoon is read anew.")


@player_action("climate_oscillation:set", ActionKind.EDIT_RECORD)
async def climate_oscillation_set(scope: PlayerScope, command: ClimateOscillationDraft) -> Effect:
    row = await control.set_record(
        await scope.context("climate_oscillation_set"),
        "climate_oscillation",
        {"world_id": command.world_id},
        {"phase": command.phase, "period": command.period, "strength": command.strength},
    )
    return Effect("The seas swing so.", values={"record_id": getattr(row, "id", 0)})


@player_action("climate_oscillation:edit", ActionKind.EDIT_RECORD)
async def climate_oscillation_edit(scope: PlayerScope, command: ClimateOscillationEdit) -> Effect:
    await control.edit_record(await scope.context("climate_oscillation_edit"), "climate_oscillation", command.world_id, command.values, command.release)
    return Effect("The oscillation is set so.")


@player_action("climate_oscillation:delete", ActionKind.EDIT_RECORD)
async def climate_oscillation_delete(scope: PlayerScope, command: ClimateOscillationTarget) -> Effect:
    await control.delete_record(await scope.context("climate_oscillation_delete"), "climate_oscillation", command.world_id)
    return Effect("The oscillation is stilled.")


@player_action("launch_window:set", ActionKind.EDIT_RECORD)
async def launch_window_set(scope: PlayerScope, command: LaunchWindowDraft) -> Effect:
    row = await control.set_record(
        await scope.context("launch_window_set"),
        "launch_window",
        {"from_world_id": command.from_world_id, "to_world_id": command.to_world_id},
        {"synodic": command.synodic, "offset": command.offset, "open": command.open},
    )
    return Effect("The window between the worlds is set.", values={"record_id": getattr(row, "id", 0)})


@player_action("launch_window:edit", ActionKind.EDIT_RECORD)
async def launch_window_edit(scope: PlayerScope, command: LaunchWindowEdit) -> Effect:
    await control.edit_record(
        await scope.context("launch_window_edit"), "launch_window", (command.from_world_id, command.to_world_id), command.values, command.release
    )
    return Effect("The window is set so.")


@player_action("launch_window:delete", ActionKind.EDIT_RECORD)
async def launch_window_delete(scope: PlayerScope, command: LaunchWindowTarget) -> Effect:
    await control.delete_record(await scope.context("launch_window_delete"), "launch_window", (command.from_world_id, command.to_world_id))
    return Effect("The window is read anew.")


@player_action("cosmopolitan_culture:create", ActionKind.EDIT_RECORD)
async def cosmopolitan_culture_create(scope: PlayerScope, command: CosmopolitanCultureDraft) -> Effect:
    row = await control.set_record(
        await scope.context("cosmopolitan_culture_create"),
        "cosmopolitan_culture",
        {},
        {"route_id": command.route_id, "name": command.name, "lingua_franca_entity_id": command.lingua_franca_entity_id, "strength": command.strength},
    )
    return Effect("A culture of the road forms.", values={"record_id": getattr(row, "id", 0)})


@player_action("cosmopolitan_culture:edit", ActionKind.EDIT_RECORD)
async def cosmopolitan_culture_edit(scope: PlayerScope, command: CosmopolitanCultureEdit) -> Effect:
    await control.edit_record(await scope.context("cosmopolitan_culture_edit"), "cosmopolitan_culture", command.record_id, command.values, command.release)
    return Effect("The culture is set so.")


@player_action("cosmopolitan_culture:delete", ActionKind.EDIT_RECORD)
async def cosmopolitan_culture_delete(scope: PlayerScope, command: CosmopolitanCultureTarget) -> Effect:
    await control.delete_record(await scope.context("cosmopolitan_culture_delete"), "cosmopolitan_culture", command.record_id)
    return Effect("The culture fades.")


@player_action("cosmopolitan_member:set", ActionKind.EDIT_RECORD)
async def cosmopolitan_member_set(scope: PlayerScope, command: CosmopolitanMemberDraft) -> Effect:
    row = await control.set_record(
        await scope.context("cosmopolitan_member_set"),
        "cosmopolitan_member",
        {"culture_id": command.culture_id, "community_entity_id": command.community_id},
        {"share": command.share},
    )
    return Effect("The community joins the culture of the road.", values={"record_id": getattr(row, "id", 0)})


@player_action("cosmopolitan_member:edit", ActionKind.EDIT_RECORD)
async def cosmopolitan_member_edit(scope: PlayerScope, command: CosmopolitanMemberEdit) -> Effect:
    await control.edit_record(
        await scope.context("cosmopolitan_member_edit"), "cosmopolitan_member", (command.culture_id, command.community_id), command.values, command.release
    )
    return Effect("The membership is set so.")


@player_action("cosmopolitan_member:delete", ActionKind.EDIT_RECORD)
async def cosmopolitan_member_delete(scope: PlayerScope, command: CosmopolitanMemberTarget) -> Effect:
    await control.delete_record(await scope.context("cosmopolitan_member_delete"), "cosmopolitan_member", (command.culture_id, command.community_id))
    return Effect("The community leaves the culture.")


@player_action("cosmopolitan_culture:value", ActionKind.EDIT_RECORD)
async def cosmopolitan_culture_value(scope: PlayerScope, command: CultureValue) -> Effect:
    await control.set_value(await scope.context("cosmopolitan_culture_value"), command.culture_id, command.axis, command.value)
    return Effect("The culture of the road holds that value so.")


@player_action("climes:run", ActionKind.EDIT_RECORD)
async def climes_run(scope: PlayerScope, command: RunNow) -> Effect:
    tally = await control.run_climes(await scope.context("climes_run"))
    told = [
        several(tally.winds.read, "land", "lands") + " read for its winds",
        several(tally.winds.shadows, "rain shadow", "rain shadows"),
        several(tally.seasons.failed, "failed monsoon", "failed monsoons"),
        several(tally.seasons.turned, "oscillation turned", "oscillations turned"),
    ]
    return Effect("; ".join(told) + ".")


@player_action("crossings:run", ActionKind.EDIT_RECORD)
async def crossings_run(scope: PlayerScope, command: RunNow) -> Effect:
    tally = await control.run_crossings(await scope.context("crossings_run"))
    told = [
        several(tally.windows, "window", "windows") + " read",
        several(tally.open_windows, "window", "windows") + " open",
        several(tally.cultures, "culture of a road", "cultures of roads") + " formed",
    ]
    return Effect("; ".join(told) + ".")
