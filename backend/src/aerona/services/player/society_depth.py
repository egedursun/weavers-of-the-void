from pydantic import Field

from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.demography import Job
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.society_depth import DriftCause
from aerona.engine.demography import society_control as control
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


def words(value: str) -> str:
    return value.replace("_", " ")


class HoldNeed(Command):
    community_id: int
    social_class: SocialClass
    commodity: CommodityKind
    held_pct: int | None = Field(default=None, ge=0, le=100)


class EditStanding(Command):
    community_id: int
    social_class: SocialClass
    values: dict[str, int] = Field(default_factory=dict)
    release: list[str] = Field(default_factory=list)


class SetLabour(Command):
    community_id: int
    job: Job
    workers: int | None = Field(default=None, ge=0)


class SetCorvee(Command):
    community_id: int
    share_pct: int = Field(ge=0, le=100)
    polity_id: int | None = None


class EditLoyalty(Command):
    polity_id: int
    member_id: int
    values: dict[str, int] = Field(default_factory=dict)
    release: list[str] = Field(default_factory=list)


class ImposeDrift(Command):
    community_id: int
    cause: DriftCause
    axis: ValueAxis
    amount: int = Field(ge=-100, le=100)
    epochs: int = Field(default=1, ge=1, le=1000)


class EditDrift(Command):
    imposition_id: int
    amount: int | None = Field(default=None, ge=-100, le=100)
    epochs: int | None = Field(default=None, ge=1, le=1000)
    cause: DriftCause | None = None
    axis: ValueAxis | None = None


class DriftTarget(Command):
    imposition_id: int


class MortalTarget(Command):
    mortal_id: int


class Ruin(Command):
    mortal_id: int
    bondage: bool = False


class Enslave(Command):
    community_id: int
    count: int = Field(ge=1)
    source: SocialClass = SocialClass.FARMER


class Manumit(Command):
    community_id: int
    count: int = Field(ge=1)
    target: SocialClass = SocialClass.FARMER


@player_action("needs:hold", ActionKind.EDIT_RECORD)
async def hold_need(scope: PlayerScope, command: HoldNeed) -> Effect:
    row = await control.hold_need(await scope.context("needs_hold"), command.community_id, command.social_class, command.commodity, command.held_pct)
    label = f"{words(command.social_class.value)}s' {words(command.commodity.value)}"
    if row.held_pct is None:
        return Effect(f"The {label} is met as the stores allow again.", command.community_id)
    return Effect(f"The {label} is held at {row.held_pct}% met.", command.community_id, values={"held_pct": row.held_pct})


@player_action("class:standing", ActionKind.EDIT_RECORD)
async def edit_standing(scope: PlayerScope, command: EditStanding) -> Effect:
    row = await control.edit_standing(
        await scope.context("class_standing"), command.community_id, command.social_class, command.values, release=command.release
    )
    return Effect(
        f"The {words(command.social_class.value)}s hold {row.wealth} wealth, are fed {row.fed_pct}% and have {row.needs_met_pct}% of their needs.",
        command.community_id,
        values={"wealth": row.wealth},
    )


@player_action("labour:set", ActionKind.EDIT_RECORD)
async def set_labour(scope: PlayerScope, command: SetLabour) -> Effect:
    row = await control.set_labour(await scope.context("labour_set"), command.community_id, command.job, command.workers)
    if not row.held:
        return Effect(f"Work at {words(command.job.value)} follows the people and the prices again.", command.community_id)
    return Effect(f"{row.workers} are held at {words(command.job.value)}.", command.community_id, values={"workers": row.workers})


@player_action("labour:corvee", ActionKind.EDIT_RECORD)
async def set_corvee(scope: PlayerScope, command: SetCorvee) -> Effect:
    row = await control.set_corvee(await scope.context("labour_corvee"), command.community_id, command.share_pct, command.polity_id)
    if row is None:
        return Effect("The corvee was lifted.", command.community_id)
    return Effect(f"A corvee of {row.share_pct}% of the farmhands was laid on the great works.", command.community_id, values={"share_pct": row.share_pct})


@player_action("loyalty:edit", ActionKind.EDIT_RECORD)
async def edit_loyalty(scope: PlayerScope, command: EditLoyalty) -> Effect:
    row = await control.edit_loyalty(await scope.context("loyalty_edit"), command.polity_id, command.member_id, command.values, release=command.release)
    return Effect(f"Loyalty {row.loyalty}: grievances {row.grievances}, benefits {row.benefits}.", command.member_id, values={"loyalty": row.loyalty})


@player_action("drift:impose", ActionKind.EDIT_RECORD)
async def impose_drift(scope: PlayerScope, command: ImposeDrift) -> Effect:
    row = await control.impose_drift(
        await scope.context("drift_impose"), command.community_id, command.cause, command.axis, amount=command.amount, epochs=command.epochs
    )
    return Effect(
        f"For {row.epochs_left} epochs, {words(command.cause.value)} will push their {words(command.axis.value)} by {row.amount}.",
        command.community_id,
        values={"imposition_id": row.id},
    )


@player_action("drift:edit", ActionKind.EDIT_RECORD)
async def edit_drift(scope: PlayerScope, command: EditDrift) -> Effect:
    row = await control.edit_drift(
        await scope.context("drift_edit"), command.imposition_id, amount=command.amount, epochs=command.epochs, cause=command.cause, axis=command.axis
    )
    return Effect(f"The pressure now pushes {words(row.axis.value)} by {row.amount} for {row.epochs_left} epochs.", row.community_entity_id)


@player_action("drift:cancel", ActionKind.EDIT_RECORD)
async def cancel_drift(scope: PlayerScope, command: DriftTarget) -> Effect:
    community_id = await control.cancel_drift(await scope.context("drift_cancel"), command.imposition_id)
    return Effect("The pressure on their values was lifted.", community_id)


@player_action("mobility:ennoble", ActionKind.EDIT_RECORD)
async def ennoble(scope: PlayerScope, command: MortalTarget) -> Effect:
    house = await control.ennoble(await scope.context("mobility_ennoble"), command.mortal_id)
    if house is None:
        return Effect("They were raised among the nobles.", command.mortal_id)
    return Effect(f"They were raised among the nobles and founded {house.name}.", command.mortal_id, created_ids=(house.id,))


@player_action("mobility:ruin", ActionKind.EDIT_RECORD)
async def ruin(scope: PlayerScope, command: Ruin) -> Effect:
    member = await control.ruin(await scope.context("mobility_ruin"), command.mortal_id, bondage=command.bondage)
    return Effect(f"{member.name} lost everything.", command.mortal_id)


@player_action("mobility:enslave", ActionKind.EDIT_RECORD)
async def enslave(scope: PlayerScope, command: Enslave) -> Effect:
    moved = await control.enslave(await scope.context("mobility_enslave"), command.community_id, command.count, command.source)
    return Effect(f"{moved} {words(command.source.value)}s were put in chains.", command.community_id, values={"moved": moved})


@player_action("mobility:manumit", ActionKind.EDIT_RECORD)
async def manumit(scope: PlayerScope, command: Manumit) -> Effect:
    moved = await control.manumit(await scope.context("mobility_manumit"), command.community_id, command.count, command.target)
    return Effect(f"{moved} of the bound were set free.", command.community_id, values={"moved": moved})
