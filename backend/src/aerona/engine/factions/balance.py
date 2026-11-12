from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.read_memo import memoized
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.mind import ValueAxis
from aerona.engine.body.customs import culture_of
from aerona.engine.context import TickContext
from aerona.engine.faith.church import clergy_sway
from aerona.engine.polity.book import Realm
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.stats import stat


@memoized(FactionProfileRow, EntityRow)
async def canon_factions(session: AsyncSession) -> tuple[tuple[FactionProfileRow, EntityRow], ...]:
    statement = (
        select(FactionProfileRow, EntityRow).join(EntityRow, EntityRow.id == FactionProfileRow.faction_entity_id).where(EntityRow.status == EntityStatus.CANON)
    )
    return tuple((profile, faction) for profile, faction in await session.execute(statement))


async def power_balance(ctx: TickContext, realm: Realm) -> dict[int, int]:
    members = set(realm.members)
    shares: dict[int, int] = defaultdict(int)
    for profile, faction in await canon_factions(ctx.session):
        weight = profile.influence_over.get(str(realm.entity.id), 0)
        if profile.home_entity_id in members:
            weight += stat(faction, "sway") or 0
        if weight > 0 and not profile.outlawed:
            shares[faction.id] += weight
    clergy = await clergy_sway(ctx.session, ctx.rules, realm.entity.id)
    if clergy > 0 and realm.profile.state_religion_id is not None:
        shares[realm.profile.state_religion_id] += clergy
    return dict(shares)


async def faction_pull(ctx: TickContext, realm: Realm) -> dict[ValueAxis, int]:
    shares = await power_balance(ctx, realm)
    whole = sum(shares.values())
    if not whole:
        return {}
    pull: dict[ValueAxis, float] = defaultdict(float)
    for faction_id, share in shares.items():
        for axis, value in (await culture_of(ctx.session, faction_id)).items():
            pull[axis] += value * share / whole
    weight = ctx.rules.factions.balance_pct / PERCENT
    return {axis: round_half_up(value * weight) for axis, value in pull.items()}
