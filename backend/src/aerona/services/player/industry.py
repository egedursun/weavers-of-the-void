from pydantic import Field
from sqlalchemy import select

from aerona.catalog.methods import ENERGY_LABELS, METHODS, POLLUTANT_LABELS, PROCESS_LABELS
from aerona.catalog.production import WORKSHOP_LABELS
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.economy import WorkshopRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.industry import ENERGY_COLUMNS, POLLUTION_COLUMNS, CommunityIndustryRow, CommunityMethodRow, RegionPollutionRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.ownership import LEDGER_COLUMNS, SiteProfitRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.economy import WorkshopKind
from aerona.domain.enums.entity import SOCIETY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.industry import EnergyKind, MethodKind, Pollutant, ProcessKind
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

SPAN = 100
STORE_FIELDS = ("heat_need", "tools_worn", "spoiled", "preserved", "meal_quality", "drink")


class SetMethod(Command):
    community_id: int
    method: MethodKind
    hold: bool = True


class MethodTarget(Command):
    community_id: int
    process: ProcessKind


class SetIndustry(Command):
    community_id: int
    muscle: int | None = Field(default=None, ge=0)
    water: int | None = Field(default=None, ge=0)
    wind: int | None = Field(default=None, ge=0)
    heat: int | None = Field(default=None, ge=0)
    magic: int | None = Field(default=None, ge=0)
    divine: int | None = Field(default=None, ge=0)
    heat_need: int | None = Field(default=None, ge=0)
    tools_worn: int | None = Field(default=None, ge=0)
    spoiled: int | None = Field(default=None, ge=0)
    preserved: int | None = Field(default=None, ge=0)
    meal_quality: int | None = Field(default=None, ge=0, le=SPAN)
    drink: int | None = Field(default=None, ge=0, le=SPAN)
    hold: bool = True


class IndustryTarget(Command):
    community_id: int


class SetPollution(Command):
    region_id: int
    air: int | None = Field(default=None, ge=0, le=SPAN)
    water: int | None = Field(default=None, ge=0, le=SPAN)
    soil: int | None = Field(default=None, ge=0, le=SPAN)
    hold: bool = True


class PurifyLand(Command):
    region_id: int
    amount: int = Field(default=30, ge=1, le=SPAN)


class PollutionTarget(Command):
    region_id: int


class SetWorkshopOwner(Command):
    community_id: int
    kind: WorkshopKind
    owner_id: int | None = None
    hold: bool = True


class EditSiteProfit(Command):
    profit_id: int
    revenue: int | None = Field(default=None, ge=0)
    inputs: int | None = Field(default=None, ge=0)
    wages: int | None = Field(default=None, ge=0)
    upkeep: int | None = Field(default=None, ge=0)
    taxes: int | None = Field(default=None, ge=0)
    invested: int | None = Field(default=None, ge=0)
    profit: int | None = None


class SiteProfitTarget(Command):
    profit_id: int


def held(locked: list[str] | None, fields: list[str], hold: bool) -> list[str]:
    found = set(locked or [])
    return sorted(found | set(fields)) if hold else sorted(found - set(fields))


async def community(scope: PlayerScope, node_id: int) -> EntityRow:
    found = await scope.session.get(EntityRow, node_id)
    if found is None or found.entity_type not in SOCIETY_TYPES or found.status is not EntityStatus.CANON:
        raise ValidationFailedError("Only a living settlement, people or other community keeps works.")
    return found


async def region(scope: PlayerScope, node_id: int) -> EntityRow:
    found = await scope.session.get(EntityRow, node_id)
    if found is None or found.entity_type is not EntityType.REGION:
        raise ValidationFailedError("Pollution lies on a region of land or sea.")
    return found


async def method_row(scope: PlayerScope, community_id: int, process: ProcessKind) -> CommunityMethodRow | None:
    return await scope.session.scalar(
        select(CommunityMethodRow).where(CommunityMethodRow.community_node_id == community_id, CommunityMethodRow.process == process)
    )


@player_action("method:set", ActionKind.EDIT_RECORD)
async def set_method(scope: PlayerScope, command: SetMethod) -> Effect:
    place = await community(scope, command.community_id)
    spec = METHODS[command.method]
    row = await method_row(scope, place.id, spec.process)
    if row is None:
        row = CommunityMethodRow(community_node_id=place.id, process=spec.process, method=spec.kind, adopted_epoch=await scope.epoch(), displaced=0, locked=[])
        scope.session.add(row)
    row.method, row.adopted_epoch = spec.kind, await scope.epoch()
    row.locked = held(row.locked, ["method"], command.hold)
    await scope.session.flush()
    return Effect(
        f"{place.name} now practises {spec.label.lower()} for {PROCESS_LABELS[spec.process].lower()}.", target_node_id=place.id, values={"method_id": row.id}
    )


@player_action("method:remove", ActionKind.EDIT_RECORD)
async def remove_method(scope: PlayerScope, command: MethodTarget) -> Effect:
    row = await method_row(scope, command.community_id, command.process)
    if row is None:
        raise NotFoundError("That place keeps no chosen method for this work.")
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect(f"{PROCESS_LABELS[command.process]} returns to the oldest way until the place chooses again.", target_node_id=command.community_id)


@player_action("industry:set", ActionKind.EDIT_RECORD)
async def set_industry(scope: PlayerScope, command: SetIndustry) -> Effect:
    place = await community(scope, command.community_id)
    row = await scope.session.get(CommunityIndustryRow, place.id)
    if row is None:
        row = CommunityIndustryRow(community_node_id=place.id, spent={}, short={}, epoch=await scope.epoch(), locked=[], meal_quality=50)
        scope.session.add(row)
    touched = [name for name in (*ENERGY_COLUMNS, *STORE_FIELDS) if getattr(command, name) is not None]
    if not touched:
        raise ValidationFailedError("Set at least one value.")
    for name in touched:
        setattr(row, name, getattr(command, name))
    row.locked = held(row.locked, touched, command.hold)
    await scope.session.flush()
    told = ", ".join(f"{ENERGY_LABELS[EnergyKind(name)].lower()} {getattr(row, name)}" for name in ENERGY_COLUMNS)
    return Effect(f"The works of {place.name} run on {told}.", target_node_id=place.id)


@player_action("industry:remove", ActionKind.EDIT_RECORD)
async def remove_industry(scope: PlayerScope, command: IndustryTarget) -> Effect:
    row = await scope.session.get(CommunityIndustryRow, command.community_id)
    if row is None:
        raise NotFoundError("That place keeps no record of its energy and stores.")
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The record of its energy and stores was wiped; it is reckoned anew next epoch.", target_node_id=command.community_id)


async def pollution_row(scope: PlayerScope, region_id: int) -> RegionPollutionRow:
    row = await scope.session.get(RegionPollutionRow, region_id)
    if row is None:
        row = RegionPollutionRow(region_node_id=region_id, air=0, water=0, soil=0, polluters={}, epoch=await scope.epoch(), locked=[])
        scope.session.add(row)
    return row


@player_action("pollution:set", ActionKind.EDIT_RECORD)
async def set_pollution(scope: PlayerScope, command: SetPollution) -> Effect:
    land = await region(scope, command.region_id)
    row = await pollution_row(scope, land.id)
    touched = [name for name in POLLUTION_COLUMNS if getattr(command, name) is not None]
    if not touched:
        raise ValidationFailedError("Set at least one kind of pollution.")
    for name in touched:
        setattr(row, name, getattr(command, name))
    row.locked = held(row.locked, touched, command.hold)
    await scope.session.flush()
    told = ", ".join(f"{POLLUTANT_LABELS[Pollutant(name)].lower()} {getattr(row, name)}" for name in POLLUTION_COLUMNS)
    return Effect(f"The land of {land.name} is fouled: {told}.", target_node_id=land.id)


@player_action("pollution:purify", ActionKind.EDIT_RECORD)
async def purify(scope: PlayerScope, command: PurifyLand) -> Effect:
    land = await region(scope, command.region_id)
    row = await pollution_row(scope, land.id)
    for name in POLLUTION_COLUMNS:
        setattr(row, name, max(0, int(getattr(row, name)) - command.amount))
    await scope.session.flush()
    return Effect(f"The air, water and soil of {land.name} run clean again.", target_node_id=land.id)


@player_action("pollution:remove", ActionKind.EDIT_RECORD)
async def remove_pollution(scope: PlayerScope, command: PollutionTarget) -> Effect:
    row = await scope.session.get(RegionPollutionRow, command.region_id)
    if row is None:
        raise NotFoundError("That land carries no record of pollution.")
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The record of its pollution was wiped.", target_node_id=command.region_id)


@player_action("workshop:owner", ActionKind.EDIT_RECORD)
async def set_workshop_owner(scope: PlayerScope, command: SetWorkshopOwner) -> Effect:
    place = await community(scope, command.community_id)
    workshop = await scope.session.scalar(select(WorkshopRow).where(WorkshopRow.community_entity_id == place.id, WorkshopRow.kind == command.kind))
    if workshop is None:
        raise NotFoundError("That place has no such workshop.")
    if command.owner_id is not None and await scope.session.get(NodeRow, command.owner_id) is None:
        raise ValidationFailedError("That owner does not exist.")
    workshop.owner_node_id = command.owner_id
    workshop.held = command.hold
    await scope.session.flush()
    owner = await scope.session.get(NodeRow, command.owner_id) if command.owner_id is not None else None
    told = f"now belongs to {owner.name}" if owner is not None else "has no owner until the place assigns one"
    return Effect(f"The {WORKSHOP_LABELS[command.kind].lower()} of {place.name} {told}.", target_node_id=command.owner_id or place.id)


@player_action("site_profit:edit", ActionKind.EDIT_RECORD)
async def edit_site_profit(scope: PlayerScope, command: EditSiteProfit) -> Effect:
    row = await scope.session.get(SiteProfitRow, command.profit_id)
    if row is None:
        raise NotFoundError("No such entry in the ledger of profits.")
    touched = [name for name in (*LEDGER_COLUMNS, "profit") if getattr(command, name) is not None]
    if not touched:
        raise ValidationFailedError("Set at least one figure.")
    for name in touched:
        setattr(row, name, getattr(command, name))
    row.locked = sorted(set(row.locked or []) | set(touched))
    await scope.session.flush()
    site = row.site.replace("_", " ")
    return Effect(f"The ledger now shows a profit of {row.profit} from {site}.", target_node_id=row.owner_node_id or row.community_node_id)


@player_action("site_profit:remove", ActionKind.EDIT_RECORD)
async def remove_site_profit(scope: PlayerScope, command: SiteProfitTarget) -> Effect:
    row = await scope.session.get(SiteProfitRow, command.profit_id)
    if row is None:
        raise NotFoundError("No such entry in the ledger of profits.")
    target = row.owner_node_id or row.community_node_id
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The entry was struck from the ledger of profits.", target_node_id=target)
