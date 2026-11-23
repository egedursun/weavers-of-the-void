from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.demography import CohortRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.demography import CohortCondition
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.demography.cohorts import ORPHANS_KEY, CohortKey, displace, seed, settle_displaced, total
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.recording.record import record


async def shelter_displaced(ctx: TickContext, host: EntityRow, count: int) -> int:
    if count <= 0 or held(host.id):
        return 0
    rows = await seed(ctx.session, ctx.rules, host, ctx.epoch)
    placed = displace(ctx.session, host, rows, count, ctx.epoch)
    if placed > 0:
        await record(ctx, "demography.displaced", roles={IncidentRole.HOST: host.id}, facts={"displaced": placed})
    return placed


def share_of(rows: dict[CohortKey, CohortRow], condition: CohortCondition) -> float:
    whole = total(rows)
    return sum(row.count for key, row in rows.items() if key[3] is condition) / whole if whole else 0.0


async def press(session: AsyncSession, community: EntityRow, unrest: int) -> None:
    town = await session.get(SettlementProfileRow, community.id)
    if town is not None and unrest > 0 and "unrest" not in (town.locked or []):
        town.unrest = clamp_int(town.unrest + unrest, 0, PERCENT)


async def tend_conditions(ctx: TickContext, community: EntityRow, rows: dict[CohortKey, CohortRow]) -> None:
    table = ctx.rules.demography
    orphaned = ctx.session.info.get(ORPHANS_KEY, {}).pop(community.id, 0)
    if orphaned > 0:
        await record(ctx, "demography.orphans", roles={IncidentRole.PLACE: community.id}, facts={"orphans": orphaned})
    need = round_half_up(share_of(rows, CohortCondition.ORPHANED) * table.orphan_care_need)
    crowd = round_half_up(share_of(rows, CohortCondition.DISPLACED) * table.displaced_pressure)
    await press(ctx.session, community, need + crowd)
    settle_displaced(ctx.session, community, rows, table.displaced_settle_pct, ctx.epoch)
