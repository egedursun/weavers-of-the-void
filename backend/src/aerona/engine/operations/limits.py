from sqlalchemy import select

from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.operations import AdmiraltyRow
from aerona.db.tables.polity import TreatyClauseRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.military import VesselStatus
from aerona.domain.enums.travel import VehicleKind
from aerona.domain.enums.vehicles import VehicleFrame
from aerona.engine.context import TickContext
from aerona.engine.polity.book import RealmBook
from aerona.engine.primitives.stats import stat_or

SUNK = frozenset({VesselStatus.WRECKED, VesselStatus.GHOST})
FRAME_NAMES = frozenset(item.value for item in VehicleFrame)
TEN_THOUSAND = 10_000


def tonnage_of(row: VesselProfileRow) -> int:
    return max(1, row.cargo_capacity + row.crew)


async def realm_people(ctx: TickContext, polity_id: int) -> int:
    owner = await ctx.session.get(EntityRow, polity_id)
    if owner is None:
        return 0
    if stat_or(owner, "population", 0) > 0:
        return stat_or(owner, "population", 0)
    realm = (await RealmBook.load(ctx.session)).realms.get(polity_id)
    members = sorted(realm.members) if realm is not None else []
    people = 0
    for member in members:
        item = await ctx.session.get(EntityRow, member)
        people += stat_or(item, "population", 0) if item is not None else 0
    return people


async def fleet_limit_of(ctx: TickContext, polity_id: int | None) -> int:
    table = ctx.rules.admiralty
    people = await realm_people(ctx, polity_id) if polity_id is not None else 0
    return max(table.fleet_limit, table.fleet_limit * people // TEN_THOUSAND)


async def cap_of(ctx: TickContext, clause: TreatyClauseRow) -> int:
    value = clause.params.get("tonnage", clause.params.get("amount"))
    return value if isinstance(value, int) and not isinstance(value, bool) else await fleet_limit_of(ctx, clause.obligor_node_id)


def frame_of(clause: TreatyClauseRow) -> VehicleFrame | None:
    value = clause.params.get("frame")
    return VehicleFrame(value) if isinstance(value, str) and value in FRAME_NAMES else None


async def owners_of(ctx: TickContext, polity_id: int) -> list[int]:
    realm = (await RealmBook.load(ctx.session)).realms.get(polity_id)
    return [polity_id, *sorted(realm.members)] if realm is not None else [polity_id]


async def fleet_of(ctx: TickContext, polity_id: int, frame: VehicleFrame | None = None) -> list[VesselProfileRow]:
    statement = (
        select(VesselProfileRow)
        .join(BondRow, BondRow.target_node_id == VesselProfileRow.entity_id)
        .where(
            BondRow.source_node_id.in_(await owners_of(ctx, polity_id)),
            BondRow.kind == BondKind.OWNS,
            BondRow.state == BondState.ACTIVE,
            VesselProfileRow.kind == VehicleKind.SHIP,
            VesselProfileRow.status.not_in(list(SUNK)),
        )
        .distinct()
        .order_by(VesselProfileRow.entity_id)
    )
    if frame is not None:
        statement = statement.where(VesselProfileRow.frame == frame)
    return list(await ctx.session.scalars(statement))


async def tonnage_under(ctx: TickContext, clause: TreatyClauseRow) -> int:
    if clause.obligor_node_id is None:
        return 0
    return sum(tonnage_of(ship) for ship in await fleet_of(ctx, clause.obligor_node_id, frame_of(clause)))


async def over_limit(ctx: TickContext, clause: TreatyClauseRow) -> bool:
    if clause.obligor_node_id is None:
        return False
    row = await ctx.session.get(AdmiraltyRow, clause.obligor_node_id)
    hidden = row.concealed if row is not None else 0
    return await tonnage_under(ctx, clause) - hidden > await cap_of(ctx, clause)
