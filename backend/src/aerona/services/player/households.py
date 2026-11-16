from pydantic import Field
from sqlalchemy import select

from aerona.catalog.genetics import DWELLINGS, HOUSEHOLD_ROLE_LABELS
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import an, several
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.households import (
    HOUSEHOLD_FIELDS,
    DwellingFurnishingRow,
    DwellingRow,
    HouseholdAggregateRow,
    HouseholdMemberRow,
    HouseholdRow,
)
from aerona.db.tables.settlement import DistrictRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.genetics import DwellingKind, DwellingTenure, HouseholdForm, HouseholdRole
from aerona.domain.enums.industry import EnergyKind
from aerona.domain.enums.society import SocialClass
from aerona.engine.households.formation import found_household
from aerona.engine.primitives.manual import manual_context
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

SPAN = 100
MEMBERS = "members"


PLAIN_FIELDS = ("name", "social_class", "formed_epoch")


class FoundHousehold(Command):
    head_id: int


class HouseholdTarget(Command):
    household_id: int


class EditHousehold(Command):
    household_id: int
    name: str | None = Field(default=None, min_length=1, max_length=200)
    social_class: SocialClass | None = None
    wealth: int | None = Field(default=None, ge=0)
    income: int | None = Field(default=None, ge=0)
    expenses: int | None = Field(default=None, ge=0)
    servants: int | None = Field(default=None, ge=0)
    dependents: int | None = Field(default=None, ge=0)
    burden: int | None = Field(default=None, ge=0, le=SPAN)
    formed_epoch: int | None = Field(default=None, ge=0)
    form: HouseholdForm | None = None
    head_id: int | None = None
    hold: bool = True


class SetDebt(Command):
    household_id: int
    lender_household_id: int
    amount: int = Field(ge=0)
    hold: bool = True


class HoldHousehold(Command):
    household_id: int
    fields: list[str] = Field(min_length=1)
    hold: bool = True


class SetMember(Command):
    household_id: int
    mortal_id: int
    role: HouseholdRole
    cares_for_id: int | None = None
    hold: bool = True


class MemberTarget(Command):
    mortal_id: int


class SetDwelling(Command):
    household_id: int
    kind: DwellingKind | None = None
    quality: int | None = Field(default=None, ge=0, le=SPAN)
    rooms: int | None = Field(default=None, ge=1)
    district_id: int | None = None
    tenure: DwellingTenure | None = None
    heating: EnergyKind | None = None
    light: EnergyKind | None = None
    crowding: int | None = Field(default=None, ge=0, le=1000)
    clear_district: bool = False
    hold: bool = True


class Furnish(Command):
    household_id: int
    item_id: int


class FurnishingTarget(Command):
    item_id: int


class EditAggregate(Command):
    community_id: int
    social_class: SocialClass
    households: int | None = Field(default=None, ge=0)
    mean_size: int | None = Field(default=None, ge=0)
    dwelling_kind: DwellingKind | None = None
    quality: int | None = Field(default=None, ge=0, le=SPAN)
    wealth: int | None = Field(default=None, ge=0)
    hold: bool = True


class AggregateTarget(Command):
    community_id: int
    social_class: SocialClass


def held(locked: list[str] | None, fields: list[str], hold: bool) -> list[str]:
    found = set(locked or [])
    return sorted(found | set(fields)) if hold else sorted(found - set(fields))


async def household(scope: PlayerScope, household_id: int) -> HouseholdRow:
    found = await scope.session.get(HouseholdRow, household_id)
    if found is None:
        raise NotFoundError("No such household.")
    return found


async def living_mortal(scope: PlayerScope, node_id: int) -> EntityRow:
    found = await scope.session.get(EntityRow, node_id)
    if found is None or found.entity_type is not EntityType.MORTAL or found.status is not EntityStatus.CANON:
        raise ValidationFailedError("Only a living mortal belongs to a household.")
    return found


async def dwelling_row(scope: PlayerScope, home: HouseholdRow) -> DwellingRow | None:
    found: DwellingRow | None = await scope.session.scalar(select(DwellingRow).where(DwellingRow.household_id == home.id))
    return found


@player_action("household:found", ActionKind.EDIT_RECORD)
async def found(scope: PlayerScope, command: FoundHousehold) -> Effect:
    head = await living_mortal(scope, command.head_id)
    existing = await scope.session.get(HouseholdMemberRow, head.id)
    if existing is not None:
        await scope.session.delete(existing)
        await scope.session.flush()
    home = await found_household(await manual_context(scope.session, "household"), head)
    return Effect(f"{head.name} now heads a household of their own.", target_node_id=head.id, values={"household_id": home.id})


@player_action("household:edit", ActionKind.EDIT_RECORD)
async def edit(scope: PlayerScope, command: EditHousehold) -> Effect:
    home = await household(scope, command.household_id)
    touched = [name for name in (*HOUSEHOLD_FIELDS, *PLAIN_FIELDS, "form") if getattr(command, name) is not None]
    for name in touched:
        setattr(home, name, getattr(command, name))
    if command.head_id is not None:
        head = await living_mortal(scope, command.head_id)
        member = await scope.session.get(HouseholdMemberRow, head.id)
        if member is None or member.household_id != home.id:
            raise ValidationFailedError("The head must be a member of the household.")
        home.head_node_id = head.id
        touched.append(MEMBERS)
    if not touched:
        raise ValidationFailedError("Set at least one value.")
    home.locked = held(home.locked, [name for name in touched if name not in PLAIN_FIELDS], command.hold)
    await scope.session.flush()
    return Effect(f"{home.name}: wealth {home.wealth}, income {home.income}, expenses {home.expenses}, burden {home.burden}.")


@player_action("household:debt", ActionKind.EDIT_RECORD)
async def set_debt(scope: PlayerScope, command: SetDebt) -> Effect:
    home = await household(scope, command.household_id)
    lender = await household(scope, command.lender_household_id)
    if lender.id == home.id:
        raise ValidationFailedError("A household cannot owe itself.")
    debts = {key: value for key, value in home.debts.items() if key != str(lender.id)}
    if command.amount:
        debts[str(lender.id)] = command.amount
    home.debts = debts
    home.locked = held(home.locked, ["debts"], command.hold)
    await scope.session.flush()
    return Effect(f"{home.name} owes {lender.name} {command.amount}.")


@player_action("household:hold", ActionKind.EDIT_RECORD)
async def hold(scope: PlayerScope, command: HoldHousehold) -> Effect:
    home = await household(scope, command.household_id)
    allowed = {*HOUSEHOLD_FIELDS, "debts", "decisions", "form", MEMBERS}
    unknown = [name for name in command.fields if name not in allowed]
    if unknown:
        raise ValidationFailedError(f"Unknown field: {', '.join(unknown)}.")
    home.locked = held(home.locked, command.fields, command.hold)
    await scope.session.flush()
    return Effect(f"{home.name}: {'held' if command.hold else 'released'} {', '.join(command.fields)}.")


@player_action("household:remove", ActionKind.EDIT_RECORD)
async def remove(scope: PlayerScope, command: HouseholdTarget) -> Effect:
    home = await household(scope, command.household_id)
    await scope.session.delete(home)
    await scope.session.flush()
    return Effect("The household was dissolved; its people are housed again next epoch.")


@player_action("household:member", ActionKind.EDIT_RECORD)
async def set_member(scope: PlayerScope, command: SetMember) -> Effect:
    home = await household(scope, command.household_id)
    person = await living_mortal(scope, command.mortal_id)
    if command.cares_for_id is not None:
        await living_mortal(scope, command.cares_for_id)
    row = await scope.session.get(HouseholdMemberRow, person.id)
    if row is None:
        row = HouseholdMemberRow(member_node_id=person.id, household_id=home.id, role=command.role, joined_epoch=await scope.epoch())
        scope.session.add(row)
    row.household_id, row.role, row.cares_for_node_id, row.locked = home.id, command.role, command.cares_for_id, command.hold
    if command.role is HouseholdRole.HEAD:
        home.head_node_id = person.id
    await scope.session.flush()
    return Effect(f"{person.name} is {HOUSEHOLD_ROLE_LABELS[command.role].lower()} of {home.name}.", target_node_id=person.id)


@player_action("household:release", ActionKind.EDIT_RECORD)
async def release(scope: PlayerScope, command: MemberTarget) -> Effect:
    row = await scope.session.get(HouseholdMemberRow, command.mortal_id)
    if row is None:
        raise NotFoundError("That mortal belongs to no household.")
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("They left their household; they are housed again next epoch.", target_node_id=command.mortal_id)


@player_action("dwelling:set", ActionKind.EDIT_RECORD)
async def set_dwelling(scope: PlayerScope, command: SetDwelling) -> Effect:
    home = await household(scope, command.household_id)
    row = await dwelling_row(scope, home)
    if command.district_id is not None:
        district = await scope.session.get(DistrictRow, command.district_id)
        if district is None:
            raise ValidationFailedError("No such district.")
    kind = command.kind or (row.kind if row is not None else DwellingKind.HUT)
    if row is None:
        spec = DWELLINGS[kind]
        row = DwellingRow(
            household_id=home.id,
            kind=kind,
            quality=spec.quality,
            rooms=spec.rooms,
            settlement_node_id=home.settlement_node_id,
            built_epoch=await scope.epoch(),
            locked=[],
        )
        scope.session.add(row)
    touched: list[str] = []
    for name in ("kind", "quality", "rooms", "district_id", "tenure", "heating", "light", "crowding"):
        value = getattr(command, name)
        if value is not None:
            setattr(row, name, value)
            touched.append(name)
    if command.clear_district:
        row.district_id = None
        touched.append("district_id")
    row.locked = held(row.locked, touched, command.hold)
    await scope.session.flush()
    return Effect(f"{home.name} lives in {an(DWELLINGS[row.kind].label.lower())} of quality {row.quality} with {several(row.rooms, 'room', 'rooms')}.")


@player_action("dwelling:remove", ActionKind.EDIT_RECORD)
async def remove_dwelling(scope: PlayerScope, command: HouseholdTarget) -> Effect:
    home = await household(scope, command.household_id)
    row = await dwelling_row(scope, home)
    if row is None:
        raise NotFoundError("That household has no home.")
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect(f"{home.name} lost its home.")


@player_action("furnishing:add", ActionKind.EDIT_RECORD)
async def furnish(scope: PlayerScope, command: Furnish) -> Effect:
    home = await household(scope, command.household_id)
    row = await dwelling_row(scope, home)
    if row is None:
        raise ValidationFailedError("That household has no home to furnish.")
    item = await scope.session.get(EntityRow, command.item_id)
    if item is None or item.entity_type not in (EntityType.ITEM, EntityType.ARTWORK) or item.status is not EntityStatus.CANON:
        raise ValidationFailedError("Only a living item or work of art can furnish a home.")
    existing = await scope.session.get(DwellingFurnishingRow, item.id)
    if existing is None:
        scope.session.add(DwellingFurnishingRow(item_node_id=item.id, dwelling_id=row.id, placed_epoch=await scope.epoch()))
    else:
        existing.dwelling_id = row.id
    await scope.session.flush()
    return Effect(f"{item.name} now furnishes the home of {home.name}.", target_node_id=item.id)


@player_action("furnishing:remove", ActionKind.EDIT_RECORD)
async def unfurnish(scope: PlayerScope, command: FurnishingTarget) -> Effect:
    row = await scope.session.get(DwellingFurnishingRow, command.item_id)
    if row is None:
        raise NotFoundError("That item furnishes no home.")
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The furnishing was taken out of the home.", target_node_id=command.item_id)


@player_action("household_aggregate:edit", ActionKind.EDIT_RECORD)
async def edit_aggregate(scope: PlayerScope, command: EditAggregate) -> Effect:
    community = await scope.session.get(EntityRow, command.community_id)
    if community is None or community.entity_type not in COMMUNITY_TYPES:
        raise ValidationFailedError("Only a community keeps anonymous households.")
    row = await scope.session.get(HouseholdAggregateRow, (community.id, command.social_class))
    if row is None:
        row = HouseholdAggregateRow(community_node_id=community.id, social_class=command.social_class, epoch=await scope.epoch(), locked=[])
        scope.session.add(row)
    touched = [name for name in ("households", "mean_size", "dwelling_kind", "quality", "wealth") if getattr(command, name) is not None]
    if not touched:
        raise ValidationFailedError("Set at least one value.")
    for name in touched:
        setattr(row, name, getattr(command, name))
    row.locked = held(row.locked, touched, command.hold)
    await scope.session.flush()
    return Effect(
        f"{community.name}: {several(row.households, 'household', 'households')} of {command.social_class.value.replace('_', ' ')} folk.",
        target_node_id=community.id,
    )


@player_action("household_aggregate:remove", ActionKind.EDIT_RECORD)
async def remove_aggregate(scope: PlayerScope, command: AggregateTarget) -> Effect:
    row = await scope.session.get(HouseholdAggregateRow, (command.community_id, command.social_class))
    if row is None:
        raise NotFoundError("No such record of households.")
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The record of households was struck; it is reckoned anew next epoch.", target_node_id=command.community_id)
