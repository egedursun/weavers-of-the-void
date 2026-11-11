from sqlalchemy import select

from aerona.core.errors import ConflictError, NotFoundError
from aerona.core.random import SeededRandom
from aerona.db.tables.settlement import DistrictRow, SettlementInfrastructureRow, SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.settlement import DistrictKind
from aerona.domain.enums.urban import Morphology
from aerona.engine.context import TickContext
from aerona.engine.urban.layout import HEX_KEY, CityLayout, Hex, layout_of, plan_seed, seed_of, water_side
from aerona.rules.registry import Rules


def coastal(districts: list[DistrictRow]) -> bool:
    return any(district.kind is DistrictKind.HARBOUR for district in districts)


def seat_cell(rules: Rules, district: DistrictRow, districts: list[DistrictRow], morphology: Morphology, walls_level: int) -> Hex:
    seeded = [item for item in districts if item is not district and seed_of(item) is not None]
    town_id = district.settlement_entity_id
    return plan_seed(
        rules,
        layout_of(rules, seeded, walls_level),
        district.kind,
        morphology,
        rng=SeededRandom.for_epoch(town_id, 0, f"city.plan.{town_id}.{district.id}"),
        waterside=water_side(town_id, coastal(districts)),
    )


def seat(ctx: TickContext, district: DistrictRow, districts: list[DistrictRow], morphology: Morphology, walls_level: int) -> bool:
    if seed_of(district) is not None or HEX_KEY in district.locked:
        return False
    district.hex_q, district.hex_r = seat_cell(ctx.rules, district, districts, morphology, walls_level)
    return True


async def plan_town(ctx: TickContext, settlement_id: int) -> CityLayout:
    districts = list(await ctx.session.scalars(select(DistrictRow).where(DistrictRow.settlement_entity_id == settlement_id).order_by(DistrictRow.id)))
    profile = await ctx.session.get(SettlementProfileRow, settlement_id)
    infrastructure = await ctx.session.get(SettlementInfrastructureRow, settlement_id)
    morphology = profile.morphology if profile is not None else Morphology.ORGANIC
    walls = infrastructure.walls_level if infrastructure is not None else 0
    if not held(settlement_id):
        for district in districts:
            seat(ctx, district, districts, morphology, walls)
    return layout_of(ctx.rules, districts, walls)


async def move(ctx: TickContext, district_id: int, cell: Hex) -> DistrictRow:
    district = await ctx.session.get(DistrictRow, district_id)
    if district is None:
        raise NotFoundError("No such district.")
    others = await ctx.session.scalars(
        select(DistrictRow).where(DistrictRow.settlement_entity_id == district.settlement_entity_id, DistrictRow.id != district.id)
    )
    await plan_town(ctx, district.settlement_entity_id)
    if any(seed_of(other) == cell for other in others):
        raise ConflictError("Another district of the town already stands on that hex.")
    district.hex_q, district.hex_r = cell
    district.locked = sorted({*district.locked, HEX_KEY})
    await ctx.session.flush()
    return district
