from sqlalchemy import select

from aerona.catalog.means import BUILDING, WATER_WORKS
from aerona.constants.units import PERCENT
from aerona.db.tables.economy import NodeMaterialRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.economy import MaterialSlot
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.integrity import HarmForce
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.structure import STANDING_STATES
from aerona.engine.context import TickContext
from aerona.engine.eras.effects import era_techniques
from aerona.engine.means.strength import fire_loss
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.structures.damage import harm
from aerona.engine.structures.profiles import material_props


async def body_of(ctx: TickContext, structure_id: int) -> MaterialKind | None:
    row = await ctx.session.get(NodeMaterialRow, (structure_id, MaterialSlot.BODY))
    return row.material if row is not None else None


async def damp_at(ctx: TickContext, work: EntityRow, profile: StructureProfileRow) -> int:
    if profile.kind in WATER_WORKS:
        return PERCENT
    atlas = await RegionAtlas.load(ctx.session)
    region = atlas.top_region(work.id)
    ground = await ctx.session.get(RegionEnvironmentRow, region) if region is not None else None
    return ground.moisture if ground is not None else PERCENT // 2


async def weathering(ctx: TickContext, work: EntityRow, profile: StructureProfileRow) -> float:
    kind = await body_of(ctx, work.id)
    spec = BUILDING.get(kind) if kind is not None else None
    if spec is None:
        return 1.0
    damp = await damp_at(ctx, work, profile)
    return 1 + damp * (PERCENT - spec.water) * ctx.rules.building_materials.weathering_pct / PERCENT / PERCENT / PERCENT


async def can_repair(ctx: TickContext, work: EntityRow, profile: StructureProfileRow) -> bool:
    kind = await body_of(ctx, work.id)
    spec = BUILDING.get(kind) if kind is not None else None
    if spec is None or spec.needs is None:
        return True
    return spec.needs in await era_techniques(ctx.session, profile.host_entity_id or work.id)


async def burn_structures(ctx: TickContext, town: EntityRow, gale: float) -> int:
    burned = 0
    rows = await ctx.session.execute(
        select(EntityRow, StructureProfileRow)
        .join(StructureProfileRow, StructureProfileRow.structure_entity_id == EntityRow.id)
        .where(
            StructureProfileRow.host_entity_id == town.id,
            EntityRow.status == EntityStatus.CANON,
            StructureProfileRow.construction_state.in_(list(STANDING_STATES)),
        )
        .order_by(EntityRow.id)
    )
    for work, profile in rows.all():
        if held(work.id):
            continue
        loss = fire_loss(ctx.rules, await material_props(ctx.session, work), gale)
        if loss > 0:
            await harm(ctx, work, profile, loss, cause="the great fire", force=HarmForce.FIRE, quiet=True)
            burned += 1
    return burned
