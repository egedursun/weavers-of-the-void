from collections.abc import Mapping
from enum import StrEnum

from fastapi import APIRouter, Path
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.industry import (
    WorksBottleneckView,
    WorksEnergyView,
    WorksLedgerView,
    WorksMethodView,
    WorksOptionView,
    WorksPolluterView,
    WorksPollutionView,
    WorksSiteView,
    WorksStockView,
    WorksStoresView,
    WorksView,
)
from aerona.api.schemas.mind import LabelView
from aerona.api.views.common import node_ref, node_refs
from aerona.catalog.commodities import COMMODITIES
from aerona.catalog.methods import ENERGY_LABELS, ENERGY_SOURCES, METHODS, PERISHABLE, PROCESS_LABELS, PROCESS_METHODS, TIER_LABELS, default_method
from aerona.catalog.ownership import OWNER_CLASS, OWNER_LABELS
from aerona.catalog.production import STEPS, WORKSHOP_LABELS
from aerona.core.errors import NotFoundError
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.culture import HolderTechniqueRow
from aerona.db.tables.economy import CommunityStockRow, ProductionRunRow, WorkshopRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.industry import CommunityIndustryRow, CommunityMethodRow, RegionPollutionRow
from aerona.db.tables.ownership import SiteProfitRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import SOCIETY_TYPES, EntityType
from aerona.domain.enums.environment import CoastKind, ScarKind
from aerona.domain.enums.industry import EnergyKind, OwnerClass, ProcessKind
from aerona.domain.enums.polity import LawKind
from aerona.engine.industry.methods import CELLAR_LEVEL, CELLARS, blocked_by
from aerona.engine.industry.quality import tier_of
from aerona.engine.polity.laws import LawBook
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.knowledge import known_levels
from aerona.rules.registry import Rules

router = APIRouter(tags=["industry"])
NO_NODE = "Nothing lives there."


def labels[K: StrEnum](table: Mapping[K, str]) -> list[LabelView]:
    return [LabelView(key=key.value, label=label) for key, label in table.items()]


async def method_views(session: AsyncSession, community: EntityRow, ground: RegionEnvironmentRow | None) -> list[WorksMethodView]:
    rows = {row.process: row for row in await session.scalars(select(CommunityMethodRow).where(CommunityMethodRow.community_node_id == community.id))}
    techniques = set(await session.scalars(select(HolderTechniqueRow.technique).where(HolderTechniqueRow.holder_entity_id == community.id)))
    levels = (await known_levels(session, [community.id])).get(community.id, {})
    energy = await session.get(CommunityIndustryRow, community.id)
    banned = (await LawBook.load(session)).in_force(community.id, LawKind.MAGIC_BAN) is not None
    stores = await session.scalars(select(WorkshopRow.level).where(WorkshopRow.community_entity_id == community.id, WorkshopRow.kind.in_(list(CELLARS))))
    cellar = any(level >= CELLAR_LEVEL for level in stores)
    views: list[WorksMethodView] = []
    for process in ProcessKind:
        row = rows.get(process)
        spec = METHODS[row.method] if row is not None else default_method(process)
        options = [
            WorksOptionView(
                method=option.kind,
                label=option.label,
                summary=option.summary,
                energy=option.energy,
                energy_need=option.energy_need,
                output_pct=option.output_pct,
                quality_bonus=option.quality_bonus,
                air=option.air,
                water=option.water,
                soil=option.soil,
                tool_wear=option.tool_wear,
                labour_pct=option.labour_pct,
                inputs=[
                    f"{units} {(material.value.replace('_', ' ') + ' ') if material is not None else ''}{COMMODITIES[commodity].label.lower()} per ten"
                    for commodity, units, material in option.inputs
                ],
                blocked=blocked_by(
                    option,
                    techniques=techniques,
                    levels=levels,
                    band=ground.temperature_band if ground is not None else None,
                    coastal=ground is not None and ground.coast_kind is not CoastKind.NONE,
                    supply=int(getattr(energy, option.energy.value)) if energy is not None else 0,
                    banned=banned,
                    cellar=cellar,
                ),
            )
            for option in PROCESS_METHODS[process]
        ]
        views.append(
            WorksMethodView(
                process=process,
                process_label=PROCESS_LABELS[process],
                method=spec.kind,
                label=spec.label,
                summary=spec.summary,
                chosen=row is not None,
                adopted_epoch=row.adopted_epoch if row is not None else None,
                displaced=row.displaced if row is not None else 0,
                held=row is not None and "method" in (row.locked or []),
                options=options,
            )
        )
    return views


def energy_views(row: CommunityIndustryRow | None) -> list[WorksEnergyView]:
    return [
        WorksEnergyView(
            kind=kind,
            label=ENERGY_LABELS[kind],
            source=ENERGY_SOURCES[kind],
            supply=int(getattr(row, kind.value)) if row is not None else 0,
            spent=row.spent.get(kind.value, 0) if row is not None else 0,
            short=row.short.get(kind.value, 0) if row is not None else 0,
            held=row is not None and kind.value in (row.locked or []),
        )
        for kind in EnergyKind
    ]


def stores_view(rules: Rules, row: CommunityIndustryRow | None) -> WorksStoresView | None:
    if row is None:
        return None
    tier = tier_of(rules, row.meal_quality)
    return WorksStoresView(
        heat_need=row.heat_need,
        tools_worn=row.tools_worn,
        spoiled=row.spoiled,
        preserved=row.preserved,
        meal_quality=row.meal_quality,
        meal_tier=tier,
        meal_tier_label=TIER_LABELS[tier],
        drink=row.drink,
        light=row.light,
        epoch=row.epoch,
        held=list(row.locked or []),
    )


async def stock_views(session: AsyncSession, rules: Rules, community_id: int) -> list[WorksStockView]:
    rows = await session.scalars(
        select(CommunityStockRow)
        .where(CommunityStockRow.community_entity_id == community_id, CommunityStockRow.quantity > 0)
        .order_by(CommunityStockRow.quality.desc(), CommunityStockRow.id)
    )
    views: list[WorksStockView] = []
    for row in rows:
        tier = tier_of(rules, row.quality)
        views.append(
            WorksStockView(
                id=row.id,
                commodity=row.commodity,
                label=COMMODITIES[row.commodity].label,
                material=row.material,
                world_material_id=row.world_material_id,
                quantity=row.quantity,
                quality=row.quality,
                tier=tier,
                tier_label=TIER_LABELS[tier],
                preserved=row.preserved,
                perishable=row.commodity in PERISHABLE,
                held=row.held,
            )
        )
    return views


async def regions_for(session: AsyncSession, node_id: int, entity: EntityRow | None) -> list[int]:
    if entity is not None and entity.entity_type is EntityType.REGION:
        return [entity.id]
    world = await session.get(WorldRow, node_id)
    if world is not None:
        return list(await session.scalars(select(RegionEnvironmentRow.entity_id).where(RegionEnvironmentRow.world_id == world.id)))
    worlds = list(await session.scalars(select(WorldRow.id).where(WorldRow.star_id == node_id)))
    if worlds:
        return list(await session.scalars(select(RegionEnvironmentRow.entity_id).where(RegionEnvironmentRow.world_id.in_(worlds))))
    if entity is None:
        return []
    top = (await RegionAtlas.load(session)).top_region(entity.id)
    return [top] if top is not None else []


async def pollution_views(session: AsyncSession, region_ids: list[int]) -> list[WorksPollutionView]:
    rows = {row.region_node_id: row for row in await session.scalars(select(RegionPollutionRow).where(RegionPollutionRow.region_node_id.in_(region_ids)))}
    grounds = {row.entity_id: row for row in await session.scalars(select(RegionEnvironmentRow).where(RegionEnvironmentRow.entity_id.in_(region_ids)))}
    polluters = [int(key) for row in rows.values() for key in (row.polluters or {})]
    refs = await node_refs(session, [*region_ids, *polluters])
    shown = region_ids if len(region_ids) == 1 else sorted(rows, key=lambda key: (-max(rows[key].air, rows[key].water, rows[key].soil), key))
    views: list[WorksPollutionView] = []
    for region_id in shown:
        row = rows.get(region_id)
        ground = grounds.get(region_id)
        views.append(
            WorksPollutionView(
                region=refs.get(region_id),
                air=row.air if row is not None else 0,
                water=row.water if row is not None else 0,
                soil=row.soil if row is not None else 0,
                blight=ground.scars.get(ScarKind.BLIGHTED.value, 0) if ground is not None else 0,
                epoch=row.epoch if row is not None else None,
                held=list(row.locked or []) if row is not None else [],
                polluters=[
                    WorksPolluterView(community=refs.get(int(key)), units=units)
                    for key, units in sorted((row.polluters or {}).items(), key=lambda item: (-item[1], item[0]))
                ]
                if row is not None
                else [],
            )
        )
    return views


async def last_profits(session: AsyncSession, workshop_ids: list[int], resource_ids: list[int]) -> dict[str, int]:
    found: dict[str, int] = {}
    rows = await session.scalars(
        select(SiteProfitRow)
        .where(or_(SiteProfitRow.workshop_id.in_(workshop_ids), SiteProfitRow.resource_node_id.in_(resource_ids)))
        .order_by(SiteProfitRow.epoch, SiteProfitRow.id)
    )
    for row in rows:
        key = f"workshop.{row.workshop_id}" if row.workshop_id is not None else f"resource.{row.resource_node_id}"
        found[key] = row.profit
    return found


async def site_views(session: AsyncSession, workshops: list[WorkshopRow], resources: list[tuple[int, int, int | None]]) -> list[WorksSiteView]:
    refs = await node_refs(
        session,
        [
            *(row.community_entity_id for row in workshops),
            *(row.owner_node_id for row in workshops if row.owner_node_id),
            *(item for resource in resources for item in resource if item),
        ],
    )
    profits = await last_profits(session, [row.id for row in workshops], [resource for resource, _, _ in resources])
    views = [
        WorksSiteView(
            workshop_id=row.id,
            kind=row.kind,
            resource=None,
            community=refs.get(row.community_entity_id),
            label=WORKSHOP_LABELS[row.kind],
            level=row.level,
            owner=refs.get(row.owner_node_id) if row.owner_node_id is not None else None,
            owner_class=OWNER_LABELS[OWNER_CLASS.get(row.kind, OwnerClass.COMMUNITY)],
            held=row.held,
            last_profit=profits.get(f"workshop.{row.id}"),
        )
        for row in workshops
    ]
    views.extend(
        WorksSiteView(
            workshop_id=None,
            kind=None,
            resource=refs.get(resource),
            community=refs.get(home) if home is not None else None,
            label=refs[resource].name if resource in refs else "A resource",
            level=1,
            owner=refs.get(owner),
            owner_class="Owned by bond",
            held=False,
            last_profit=profits.get(f"resource.{resource}"),
        )
        for resource, owner, home in resources
    )
    return views


async def owned_resources(session: AsyncSession, owner_id: int) -> list[tuple[int, int, int | None]]:
    bonds = await session.scalars(
        select(BondRow.target_node_id).where(BondRow.source_node_id == owner_id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE)
    )
    found: list[tuple[int, int, int | None]] = []
    for target in bonds:
        entity = await session.get(EntityRow, target)
        if entity is not None and entity.entity_type is EntityType.RESOURCE:
            found.append((target, owner_id, entity.location_id))
    return found


async def ledger_views(session: AsyncSession, node_id: int) -> list[WorksLedgerView]:
    rows = list(
        await session.scalars(
            select(SiteProfitRow)
            .where(or_(SiteProfitRow.owner_node_id == node_id, SiteProfitRow.community_node_id == node_id))
            .order_by(SiteProfitRow.epoch.desc(), SiteProfitRow.id.desc())
        )
    )
    refs = await node_refs(session, [item for row in rows for item in (row.owner_node_id, row.community_node_id) if item])
    return [
        WorksLedgerView(
            id=row.id,
            epoch=row.epoch,
            site=row.site.replace("_", " ").capitalize(),
            community=refs.get(row.community_node_id),
            owner=refs.get(row.owner_node_id) if row.owner_node_id is not None else None,
            revenue=row.revenue,
            inputs=row.inputs,
            wages=row.wages,
            upkeep=row.upkeep,
            taxes=row.taxes,
            profit=row.profit,
            invested=row.invested,
            held=list(row.locked or []),
        )
        for row in rows
    ]


async def bottleneck_views(session: AsyncSession, community_id: int) -> list[WorksBottleneckView]:
    latest = await session.scalar(select(func.max(ProductionRunRow.epoch)).where(ProductionRunRow.community_entity_id == community_id))
    if latest is None:
        return []
    rows = await session.scalars(
        select(ProductionRunRow)
        .where(ProductionRunRow.community_entity_id == community_id, ProductionRunRow.epoch == latest, ProductionRunRow.bottleneck.is_not(None))
        .order_by(ProductionRunRow.id)
    )
    return [
        WorksBottleneckView(
            step=STEPS[row.step].label if row.step in STEPS else row.step.replace("_", " "),
            workshop=WORKSHOP_LABELS[row.workshop] if row.workshop is not None else "Homes",
            missing=COMMODITIES[row.bottleneck].label if row.bottleneck is not None else "",
            epoch=row.epoch,
        )
        for row in rows
    ]


@router.get("/works/{node_id}", response_model=WorksView)
async def works_view(services: ServicesDep, node_id: int = Path(ge=1)) -> WorksView:
    async with reader(services) as session:
        ref = await node_ref(session, node_id)
        if ref is None:
            raise NotFoundError(NO_NODE)
        rules = services.rules.current
        entity = await session.get(EntityRow, node_id)
        community = entity is not None and entity.entity_type in SOCIETY_TYPES
        regions = await regions_for(session, node_id, entity)
        ground = await session.get(RegionEnvironmentRow, regions[0]) if regions and community else None
        industry = await session.get(CommunityIndustryRow, node_id) if community else None
        return WorksView(
            node_id=node_id,
            name=ref.name,
            community=community,
            methods=await method_views(session, entity, ground) if community and entity is not None else [],
            energy=energy_views(industry) if community else [],
            stores=stores_view(rules, industry),
            stocks=await stock_views(session, rules, node_id) if community else [],
            pollution=await pollution_views(session, regions),
            sites=await site_views(
                session, list(await session.scalars(select(WorkshopRow).where(WorkshopRow.community_entity_id == node_id).order_by(WorkshopRow.id))), []
            )
            if community
            else [],
            holdings=await site_views(
                session,
                list(await session.scalars(select(WorkshopRow).where(WorkshopRow.owner_node_id == node_id).order_by(WorkshopRow.id))),
                await owned_resources(session, node_id),
            ),
            ledger=await ledger_views(session, node_id),
            bottlenecks=await bottleneck_views(session, node_id) if community else [],
            workshop_kinds=labels(WORKSHOP_LABELS),
            tiers=labels(TIER_LABELS),
            processes=labels(PROCESS_LABELS),
        )
