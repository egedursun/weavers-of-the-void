from pydantic import Field

from aerona.catalog.mobility import MOBILITY_EVENTS
from aerona.catalog.needs import SHORTFALLS
from aerona.core.errors import ValidationFailedError
from aerona.core.grammar import several, spoken
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.demography import Job
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.society_depth import DriftCause, MobilityEvent, ShortfallEffect
from aerona.engine.demography import society_control as control
from aerona.engine.demography.events import moved_class
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class HoldNeed(Command):
    community_id: int
    social_class: SocialClass
    commodity: CommodityKind
    held_pct: int | None = Field(default=None, ge=0, le=100)


class HoldShortfall(Command):
    community_id: int
    effect: ShortfallEffect
    short_pct: int | None = Field(default=None, ge=0, le=100)


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
    work_id: int | None = None


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
    label = f"{spoken(command.social_class)}s' {spoken(command.commodity)}"
    if row.held_pct is None:
        return Effect(f"The {label} is met as the stores allow again.", command.community_id)
    return Effect(f"The {label} is held at {row.held_pct}% met.", command.community_id, values={"held_pct": row.held_pct})


@player_action("shortfall:set", ActionKind.EDIT_RECORD)
async def hold_shortfall(scope: PlayerScope, command: HoldShortfall) -> Effect:
    row = await control.hold_shortfall(await scope.context("shortfall_set"), command.community_id, command.effect, command.short_pct)
    label = SHORTFALLS[command.effect].label.lower()
    if command.short_pct is None:
        return Effect(f"{label.capitalize()} follows the world again.", command.community_id)
    return Effect(f"{label.capitalize()} is held at {row.short_pct}% short.", command.community_id, values={"short_pct": row.short_pct})


@player_action("class:standing", ActionKind.EDIT_RECORD)
async def edit_standing(scope: PlayerScope, command: EditStanding) -> Effect:
    row = await control.edit_standing(
        await scope.context("class_standing"), command.community_id, command.social_class, command.values, release=command.release
    )
    return Effect(
        f"The {spoken(command.social_class)}s hold {row.wealth} wealth, are fed {row.fed_pct}% and have {row.needs_met_pct}% of their needs.",
        command.community_id,
        values={"wealth": row.wealth},
    )


@player_action("labour:set", ActionKind.EDIT_RECORD)
async def set_labour(scope: PlayerScope, command: SetLabour) -> Effect:
    row = await control.set_labour(await scope.context("labour_set"), command.community_id, command.job, command.workers)
    if not row.held:
        return Effect(f"Work at {spoken(command.job)} follows the people and the prices again.", command.community_id)
    return Effect(f"{row.workers} are held at {spoken(command.job)}.", command.community_id, values={"workers": row.workers})


@player_action("labour:corvee", ActionKind.EDIT_RECORD)
async def set_corvee(scope: PlayerScope, command: SetCorvee) -> Effect:
    row = await control.set_corvee(await scope.context("labour_corvee"), command.community_id, command.share_pct, command.polity_id, command.work_id)
    if row is None:
        return Effect("The corvee was lifted.", command.community_id)
    return Effect(f"A corvee of {row.share_pct}% of the workers was laid on the great works.", command.community_id, values={"share_pct": row.share_pct})


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
        f"For {several(row.epochs_left, 'epoch', 'epochs')}, {spoken(command.cause)} will push their {spoken(command.axis)} by {row.amount}.",
        command.community_id,
        values={"imposition_id": row.id},
    )


@player_action("drift:edit", ActionKind.EDIT_RECORD)
async def edit_drift(scope: PlayerScope, command: EditDrift) -> Effect:
    row = await control.edit_drift(
        await scope.context("drift_edit"), command.imposition_id, amount=command.amount, epochs=command.epochs, cause=command.cause, axis=command.axis
    )
    return Effect(f"The pressure now pushes {spoken(row.axis)} by {row.amount} for {several(row.epochs_left, 'epoch', 'epochs')}.", row.community_entity_id)


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
    return Effect(f"{moved} {spoken(command.source)}s were put in chains.", command.community_id, values={"moved": moved})


@player_action("mobility:manumit", ActionKind.EDIT_RECORD)
async def manumit(scope: PlayerScope, command: Manumit) -> Effect:
    moved = await control.manumit(await scope.context("mobility_manumit"), command.community_id, command.count, command.target)
    return Effect(f"{moved} of the bound were set free.", command.community_id, values={"moved": moved})


class MoveClass(Command):
    mortal_id: int
    event: MobilityEvent


@player_action("mobility:move", ActionKind.EDIT_RECORD)
async def move_class(scope: PlayerScope, command: MoveClass) -> Effect:
    mortal = await scope.session.get(EntityRow, command.mortal_id)
    if mortal is None or mortal.entity_type is not EntityType.MORTAL:
        raise ValidationFailedError("Only a mortal changes class.")
    if MOBILITY_EVENTS[command.event].lands_in is None:
        raise ValidationFailedError("That change of standing lands in no single class; use its own control.")
    moved = await moved_class(await scope.context("mobility_move"), mortal, command.event, cause="the will of the Creator", by_hand=True)
    label = MOBILITY_EVENTS[command.event].label.lower()
    return Effect(f"{mortal.name} was {label}." if moved else f"{mortal.name} already stands there.", mortal.id)
