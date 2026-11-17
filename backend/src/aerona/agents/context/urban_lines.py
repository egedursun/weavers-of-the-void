from sqlalchemy import select

from aerona.agents.context.scope import Scope
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionMembershipRow
from aerona.db.tables.settlement import DistrictRow, SettlementProfileRow
from aerona.db.tables.urban import MarketPlayRow, OrderLawRow, PayrollRow, TradingPostRow, TurfRow


async def town_lines(scope: Scope, town_id: int) -> list[str]:
    session = scope.session
    found: list[str] = []
    profile = await session.get(SettlementProfileRow, town_id)
    districts = list(await session.scalars(select(DistrictRow).where(DistrictRow.settlement_entity_id == town_id).order_by(DistrictRow.id)))
    if profile is not None:
        homes = ", ".join(sorted({district.housing.value for district in districts}))
        found.append(f"your town grew {spoken(profile.morphology)}; its homes are {homes or 'none'}; {profile.homeless} are homeless")
    for turf in await session.scalars(
        select(TurfRow).where(TurfRow.district_id.in_([district.id for district in districts])).order_by(TurfRow.faction_entity_id)
    ):
        holder = await session.get(EntityRow, turf.faction_entity_id)
        if holder is not None:
            found.append(f"{holder.name} holds streets of your town ({turf.strength})")
    for post in await session.scalars(select(TradingPostRow).where(TradingPostRow.host_settlement_id == town_id)):
        owner = await session.get(EntityRow, post.owner_entity_id) if post.owner_entity_id is not None else None
        if owner is not None:
            found.append(f"{owner.name} keeps a trading post here")
    for play in await session.scalars(select(MarketPlayRow).where(MarketPlayRow.settlement_entity_id == town_id)):
        holder = await session.get(EntityRow, play.holder_entity_id)
        if holder is not None:
            found.append(f"{holder.name} {'corners' if play.play.value == 'corner' else 'floods'} the market in {spoken(play.commodity)}")
    return found


async def mortal_urban_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    found = await town_lines(scope, me.location_id) if me.location_id is not None else []
    for row in await session.scalars(select(PayrollRow).where(PayrollRow.official_entity_id == me.id)):
        payer = await session.get(EntityRow, row.faction_entity_id)
        if payer is not None:
            found.append(f"you take {row.bribe} coin a season from {payer.name}")
    for member in await session.scalars(select(FactionMembershipRow).where(FactionMembershipRow.mortal_entity_id == me.id)):
        laws = [
            row.law.value.replace("_", " ")
            for row in await session.scalars(select(OrderLawRow).where(OrderLawRow.faction_entity_id == member.faction_entity_id))
        ]
        if laws:
            order = await session.get(EntityRow, member.faction_entity_id)
            found.append(f"the laws of {order.name if order is not None else 'your order'}: {', '.join(laws)}")
    return found
