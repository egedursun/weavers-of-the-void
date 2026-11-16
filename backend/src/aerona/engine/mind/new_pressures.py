from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.industry import RegionPollutionRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow
from aerona.domain.enums.mind import PressureKind
from aerona.domain.enums.society import SocialClass
from aerona.engine.context import TickContext
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.society import class_shares


async def wider_pressures(ctx: TickContext, community: EntityRow, *, prosperity: int, impiety: int) -> dict[PressureKind, int]:
    table = ctx.rules.needs
    region_id = (await RegionAtlas.load(ctx.session)).top_region(community.id)
    fouled = await ctx.session.get(RegionPollutionRow, region_id) if region_id is not None else None
    land = await ctx.session.get(RegionEnvironmentRow, region_id) if region_id is not None else None
    shares = await class_shares(ctx.session, ctx.rules, community.id)
    realm = await ctx.session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == community.id).limit(1))
    rule = await ctx.session.get(PolityProfileRow, realm) if realm is not None else None
    return {
        PressureKind.POLLUTION: clamp_int(max(fouled.air, fouled.water, fouled.soil) if fouled is not None else 0, 0, PERCENT),
        PressureKind.UNEMPLOYMENT: clamp_int(shares.get(SocialClass.UNEMPLOYED, 0.0) * table.unemployment_pct / PERCENT, 0, PERCENT),
        PressureKind.OPPRESSION: clamp_int((PERCENT - rule.legitimacy) * table.oppression_pct / PERCENT if rule is not None else 0, 0, PERCENT),
        PressureKind.DISEASE_BURDEN: clamp_int(land.disease_load if land is not None else 0, 0, PERCENT),
        PressureKind.PURPOSELESSNESS: clamp_int(max(0, prosperity - table.purpose_prosperity) * impiety // PERCENT, 0, PERCENT),
    }
