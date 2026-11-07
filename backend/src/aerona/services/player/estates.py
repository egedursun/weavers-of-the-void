from pydantic import Field
from sqlalchemy import delete

from aerona.catalog.estates import CAUSE_LABELS, ESTATE_NAMES, PRIVILEGE_LABELS
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import an
from aerona.db.tables.culture import HolderTechniqueRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.estates import (
    CompanyProfileRow,
    CompanyShareRow,
    EstatePrivilegeRow,
    EstateProfileRow,
    GuildSecretRow,
    HolyOrderProfileRow,
    MovementProfileRow,
    MovementSupportRow,
)
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.node import NodeRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faction import EstatePrivilege, FactionKind, MovementCause
from aerona.domain.enums.society import SocialClass
from aerona.engine.factions.estates import found_estate
from aerona.engine.factions.movements import found_movement
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.laws import LawBook
from aerona.engine.primitives.manual import manual_context
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

SPAN = 100


class FoundEstate(Command):
    realm_id: int
    social_class: SocialClass


class EstateTarget(Command):
    estate_id: int


class EditEstate(Command):
    estate_id: int
    loyalty: int | None = Field(default=None, ge=0, le=SPAN)
    influence: int | None = Field(default=None, ge=0, le=SPAN)
    hold: bool = True


class SetPrivilege(Command):
    estate_id: int
    privilege: EstatePrivilege
    grant: bool = True
    granted_epoch: int | None = Field(default=None, ge=0)
    hold: bool = True


class FoundMovement(Command):
    realm_id: int
    cause: MovementCause
    home_id: int


class MovementTarget(Command):
    movement_id: int


class EditMovement(Command):
    movement_id: int
    support: int | None = Field(default=None, ge=0, le=SPAN)
    is_party: bool | None = None
    cause: MovementCause | None = None
    hold: bool = True


class SetSupport(Command):
    movement_id: int
    community_id: int
    share: int = Field(ge=0, le=SPAN)
    hold: bool = True


class SupportTarget(Command):
    movement_id: int
    community_id: int


class EditCompany(Command):
    company_id: int
    dividend_pct: int | None = Field(default=None, ge=0, le=SPAN)
    route_id: int | None = None
    region_id: int | None = None
    commodity: CommodityKind | None = None
    chartered_epoch: int | None = Field(default=None, ge=0)
    hold: bool = True


class CompanyTarget(Command):
    company_id: int


class SetShare(Command):
    company_id: int
    holder_id: int
    share: int = Field(ge=0, le=SPAN)
    hold: bool = True


class ShareTarget(Command):
    company_id: int
    holder_id: int


class EditOrder(Command):
    order_id: int
    fortress_id: int | None = None
    cult_id: int | None = None
    tithe_share: int | None = Field(default=None, ge=0, le=SPAN)
    hold: bool = True


class OrderTarget(Command):
    order_id: int


class SetSecret(Command):
    guild_id: int
    technique: Technique
    keep: bool = True


def held(locked: list[str] | None, fields: list[str], hold: bool) -> list[str]:
    found = set(locked or [])
    return sorted(found | set(fields)) if hold else sorted(found - set(fields))


async def entity(scope: PlayerScope, entity_id: int | None, label: str, kinds: frozenset[EntityType]) -> EntityRow:
    found = await scope.session.get(EntityRow, entity_id) if entity_id is not None else None
    if found is None or found.entity_type not in kinds:
        raise ValidationFailedError(f"{label} is not the right kind of record.")
    return found


async def row_of[T](scope: PlayerScope, table: type[T], key: int, label: str) -> T:
    found = await scope.session.get(table, key)
    if found is None:
        raise NotFoundError(f"No such {label}.")
    return found


async def faction_kind(scope: PlayerScope, faction_id: int, kind: FactionKind) -> FactionProfileRow:
    profile = await scope.session.get(FactionProfileRow, faction_id)
    if profile is None or profile.kind is not kind:
        raise ValidationFailedError(f"That faction is not {an(kind.value.replace('_', ' '))}.")
    return profile


@player_action("estate:found", ActionKind.EDIT_RECORD)
async def found(scope: PlayerScope, command: FoundEstate) -> Effect:
    await entity(scope, command.realm_id, "The realm", frozenset({EntityType.POLITY}))
    realm = (await RealmBook.load(scope.session)).realms.get(command.realm_id)
    if realm is None or realm.profile.capital_entity_id is None:
        raise ValidationFailedError("The realm has no seat for an estate to gather in.")
    row = await found_estate(await manual_context(scope.session, "estate.found"), realm, command.social_class)
    return Effect(f"The {ESTATE_NAMES[command.social_class].lower()} of {realm.entity.name} gathered as an estate.", target_node_id=row.faction_entity_id)


@player_action("estate:edit", ActionKind.EDIT_RECORD)
async def edit(scope: PlayerScope, command: EditEstate) -> Effect:
    row = await row_of(scope, EstateProfileRow, command.estate_id, "estate")
    touched = [name for name in ("loyalty", "influence") if getattr(command, name) is not None]
    for name in touched:
        setattr(row, name, getattr(command, name))
    if not touched:
        raise ValidationFailedError("Set the loyalty or the influence.")
    row.locked = held(row.locked, touched, command.hold)
    await scope.session.flush()
    return Effect(f"Loyalty {row.loyalty}, influence {row.influence}.", target_node_id=row.faction_entity_id)


@player_action("estate:privilege", ActionKind.EDIT_RECORD)
async def privilege(scope: PlayerScope, command: SetPrivilege) -> Effect:
    row = await row_of(scope, EstateProfileRow, command.estate_id, "estate")
    found_row = await scope.session.get(EstatePrivilegeRow, (row.faction_entity_id, command.privilege))
    if command.grant:
        if found_row is None:
            found_row = EstatePrivilegeRow(estate_entity_id=row.faction_entity_id, privilege=command.privilege, granted_epoch=await scope.epoch())
            scope.session.add(found_row)
        if command.granted_epoch is not None:
            found_row.granted_epoch = command.granted_epoch
        found_row.locked = command.hold
    elif found_row is not None:
        await scope.session.delete(found_row)
    row.locked = held(row.locked, ["privileges"], command.hold)
    await scope.session.flush()
    verb = "granted" if command.grant else "taken back"
    return Effect(f"{PRIVILEGE_LABELS[command.privilege]} was {verb}.", target_node_id=row.faction_entity_id)


@player_action("estate:remove", ActionKind.EDIT_RECORD)
async def remove(scope: PlayerScope, command: EstateTarget) -> Effect:
    row = await row_of(scope, EstateProfileRow, command.estate_id, "estate")
    await scope.session.execute(delete(EstatePrivilegeRow).where(EstatePrivilegeRow.estate_entity_id == row.faction_entity_id))
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The estate's standing was struck; the faction remains.", target_node_id=command.estate_id)


@player_action("movement:found", ActionKind.EDIT_RECORD)
async def found_cause(scope: PlayerScope, command: FoundMovement) -> Effect:
    await entity(scope, command.realm_id, "The realm", frozenset({EntityType.POLITY}))
    home = await entity(scope, command.home_id, "The home", frozenset({EntityType.SETTLEMENT, EntityType.PEOPLE}))
    realm = (await RealmBook.load(scope.session)).realms.get(command.realm_id)
    if realm is None:
        raise ValidationFailedError("No such realm.")
    row = await found_movement(await manual_context(scope.session, "movement.found"), realm, command.cause, home, await LawBook.load(scope.session))
    return Effect(f"A movement for {CAUSE_LABELS[command.cause].lower()} rose in {home.name}.", target_node_id=row.faction_entity_id)


@player_action("movement:edit", ActionKind.EDIT_RECORD)
async def edit_movement(scope: PlayerScope, command: EditMovement) -> Effect:
    row = await row_of(scope, MovementProfileRow, command.movement_id, "movement")
    touched = [name for name in ("support", "is_party", "cause") if getattr(command, name) is not None]
    for name in touched:
        setattr(row, name, getattr(command, name))
    if command.is_party is not None:
        profile = await scope.session.get(FactionProfileRow, row.faction_entity_id)
        if profile is not None:
            profile.kind = FactionKind.PARTY if command.is_party else FactionKind.MOVEMENT
    if not touched:
        raise ValidationFailedError("Set at least one value.")
    row.locked = held(row.locked, touched, command.hold)
    await scope.session.flush()
    return Effect(
        f"{an('party' if row.is_party else 'movement', capital=True)} for {CAUSE_LABELS[row.cause].lower()}, {row.support}% behind it.",
        target_node_id=row.faction_entity_id,
    )


@player_action("movement:support", ActionKind.EDIT_RECORD)
async def set_support(scope: PlayerScope, command: SetSupport) -> Effect:
    row = await row_of(scope, MovementProfileRow, command.movement_id, "movement")
    community = await entity(scope, command.community_id, "The community", frozenset({EntityType.SETTLEMENT, EntityType.PEOPLE}))
    support = await scope.session.get(MovementSupportRow, (row.faction_entity_id, community.id))
    if support is None:
        support = MovementSupportRow(movement_entity_id=row.faction_entity_id, community_entity_id=community.id, share=0)
        scope.session.add(support)
    support.share, support.locked = command.share, command.hold
    await scope.session.flush()
    return Effect(f"{command.share}% of {community.name} now stand behind the movement.", target_node_id=row.faction_entity_id)


@player_action("movement:support_remove", ActionKind.EDIT_RECORD)
async def remove_support(scope: PlayerScope, command: SupportTarget) -> Effect:
    support = await scope.session.get(MovementSupportRow, (command.movement_id, command.community_id))
    if support is None:
        raise NotFoundError("No such support.")
    await scope.session.delete(support)
    await scope.session.flush()
    return Effect("That community's support was wiped.", target_node_id=command.movement_id)


@player_action("movement:remove", ActionKind.EDIT_RECORD)
async def remove_movement(scope: PlayerScope, command: MovementTarget) -> Effect:
    row = await row_of(scope, MovementProfileRow, command.movement_id, "movement")
    await scope.session.execute(delete(MovementSupportRow).where(MovementSupportRow.movement_entity_id == row.faction_entity_id))
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The movement's cause was struck; the faction remains.", target_node_id=command.movement_id)


@player_action("company:edit", ActionKind.EDIT_RECORD)
async def edit_company(scope: PlayerScope, command: EditCompany) -> Effect:
    row = await scope.session.get(CompanyProfileRow, command.company_id)
    if row is None:
        await faction_kind(scope, command.company_id, FactionKind.CHARTERED_COMPANY)
        row = CompanyProfileRow(faction_entity_id=command.company_id, chartered_epoch=await scope.epoch(), locked=[])
        scope.session.add(row)
    touched: list[str] = []
    if command.dividend_pct is not None:
        row.dividend_pct = command.dividend_pct
        touched.append("dividend_pct")
    if command.route_id is not None:
        row.route_entity_id = (await entity(scope, command.route_id, "The route", frozenset({EntityType.TRADE_ROUTE}))).id
        touched.append("route_entity_id")
    if command.region_id is not None:
        row.region_entity_id = (await entity(scope, command.region_id, "The land", frozenset({EntityType.REGION}))).id
        touched.append("region_entity_id")
    if command.commodity is not None:
        row.commodity = command.commodity
        touched.append("commodity")
    if command.chartered_epoch is not None:
        row.chartered_epoch = command.chartered_epoch
    row.locked = held(row.locked, touched, command.hold)
    await scope.session.flush()
    return Effect(f"The company pays {row.dividend_pct}% to its shareholders.", target_node_id=command.company_id)


@player_action("company:share", ActionKind.EDIT_RECORD)
async def set_share(scope: PlayerScope, command: SetShare) -> Effect:
    await row_of(scope, CompanyProfileRow, command.company_id, "company")
    if await scope.session.get(NodeRow, command.holder_id) is None:
        raise ValidationFailedError("The shareholder must be a living thing of the cosmos.")
    share = await scope.session.get(CompanyShareRow, (command.company_id, command.holder_id))
    if share is None:
        share = CompanyShareRow(company_entity_id=command.company_id, holder_node_id=command.holder_id, share=0)
        scope.session.add(share)
    share.share, share.locked = command.share, command.hold
    await scope.session.flush()
    return Effect(f"The shareholder now holds {command.share}% of the company.", target_node_id=command.company_id)


@player_action("company:share_remove", ActionKind.EDIT_RECORD)
async def remove_share(scope: PlayerScope, command: ShareTarget) -> Effect:
    share = await scope.session.get(CompanyShareRow, (command.company_id, command.holder_id))
    if share is None:
        raise NotFoundError("No such share.")
    await scope.session.delete(share)
    await scope.session.flush()
    return Effect("The share was struck.", target_node_id=command.company_id)


@player_action("company:remove", ActionKind.EDIT_RECORD)
async def remove_company(scope: PlayerScope, command: CompanyTarget) -> Effect:
    row = await row_of(scope, CompanyProfileRow, command.company_id, "company")
    await scope.session.execute(delete(CompanyShareRow).where(CompanyShareRow.company_entity_id == row.faction_entity_id))
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The company's charter was struck; the faction remains.", target_node_id=command.company_id)


@player_action("holy_order:edit", ActionKind.EDIT_RECORD)
async def edit_order(scope: PlayerScope, command: EditOrder) -> Effect:
    row = await scope.session.get(HolyOrderProfileRow, command.order_id)
    if row is None:
        await faction_kind(scope, command.order_id, FactionKind.HOLY_ORDER)
        row = HolyOrderProfileRow(faction_entity_id=command.order_id, locked=[])
        scope.session.add(row)
    touched: list[str] = []
    if command.fortress_id is not None:
        row.fortress_entity_id = (await entity(scope, command.fortress_id, "The fortress", frozenset({EntityType.SETTLEMENT}))).id
        touched.append("fortress_entity_id")
    if command.cult_id is not None:
        row.cult_entity_id = (await entity(scope, command.cult_id, "The faith", frozenset({EntityType.CULT}))).id
        touched.append("cult_entity_id")
    if command.tithe_share is not None:
        row.tithe_share = command.tithe_share
        touched.append("tithe_share")
    row.locked = held(row.locked, touched, command.hold)
    await scope.session.flush()
    return Effect(f"The holy order draws {row.tithe_share}% of its faith's tithes.", target_node_id=command.order_id)


@player_action("holy_order:remove", ActionKind.EDIT_RECORD)
async def remove_order(scope: PlayerScope, command: OrderTarget) -> Effect:
    row = await row_of(scope, HolyOrderProfileRow, command.order_id, "holy order")
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The order's vows were struck; the faction remains.", target_node_id=command.order_id)


@player_action("guild:secret", ActionKind.EDIT_RECORD)
async def secret(scope: PlayerScope, command: SetSecret) -> Effect:
    guild = await row_of(scope, FactionProfileRow, command.guild_id, "guild")
    if guild.kind not in {FactionKind.CRAFT_GUILD, FactionKind.MERCHANT_GUILD} or guild.home_entity_id is None:
        raise ValidationFailedError("Only a guild with a home town keeps craft secrets.")
    known = await scope.session.get(HolderTechniqueRow, (guild.home_entity_id, command.technique))
    row = await scope.session.get(GuildSecretRow, (command.guild_id, command.technique))
    if command.keep:
        if known is None:
            raise ValidationFailedError("The guild's town does not know that technique.")
        known.secret = True
        if row is None:
            scope.session.add(GuildSecretRow(guild_entity_id=command.guild_id, technique=command.technique, since_epoch=await scope.epoch(), locked=True))
    else:
        if known is not None:
            known.secret = False
        if row is not None:
            await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The guild keeps it secret." if command.keep else "The guild's secret is out.", target_node_id=command.guild_id)
