from sqlalchemy import select

from aerona.catalog.materials import LUXURY_MATERIALS
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.economy import MaterialSlot
from aerona.domain.enums.entity import SOCIETY_TYPES, EngineKind, EntityStatus, EntityType
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import FactUnit, StepAction
from aerona.engine.context import TickContext
from aerona.engine.economy.materials import MIDDLE, MaterialBook, node_material, worth
from aerona.engine.economy.money import inject_hoard
from aerona.engine.economy.stocks import sync_aggregates
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.recording.record import StepDraft, record


async def temples_in(ctx: TickContext, place_id: int) -> list[EntityRow]:
    statement = select(EntityRow).where(
        EntityRow.location_id == place_id,
        EntityRow.entity_type == EntityType.STRUCTURE,
        EntityRow.engine_kind == EngineKind.TEMPLE,
        EntityRow.status == EntityStatus.CANON,
    )
    return list(await ctx.session.scalars(statement.order_by(EntityRow.id)))


async def temple_hoard(ctx: TickContext, temple: EntityRow, book: MaterialBook) -> tuple[int, MaterialKind]:
    table = ctx.rules.money
    node = await node_material(ctx.session, temple.id, MaterialSlot.BODY)
    props = book.props(temple.world_id, node.material, node.world_material_id) if node is not None else None
    lift = (worth(props) - MIDDLE) / PERCENT * table.temple_worth_pct / PERCENT if props is not None else 0.0
    units = max(1, round_half_up(table.temple_hoard_units * (1 + lift)))
    metal = node.material if node is not None and node.material in LUXURY_MATERIALS else MaterialKind.GOLD
    return units, metal


async def loot_temple(ctx: TickContext, temple: EntityRow, looter: EntityRow, *, book: MaterialBook | None = None) -> int:
    if looter.entity_type not in SOCIETY_TYPES:
        return 0
    materials = book if book is not None else await MaterialBook.load(ctx.session)
    units, metal = await temple_hoard(ctx, temple, materials)
    added = await inject_hoard(ctx, looter, units, metal)
    await sync_aggregates(ctx.session, ctx.rules, looter)
    await record(
        ctx,
        "money.temple_loot",
        roles={IncidentRole.ACTOR: looter.id, IncidentRole.VICTIM: temple.id},
        facts={"loads": added, "metal": metal},
        steps=(StepDraft(StepAction.PILLAGE, actor=looter.id, target=temple.id, amount=added, unit=FactUnit.COUNT),),
        place=temple.location_id,
    )
    return added


async def loot_temples(ctx: TickContext, place: EntityRow, looter: EntityRow) -> int:
    book = await MaterialBook.load(ctx.session)
    return sum([await loot_temple(ctx, temple, looter, book=book) for temple in await temples_in(ctx, place.id)])
