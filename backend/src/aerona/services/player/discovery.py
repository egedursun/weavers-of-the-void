from aerona.catalog.discovery import AGES, BLUEPRINT_KINDS, FIELDS, INCIDENTS, era_name
from aerona.core.grammar import an
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.discovery import AgeKind, BlueprintKind, GreatField, ResearchIncident
from aerona.engine.lore import discovery_control
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class RaiseGreat(Command):
    mortal_id: int
    field: GreatField
    deed: bool = True


class SetEra(Command):
    polity_id: int
    score: int | None = None
    age: AgeKind | None = None
    hold: bool = True


class SetWorldEra(Command):
    world_id: int
    era: int
    hold: bool = True


class CauseIncident(Command):
    holder_id: int
    kind: ResearchIncident
    technique: Technique | None = None


class GrantDesign(Command):
    holder_id: int
    kind: BlueprintKind
    subject: str
    quality: int = 60
    name: str | None = None


class BanWork(Command):
    polity_id: int
    work_id: int
    banned: bool = True


@player_action("discovery:raise_great", ActionKind.EDIT_RECORD)
async def raise_great(scope: PlayerScope, command: RaiseGreat) -> Effect:
    row = await discovery_control.raise_great(await scope.context("discovery_raise_great"), command.mortal_id, command.field, deed=command.deed)
    return Effect(f"They rise as {an(FIELDS[row.field].label.lower())}.", command.mortal_id)


@player_action("discovery:era", ActionKind.EDIT_RECORD)
async def set_era(scope: PlayerScope, command: SetEra) -> Effect:
    row = await discovery_control.set_era(await scope.context("discovery_era"), command.polity_id, command.score, command.age, hold=command.hold)
    return Effect(f"{AGES[row.age]}, with an era score of {row.score}.", command.polity_id)


@player_action("discovery:world_era", ActionKind.EDIT_RECORD)
async def set_world_era(scope: PlayerScope, command: SetWorldEra) -> Effect:
    row = await discovery_control.set_world_era(await scope.context("discovery_world_era"), command.world_id, command.era, hold=command.hold)
    return Effect(f"The world stands in the {era_name(row.era).lower()}.", command.world_id)


@player_action("discovery:incident", ActionKind.EDIT_RECORD)
async def cause_incident(scope: PlayerScope, command: CauseIncident) -> Effect:
    row = await discovery_control.cause_incident(await scope.context("discovery_incident"), command.holder_id, command.kind, command.technique)
    return Effect(f"{INCIDENTS[row.kind]}.", command.holder_id)


@player_action("discovery:design", ActionKind.EDIT_RECORD)
async def grant_design(scope: PlayerScope, command: GrantDesign) -> Effect:
    ctx = await scope.context("discovery_design")
    row = await discovery_control.grant_design(ctx, command.holder_id, command.kind, command.subject, quality=command.quality, name=command.name)
    return Effect(f"They hold {an(BLUEPRINT_KINDS[row.kind].lower())}: {row.name}.", command.holder_id)


@player_action("discovery:ban", ActionKind.EDIT_RECORD)
async def ban_work(scope: PlayerScope, command: BanWork) -> Effect:
    row = await discovery_control.set_ban(await scope.context("discovery_ban"), command.polity_id, command.work_id, banned=command.banned)
    return Effect("The work is banned there." if row is not None else "The ban is lifted.", command.polity_id)
