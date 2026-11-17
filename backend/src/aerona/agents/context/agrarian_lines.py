from sqlalchemy import select

from aerona.agents.context.cycle_lines import named, words
from aerona.agents.context.scope import Scope
from aerona.core.grammar import an, spoken
from aerona.db.tables.agrarian import (
    BrandRow,
    CentralPlaceRow,
    CommonsRow,
    FamineLoreRow,
    GameReserveRow,
    IntensificationRow,
    KeystoneResourceRow,
    LandRingRow,
    PerennialRow,
    PreparednessRow,
    ReconstructionRow,
    SoilNutrientRow,
)
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.agrarian import NutrientKind
from aerona.domain.enums.entity import EntityType
from aerona.engine.body.customs import people_of
from aerona.engine.primitives.queries import top_region
from aerona.engine.primitives.records import definite

LIST_LINES = 3
SALTED_AT = 40


async def land_lines(scope: Scope, land: EntityRow) -> list[str]:
    session = scope.session
    found: list[str] = []
    ring = await session.get(LandRingRow, land.id)
    if ring is not None:
        market = f" around the market of {await named(scope, ring.market_entity_id)}" if ring.market_entity_id is not None else ""
        found.append(f"your land {land.name} lies in the {words(ring.ring.value)} ring{market}, gap between markets {ring.gap}")
    stocks = {row.nutrient: row.stock for row in await session.scalars(select(SoilNutrientRow).where(SoilNutrientRow.region_entity_id == land.id))}
    if stocks:
        found.append("its soil holds " + ", ".join(f"{words(kind.value)} {stocks[kind]}" for kind in NutrientKind if kind in stocks))
    pressed = await session.get(IntensificationRow, land.id)
    if pressed is not None and pressed.intensity > 0:
        found.append(f"its farmers work it at intensity {pressed.intensity} under a pressure of {pressed.pressure}% on the land")
    for common in await session.scalars(select(CommonsRow).where(CommonsRow.region_entity_id == land.id).order_by(CommonsRow.id).limit(LIST_LINES)):
        found.append(f"common {spoken(common.kind)} (commons {common.id}), {spoken(common.rule)}, condition {common.condition}")
    for reserve in await session.scalars(select(GameReserveRow).where(GameReserveRow.region_entity_id == land.id).order_by(GameReserveRow.id).limit(1)):
        found.append(
            f"its game is reserved by {await named(scope, reserve.holder_node_id)} (reserve {reserve.id}), "
            f"strictness {reserve.strictness}, poaching {reserve.poaching}"
        )
    return found


async def town_lines(scope: Scope, town: EntityRow) -> list[str]:
    session = scope.session
    found: list[str] = []
    place = await session.get(CentralPlaceRow, town.id)
    if place is not None:
        found.append(f"{town.name} is a central place of {spoken(place.rank)} goods, centrality {place.centrality}")
    works = list(await session.scalars(select(PreparednessRow).where(PreparednessRow.settlement_entity_id == town.id).order_by(PreparednessRow.kind)))
    if works:
        found.append(f"{town.name} stands ready with " + ", ".join(f"{words(work.kind.value)} level {work.level}" for work in works))
    rebuild = await session.scalar(
        select(ReconstructionRow).where(ReconstructionRow.settlement_entity_id == town.id, ReconstructionRow.finished_epoch.is_(None)).limit(1)
    )
    if rebuild is not None:
        found.append(f"{town.name} is rebuilding after {an(spoken(rebuild.cause))}, {spoken(rebuild.plan)}, {rebuild.progress}% done")
    return found


async def holding_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    found: list[str] = []
    for planting in await session.scalars(select(PerennialRow).where(PerennialRow.owner_node_id == me.id).order_by(PerennialRow.id).limit(LIST_LINES)):
        found.append(f"your {spoken(planting.kind)} in {await named(scope, planting.region_entity_id)} has grown {planting.maturity}%")
    for brand in await session.scalars(select(BrandRow).where(BrandRow.owner_node_id == me.id).order_by(BrandRow.id).limit(LIST_LINES)):
        found.append(f"you own the brand {definite(brand.name)}, reputation {brand.reputation}")
    people = await people_of(session, me)
    lore = await session.get(FamineLoreRow, people.id) if people is not None else None
    if lore is not None and lore.memory > 0:
        foods = "; they know their famine foods" if lore.famine_foods else ""
        found.append(f"your people remember hunger, memory {lore.memory}, storing food {lore.storage}{foods}")
    return found


async def keystone_line(scope: Scope, world_id: int | None) -> list[str]:
    if world_id is None:
        return []
    row = await scope.session.scalar(select(KeystoneResourceRow).where(KeystoneResourceRow.world_id == world_id).limit(1))
    if row is None:
        return []
    holder = f", held by {await named(scope, row.controller_entity_id)}" if row.controller_entity_id is not None else ""
    return [f"{definite(row.name)} from {await named(scope, row.source_region_entity_id)} is what this world depends on{holder}, supply {row.supply}"]


async def mortal_agrarian_lines(scope: Scope, me: EntityRow) -> list[str]:
    land = await top_region(scope.session, me)
    town = await scope.session.get(EntityRow, me.location_id) if me.location_id is not None else None
    found = await land_lines(scope, land) if land is not None else []
    if town is not None and town.entity_type is EntityType.SETTLEMENT:
        found.extend(await town_lines(scope, town))
    found.extend(await holding_lines(scope, me))
    found.extend(await keystone_line(scope, me.world_id))
    return found


async def son_agrarian_lines(scope: Scope, son: SonRow) -> list[str]:
    if son.current_world_id is None:
        return []
    session = scope.session
    found = await keystone_line(scope, son.current_world_id)
    for _, land in await session.execute(
        select(SoilNutrientRow, EntityRow)
        .join(EntityRow, EntityRow.id == SoilNutrientRow.region_entity_id)
        .where(EntityRow.world_id == son.current_world_id, SoilNutrientRow.nutrient == NutrientKind.SALINITY, SoilNutrientRow.stock >= SALTED_AT)
        .order_by(SoilNutrientRow.stock.desc(), SoilNutrientRow.region_entity_id)
        .limit(LIST_LINES)
    ):
        found.append(f"the fields of {land.name} (region {land.id}) are salting")
    for rebuild, town in await session.execute(
        select(ReconstructionRow, EntityRow)
        .join(EntityRow, EntityRow.id == ReconstructionRow.settlement_entity_id)
        .where(EntityRow.world_id == son.current_world_id, ReconstructionRow.finished_epoch.is_(None))
        .order_by(ReconstructionRow.id)
        .limit(LIST_LINES)
    ):
        found.append(f"{town.name} (settlement {town.id}) is rebuilding after {an(spoken(rebuild.cause))}")
    return found
