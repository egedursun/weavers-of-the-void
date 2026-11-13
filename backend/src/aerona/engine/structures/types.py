from types import MappingProxyType

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.structure_sections import FORMS
from aerona.catalog.structures import STRUCTURES
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.structures import StructureDesignRow
from aerona.db.write_guard import held
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.structure import BuildingForm, BuildScale, StructureKind
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.primitives.made_names import made_name

UPKEEP_MATERIALS: MappingProxyType[CommodityKind, MaterialKind] = MappingProxyType(
    {
        CommodityKind.STONE: MaterialKind.STONE,
        CommodityKind.TIMBER: MaterialKind.WOOD,
        CommodityKind.ORE: MaterialKind.IRON,
        CommodityKind.CLOTH: MaterialKind.CLOTH,
    }
)
SCALE_STOREYS: MappingProxyType[BuildScale, int] = MappingProxyType({BuildScale.MINOR: 1, BuildScale.MAJOR: 2, BuildScale.GRAND: 3, BuildScale.WONDER: 5})


async def maker_of(session: AsyncSession, builder: EntityRow | SonRow | None, site: EntityRow) -> EntityRow:
    maker = builder if isinstance(builder, EntityRow) else site
    people = await people_of(session, maker)
    return people if people is not None else maker


async def type_of(session: AsyncSession, origin_id: int, kind: StructureKind) -> StructureDesignRow | None:
    statement = select(StructureDesignRow).where(
        StructureDesignRow.origin_node_id == origin_id, StructureDesignRow.base_kind == kind, StructureDesignRow.retired.is_(False)
    )
    return await session.scalar(statement.order_by(StructureDesignRow.id.desc()).limit(1))


async def draw_structure_type(
    ctx: TickContext,
    origin: EntityRow | None,
    kind: StructureKind,
    *,
    world_id: int | None,
    name: str | None = None,
    form: BuildingForm | None = None,
    storeys: int | None = None,
    material: MaterialKind | None = None,
    son_id: int | None = None,
) -> StructureDesignRow:
    spec = STRUCTURES[kind]
    row = StructureDesignRow(
        world_id=world_id,
        name=name or await made_name(ctx.session, ctx.rules, origin, spec.label, kind.value, ctx.epoch),
        base_kind=kind,
        origin_node_id=origin.id if origin is not None else None,
        creator_son_id=son_id,
        form=form or FORMS[kind],
        storeys=storeys or SCALE_STOREYS[spec.scale],
        material=material or UPKEEP_MATERIALS.get(spec.upkeep),
        created_epoch=ctx.epoch,
        retired=False,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def builders_type(ctx: TickContext, builder: EntityRow | SonRow | None, site: EntityRow, kind: StructureKind) -> StructureDesignRow | None:
    maker = await maker_of(ctx.session, builder, site)
    found = await type_of(ctx.session, maker.id, kind)
    if found is not None or held(maker.id):
        return found
    return await draw_structure_type(ctx, maker, kind, world_id=site.world_id)
