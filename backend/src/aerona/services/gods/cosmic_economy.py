from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.cosmic_state import AddictionImmunityRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.routes import RouteRow
from aerona.db.tables.society import AddictionRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, LOCATION_TYPES, EngineKind, EntityStatus, EntityType
from aerona.engine.context import Publisher
from aerona.engine.gods.economy import cosmic_economy, create_deposit, found_faction, monopoly, resource_mechanics
from aerona.engine.gods.queries import cosmos_row
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.numbers import clamp_int
from aerona.rules.registry import Rules
from aerona.services.gods.context import record_action, require

DEPOSIT_PLACES = frozenset({EntityType.REGION, EntityType.PLACE})


async def run_resource_mechanics(session: AsyncSession, rules: Rules, publish: Publisher | None = None) -> None:
    await resource_mechanics(await manual_context(session, "resource_mechanics", rules, publish))


async def run_cosmic_economy(session: AsyncSession, rules: Rules, publish: Publisher | None = None) -> None:
    await cosmic_economy(await manual_context(session, "cosmic_economy", rules, publish))


async def open_deposit(session: AsyncSession, rules: Rules, place_id: int) -> EntityRow:
    ctx = await manual_context(session, "open_deposit", rules)
    place = require(await session.get(EntityRow, place_id), "record")
    if place.entity_type not in DEPOSIT_PLACES or place.status is not EntityStatus.CANON:
        raise ValidationFailedError("A deposit can only be opened in a living region or place.")
    cosmos = await cosmos_row(session)
    if cosmos is None or cosmos.travel_resource is None:
        raise ValidationFailedError("Define the cosmos's travel resource first.")
    deposit = await create_deposit(ctx, place)
    if deposit is None:
        raise ValidationFailedError("Define the cosmos's travel resource first.")
    await record_action(ctx, ActionKind.OPEN_COSMIC_BED, deposit.id)
    return deposit


async def set_deposit_owner(session: AsyncSession, rules: Rules, deposit_id: int, owner_id: int | None) -> None:
    ctx = await manual_context(session, "deposit_owner", rules)
    deposit = require(await session.get(EntityRow, deposit_id), "record")
    if deposit.engine_kind is not EngineKind.COSMIC_TRAVEL_RESOURCE:
        raise ValidationFailedError(f"{deposit.name} is not a cosmic deposit.")
    bonds = BondRepository(session)
    for bond in await bonds.incoming(deposit.id, BondKind.OWNS):
        await bonds.deactivate(bond, ctx.epoch, "reassigned")
    if owner_id is not None:
        owner = require(await session.get(EntityRow, owner_id), "record")
        if owner.entity_type not in COMMUNITY_TYPES or owner.status is not EntityStatus.CANON:
            raise ValidationFailedError("Only a living community can own a deposit.")
        await bonds.connect(BondDraft(owner.id, deposit.id, BondKind.OWNS, ctx.epoch))
    await monopoly(ctx)
    await record_action(ctx, ActionKind.CLAIM, deposit.id)


async def found_wandering_market(session: AsyncSession, rules: Rules, region_id: int) -> EntityRow:
    return await _found(session, rules, region_id, EngineKind.WANDERING_MARKET)


async def spawn_route_raiders(session: AsyncSession, rules: Rules, region_id: int) -> EntityRow:
    return await _found(session, rules, region_id, EngineKind.ROUTE_RAIDERS)


async def _found(session: AsyncSession, rules: Rules, region_id: int, kind: EngineKind) -> EntityRow:
    ctx = await manual_context(session, f"found.{kind.value}", rules)
    region = require(await session.get(EntityRow, region_id), "record")
    if region.entity_type not in LOCATION_TYPES or region.status is not EntityStatus.CANON:
        raise ValidationFailedError("Choose a living region, place or settlement.")
    faction = await found_faction(ctx, kind, region)
    await record_action(ctx, ActionKind.CREATE_ENTITY, faction.id)
    return faction


async def disband_faction(session: AsyncSession, rules: Rules, faction_id: int) -> EntityRow:
    ctx = await manual_context(session, "disband", rules)
    faction = require(await session.get(EntityRow, faction_id), "record")
    if faction.engine_kind not in (EngineKind.WANDERING_MARKET, EngineKind.ROUTE_RAIDERS) or faction.status is not EntityStatus.CANON:
        raise ValidationFailedError("Only a living wandering market or pirate band can be disbanded.")
    await EntityRepository(session).set_status(faction, EntityStatus.DESTROYED, ctx.epoch)
    await record_action(ctx, ActionKind.DESTROY, faction.id)
    return faction


async def cure_addiction(session: AsyncSession, rules: Rules, entity_id: int, resource_id: int) -> bool:
    ctx = await manual_context(session, "cure_addiction", rules)
    row = await session.get(AddictionRow, (entity_id, resource_id))
    if row is None or row.addicted_since_epoch is None:
        return False
    row.addicted_since_epoch = None
    row.withdrawal_since_epoch = None
    await session.merge(AddictionImmunityRow(community_entity_id=entity_id, resource_entity_id=resource_id, recovered_epoch=ctx.epoch))
    await record_action(ctx, ActionKind.MIRACLE, entity_id)
    return True


async def set_route_danger(session: AsyncSession, rules: Rules, route_id: int, danger: int) -> RouteRow:
    ctx = await manual_context(session, "route_danger", rules)
    route = require(await session.get(RouteRow, route_id), "route")
    route.danger = clamp_int(danger, rules.travel.route_danger_min, rules.travel.route_danger_max)
    await record_action(ctx, ActionKind.OTHER)
    return route
