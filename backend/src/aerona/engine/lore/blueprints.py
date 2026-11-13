from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.discovery import BLUEPRINT_KINDS
from aerona.constants.units import PERCENT
from aerona.core.grammar import an
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.culture import ItemProfileRow
from aerona.db.tables.discovery import BlueprintRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import ArmyUnitRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.culture import ItemClass, Technique
from aerona.domain.enums.discovery import BlueprintKind, BlueprintSource
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.military import UnitKind
from aerona.domain.enums.structure import ConstructionState
from aerona.engine.context import TickContext
from aerona.engine.lore.research import has_technique
from aerona.engine.lore.research_depth import trade_partners
from aerona.engine.notes import note
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.stats import move_stat, stat, stat_or
from aerona.rules.registry import Rules

PATTERN_QUALITY = 70
BOOKS = (ItemClass.BOOK, ItemClass.SCROLL)


async def books_of(session: AsyncSession, holder_id: int) -> set[int]:
    keepers = select(EntityRow.id).where(await present_among(session, [holder_id]), EntityRow.entity_type == EntityType.MORTAL)
    owned = await session.scalars(
        select(BondRow.target_node_id)
        .join(ItemProfileRow, ItemProfileRow.item_entity_id == BondRow.target_node_id)
        .where(
            (BondRow.source_node_id == holder_id) | BondRow.source_node_id.in_(keepers),
            BondRow.kind == BondKind.OWNS,
            BondRow.state == BondState.ACTIVE,
            ItemProfileRow.item_class.in_(list(BOOKS)),
        )
    )
    return set(owned)


async def designs_for(session: AsyncSession, holder_id: int, kind: BlueprintKind, subject: str) -> list[BlueprintRow]:
    rows = list(await session.scalars(select(BlueprintRow).where(BlueprintRow.kind == kind, BlueprintRow.subject == subject)))
    shelves = await books_of(session, holder_id) if any(row.book_entity_id is not None for row in rows) else set()
    return [row for row in rows if row.holder_node_id == holder_id or holder_id in (row.licensed_to or []) or row.book_entity_id in shelves]


async def design_factor(session: AsyncSession, rules: Rules, holder_id: int | None, kind: BlueprintKind, subject: str) -> float:
    if holder_id is None:
        return 1.0
    best = max((row.quality for row in await designs_for(session, holder_id, kind, subject)), default=0)
    return 1 + rules.discovery.blueprint_pct * best / PERCENT / PERCENT


async def has_design(session: AsyncSession, holder_id: int, kind: BlueprintKind, subject: str) -> bool:
    found = await session.scalar(
        select(BlueprintRow.id).where(BlueprintRow.holder_node_id == holder_id, BlueprintRow.kind == kind, BlueprintRow.subject == subject).limit(1)
    )
    return found is not None


async def draw(ctx: TickContext, holder: EntityRow, kind: BlueprintKind, subject: str) -> BlueprintRow | None:
    if held(holder.id) or await has_design(ctx.session, holder.id, kind, subject):
        return None
    label = subject.replace("_", " ")
    shelf = sorted(await books_of(ctx.session, holder.id))
    row = BlueprintRow(
        book_entity_id=shelf[0] if shelf else None,
        name=f"{BLUEPRINT_KINDS[kind]}: {label}",
        kind=kind,
        subject=subject,
        holder_node_id=holder.id,
        origin_node_id=holder.id,
        source=BlueprintSource.DRAWN,
        licensed_to=[],
        quality=ctx.rules.discovery.blueprint_quality,
        since_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await note(
        ctx,
        f"The makers of {holder.name} drew {an(BLUEPRINT_KINDS[kind].lower())} of {label}.",
        key="discovery.design_drawn",
        ids=[holder.id],
        kind=ChronicleKind.KNOWLEDGE,
    )
    return row


async def community(session: AsyncSession, node_id: int | None) -> EntityRow | None:
    entity = await session.get(EntityRow, node_id) if node_id is not None else None
    if entity is None or entity.status is not EntityStatus.CANON:
        return None
    if entity.entity_type in COMMUNITY_TYPES:
        return entity
    home = await session.get(EntityRow, entity.location_id) if entity.location_id is not None else None
    return home if home is not None and home.entity_type in COMMUNITY_TYPES and home.status is EntityStatus.CANON else None


async def draw_designs(ctx: TickContext) -> int:
    drawn = 0
    finished = await ctx.session.scalars(
        select(StructureProfileRow).where(
            StructureProfileRow.construction_state == ConstructionState.COMPLETE, StructureProfileRow.built_epoch >= ctx.epoch - 1
        )
    )
    for profile in list(finished):
        host = await community(ctx.session, profile.host_entity_id)
        if host is not None:
            drawn += int(await draw(ctx, host, BlueprintKind.STRUCTURE, profile.kind.value) is not None)
    for vessel in list(await ctx.session.scalars(select(VesselProfileRow).where(VesselProfileRow.home_port_entity_id.is_not(None)))):
        port = await community(ctx.session, vessel.home_port_entity_id)
        if port is not None:
            drawn += int(await draw(ctx, port, BlueprintKind.VESSEL, vessel.frame.value) is not None)
    engines = await ctx.session.execute(
        select(BondRow.target_node_id)
        .join(ArmyUnitRow, ArmyUnitRow.army_entity_id == BondRow.source_node_id)
        .where(BondRow.kind == BondKind.PROTECTS, BondRow.state == BondState.ACTIVE, ArmyUnitRow.kind == UnitKind.SIEGE_CREW, ArmyUnitRow.count > 0)
        .distinct()
    )
    for owner_id in sorted(engines.scalars()):
        owner = await community(ctx.session, owner_id)
        if owner is not None:
            drawn += int(await draw(ctx, owner, BlueprintKind.SIEGE_ENGINE, UnitKind.SIEGE_CREW.value) is not None)
    made = await ctx.session.scalars(
        select(ItemProfileRow)
        .join(EntityRow, EntityRow.id == ItemProfileRow.item_entity_id)
        .where(ItemProfileRow.quality >= PATTERN_QUALITY, EntityRow.birth_epoch >= ctx.epoch - 1)
    )
    for item in list(made):
        maker = await community(ctx.session, item.maker_entity_id)
        if maker is not None:
            drawn += int(await draw(ctx, maker, BlueprintKind.ARTIFACT_PATTERN, item.item_class.value) is not None)
    await ctx.session.flush()
    return drawn


async def copy_design(ctx: TickContext, row: BlueprintRow, buyer_id: int, source: BlueprintSource) -> BlueprintRow:
    copy = BlueprintRow(
        name=row.name,
        kind=row.kind,
        subject=row.subject,
        holder_node_id=buyer_id,
        book_entity_id=None,
        origin_node_id=row.origin_node_id,
        source=source,
        licensed_to=[],
        quality=row.quality,
        since_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(copy)
    return copy


def pay(payer: EntityRow, payee: EntityRow, amount: int) -> bool:
    if held(payer.id) or held(payee.id) or (stat(payer, "wealth") or 0) < amount or PERCENT - stat_or(payee, "wealth", PERCENT) < amount:
        return False
    return move_stat(payer, payee, "wealth", amount) == amount


async def trade_designs(ctx: TickContext) -> dict[str, int]:
    table = ctx.rules.discovery
    sold = licensed = 0
    for row in list(await ctx.session.scalars(select(BlueprintRow).where(BlueprintRow.source != BlueprintSource.LICENSED).order_by(BlueprintRow.id))):
        holder = await community(ctx.session, row.holder_node_id)
        if holder is None or "licensed_to" in row.locked:
            continue
        guild = await has_technique(ctx.session, holder.id, Technique.GUILDS)
        for partner_id in sorted(await trade_partners(ctx.session, holder.id)):
            partner = await community(ctx.session, partner_id)
            if partner is None or partner.id == holder.id or await designs_for(ctx.session, partner.id, row.kind, row.subject):
                continue
            if not ctx.rng(f"design.trade.{row.id}.{partner.id}.{ctx.epoch}").chance(table.blueprint_trade_pct):
                continue
            if guild:
                row.licensed_to = [*(row.licensed_to or []), partner.id]
                licensed += 1
            elif pay(partner, holder, table.blueprint_price):
                await copy_design(ctx, row, partner.id, BlueprintSource.TRADED)
                sold += 1
    await ctx.session.flush()
    return {"designs_sold": sold, "designs_licensed": licensed}


async def collect_fees(ctx: TickContext) -> int:
    fee = ctx.rules.discovery.licence_fee
    paid = 0
    for row in list(await ctx.session.scalars(select(BlueprintRow).order_by(BlueprintRow.id))):
        holder = await community(ctx.session, row.holder_node_id)
        if holder is None or not row.licensed_to:
            continue
        for licensee_id in list(row.licensed_to):
            licensee = await community(ctx.session, licensee_id)
            if licensee is not None and pay(licensee, holder, fee):
                paid += 1
    return paid


async def steal_design(ctx: TickContext, thief_id: int, victim_id: int) -> BlueprintRow | None:
    if held(thief_id) or not ctx.rng(f"design.theft.{thief_id}.{victim_id}.{ctx.epoch}").chance(ctx.rules.discovery.blueprint_theft_pct):
        return None
    for row in list(await ctx.session.scalars(select(BlueprintRow).where(BlueprintRow.holder_node_id == victim_id).order_by(BlueprintRow.id))):
        if not await designs_for(ctx.session, thief_id, row.kind, row.subject):
            return await copy_design(ctx, row, thief_id, BlueprintSource.STOLEN)
    return None


async def blueprints(ctx: TickContext) -> dict[str, int]:
    return {"designs_drawn": await draw_designs(ctx), **await trade_designs(ctx), "licence_fees": await collect_fees(ctx)}
