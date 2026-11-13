from types import MappingProxyType

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.structure_sections import FORMS, TALL_FORMS
from aerona.catalog.structures import STRUCTURES
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.structures import StructureDesignRow, StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.environment import CoastKind, TerrainKind
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.structure import STANDING_STATES, UNFINISHED_STATES, BuildingForm, BuildScale, StructureGroup, StructureKind
from aerona.engine.body.customs import people_of
from aerona.engine.collective.embodied import embody
from aerona.engine.context import TickContext
from aerona.engine.primitives.knowledge import known_levels
from aerona.engine.primitives.made_names import made_name
from aerona.engine.primitives.queries import living_entity

UPKEEP_MATERIALS: MappingProxyType[CommodityKind, MaterialKind] = MappingProxyType(
    {
        CommodityKind.STONE: MaterialKind.STONE,
        CommodityKind.TIMBER: MaterialKind.WOOD,
        CommodityKind.ORE: MaterialKind.IRON,
        CommodityKind.CLOTH: MaterialKind.CLOTH,
    }
)
FIXED_FORMS = frozenset({BuildingForm.WALL_LINE, BuildingForm.TUNNEL_FORM, BuildingForm.BRIDGE_FORM, BuildingForm.ORBITAL, BuildingForm.RING})
CARVED_GROUND = frozenset({TerrainKind.UNDERGROUND, TerrainKind.MOUNTAINS})
WATERSIDE_GROUPS = frozenset({StructureGroup.CIVIC, StructureGroup.COMMERCE, StructureGroup.PRODUCTION})
DWELLING_KINDS = frozenset({StructureKind.APARTMENT_BLOCK, StructureKind.HABITAT_RING, StructureKind.INN})
GREAT_SCALES = frozenset({BuildScale.GRAND, BuildScale.WONDER})
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
    form = form or await cultural_form(ctx, origin, kind)
    row = StructureDesignRow(
        world_id=world_id,
        name=name or await made_name(ctx.session, ctx.rules, origin, spec.label, kind.value, ctx.epoch),
        base_kind=kind,
        origin_node_id=origin.id if origin is not None else None,
        creator_son_id=son_id,
        form=form,
        storeys=storeys or SCALE_STOREYS[spec.scale] * (2 if form in TALL_FORMS else 1),
        material=material or UPKEEP_MATERIALS.get(spec.upkeep),
        created_epoch=ctx.epoch,
        retired=False,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await embody(ctx.session, row)
    return row


async def cultural_form(ctx: TickContext, origin: EntityRow | None, kind: StructureKind) -> BuildingForm:
    base = FORMS[kind]
    if origin is None or base in FIXED_FORMS:
        return base
    levels = (await known_levels(ctx.session, [origin.id])).get(origin.id, {})
    home = await ctx.session.get(RegionEnvironmentRow, origin.location_id or -1)
    table = ctx.rules.integrity
    group = STRUCTURES[kind].group
    level = levels.get
    ladder = (
        (group is StructureGroup.DEFENCE and level(KnowledgeBranch.WARFARE, 0) >= table.bunker_level, BuildingForm.BUNKER),
        (level(KnowledgeBranch.BIOMANCY, 0) >= table.grown_level, BuildingForm.GROWN),
        (home is not None and home.dominant_terrain in CARVED_GROUND, BuildingForm.CARVED),
        (
            home is not None
            and home.coast_kind is not CoastKind.NONE
            and group in WATERSIDE_GROUPS
            and level(KnowledgeBranch.SHIPBUILDING, 0) >= table.floating_level,
            BuildingForm.FLOATING,
        ),
        (kind in DWELLING_KINDS and level(KnowledgeBranch.ARCHITECTURE, 0) >= table.arcology_level, BuildingForm.ARCOLOGY),
        (
            base in {BuildingForm.TOWER, BuildingForm.HALL}
            and STRUCTURES[kind].scale in GREAT_SCALES
            and level(KnowledgeBranch.ARCHITECTURE, 0) >= table.high_rise_level,
            BuildingForm.HIGH_RISE,
        ),
        (base is BuildingForm.DOME and level(KnowledgeBranch.ARCHITECTURE, 0) >= table.geodesic_level, BuildingForm.GEODESIC),
        (group is StructureGroup.PRODUCTION and level(KnowledgeBranch.METALLURGY, 0) >= table.modular_level, BuildingForm.MODULAR),
    )
    return next((form for matched, form in ladder if matched), base)


async def builders_type(ctx: TickContext, builder: EntityRow | SonRow | None, site: EntityRow, kind: StructureKind) -> StructureDesignRow | None:
    maker = await maker_of(ctx.session, builder, site)
    found = await type_of(ctx.session, maker.id, kind)
    if found is not None or held(maker.id):
        return found
    return await draw_structure_type(ctx, maker, kind, world_id=site.world_id)


async def type_standing(ctx: TickContext) -> int:
    typed = 0
    profiles = await ctx.session.scalars(
        select(StructureProfileRow)
        .where(StructureProfileRow.design_id.is_(None), StructureProfileRow.construction_state.in_(list(STANDING_STATES | UNFINISHED_STATES)))
        .order_by(StructureProfileRow.structure_entity_id)
    )
    for profile in list(profiles):
        work = await living_entity(ctx.session, profile.structure_entity_id)
        site_id = profile.host_entity_id if profile.host_entity_id is not None else (work.location_id if work is not None else None)
        site = await living_entity(ctx.session, site_id) if site_id is not None else None
        if work is None or site is None or held(work.id) or "design_id" in (profile.locked or []):
            continue
        builder = await living_entity(ctx.session, profile.builder_entity_id) if profile.builder_entity_id is not None else None
        design = await builders_type(ctx, builder, site, profile.kind)
        if design is not None:
            profile.design_id = design.id
            typed += 1
    return typed
