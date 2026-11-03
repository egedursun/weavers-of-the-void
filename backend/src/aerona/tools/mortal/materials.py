from sqlalchemy import select

from aerona.db.tables.economy import CommunityStockRow, ResourceProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.domain.enums.economy import GoodsFlow
from aerona.domain.enums.material import MaterialKind
from aerona.engine.economy.materials import MaterialBook, MaterialProps, workable
from aerona.engine.economy.stocks import goods_of
from aerona.engine.primitives.knowledge import known_levels
from aerona.prompts.tools.results import MortalResult
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.validation import fail
from aerona.tools.mortal.support import home_of


async def held_lot(call: MortalCall, community: EntityRow | None, material: MaterialKind) -> CommunityStockRow | None:
    if community is None:
        return None
    statement = select(CommunityStockRow).where(
        CommunityStockRow.community_entity_id == community.id, CommunityStockRow.material == material, CommunityStockRow.quantity > 0
    )
    return await call.session.scalar(statement.order_by(CommunityStockRow.quality.desc(), CommunityStockRow.id).limit(1))


async def chosen_material(call: MortalCall, material: MaterialKind | None, resources: list[EntityRow]) -> MaterialProps | None:
    if material is None:
        return None
    props = (await MaterialBook.load(call.session)).props(call.me.world_id, material)
    if props is None:
        fail(MortalResult.MATERIAL_UNHELD, material=material.value.replace("_", " "))
    home = await home_of(call)
    community = home if home is not None else call.me
    levels = (await known_levels(call.session, [community.id, call.me.id])).get(community.id, {})
    region_id = (await call.atlas()).top_region(call.me.id)
    region = await call.session.get(RegionEnvironmentRow, region_id) if region_id is not None else None
    if not workable(call.rules, props, levels, region.magic_density if region is not None else 0):
        branch = props.gate or props.branch
        fail(MortalResult.MATERIAL_UNWORKABLE, material=props.label.lower(), branch=branch.value.replace("_", " ") if branch else "", level=max(1, props.level))
    for resource in resources:
        profile = await call.session.get(ResourceProfileRow, resource.id)
        if profile is not None and profile.material is material:
            return props
    lot = await held_lot(call, home, material)
    if lot is None:
        fail(MortalResult.MATERIAL_UNHELD, material=props.label.lower())
    await goods_of(call.session, call.epoch).take(lot.community_entity_id, lot.commodity, 1, GoodsFlow.TOOL, material=material)
    return props
