from pydantic import Field

from aerona.core.grammar import an
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.faction import FactionGoalKind, FactionRank
from aerona.engine.factions import control
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class EditFaction(Command):
    faction_id: int
    values: dict[str, int | str | bool | dict[str, int] | dict[str, float] | None] = Field(default_factory=dict)
    release: list[str] = Field(default_factory=list)


class FactionGoal(Command):
    faction_id: int
    kind: FactionGoalKind
    goal_id: int | None = None
    target_id: int | None = None
    target_key: str | None = Field(default=None, max_length=120)
    priority: int = Field(default=80, ge=0, le=100)
    progress: int | None = Field(default=None, ge=0, le=100)
    remove: bool = False


class FactionMember(Command):
    faction_id: int
    mortal_id: int
    rank: FactionRank | None = None
    remove: bool = False


class FundFaction(Command):
    faction_id: int
    amount: int = Field(ge=-1000000, le=1000000)


class OutlawFaction(Command):
    faction_id: int
    outlawed: bool = True


class CharterFaction(Command):
    faction_id: int
    polity_id: int | None = None
    monopoly: str | None = Field(default=None, max_length=120)


class HireCompany(Command):
    faction_id: int
    polity_id: int | None = None
    pay: int = Field(default=20, ge=0, le=1000000)
    epochs: int = Field(default=3, ge=1, le=1000)


@player_action("faction:edit", ActionKind.EDIT_RECORD)
async def edit_faction(scope: PlayerScope, command: EditFaction) -> Effect:
    profile = await control.edit_faction(await scope.context("faction_edit"), command.faction_id, command.values, release=command.release)
    return Effect(f"The faction is {an(profile.kind.value.replace('_', ' '))} with {profile.treasury} in its coffers.", command.faction_id)


@player_action("faction:goal", ActionKind.STEER_FACTION)
async def set_goal(scope: PlayerScope, command: FactionGoal) -> Effect:
    goal = await control.set_goal(
        await scope.context("faction_goal"),
        command.faction_id,
        command.kind,
        goal_id=command.goal_id,
        target_id=command.target_id,
        target_key=command.target_key,
        priority=command.priority,
        progress=command.progress,
        remove=command.remove,
    )
    return Effect("The goal is struck." if goal is None else f"The faction now strives to {command.kind.value.replace('_', ' ')}.", command.faction_id)


@player_action("faction:member", ActionKind.EDIT_RECORD)
async def set_member(scope: PlayerScope, command: FactionMember) -> Effect:
    row = await control.set_member(await scope.context("faction_member"), command.faction_id, command.mortal_id, rank=command.rank, remove=command.remove)
    return Effect("The member is cast out." if row is None else f"The mortal is now {an(row.rank.value)} of the faction.", command.faction_id)


@player_action("faction:fund", ActionKind.EDIT_RECORD)
async def fund(scope: PlayerScope, command: FundFaction) -> Effect:
    profile = await control.fund(await scope.context("faction_fund"), command.faction_id, command.amount)
    return Effect(f"The faction's treasury stands at {profile.treasury}.", command.faction_id)


@player_action("faction:outlaw", ActionKind.EDIT_RECORD)
async def outlaw(scope: PlayerScope, command: OutlawFaction) -> Effect:
    await control.outlaw(await scope.context("faction_outlaw"), command.faction_id, outlawed=command.outlawed)
    return Effect("The faction is outlawed; every hand is against it." if command.outlawed else "The faction is lawful again.", command.faction_id)


@player_action("faction:charter", ActionKind.EDIT_RECORD)
async def charter(scope: PlayerScope, command: CharterFaction) -> Effect:
    await control.charter(await scope.context("faction_charter"), command.faction_id, command.polity_id, monopoly=command.monopoly)
    return Effect("The charter is granted." if command.polity_id is not None else "The charter is revoked.", command.faction_id)


@player_action("faction:contract", ActionKind.EDIT_RECORD)
async def hire(scope: PlayerScope, command: HireCompany) -> Effect:
    await control.hire_company(await scope.context("faction_contract"), command.faction_id, command.polity_id, pay=command.pay, epochs=command.epochs)
    return Effect("The condotta is sealed." if command.polity_id is not None else "The condotta is ended.", command.faction_id)
