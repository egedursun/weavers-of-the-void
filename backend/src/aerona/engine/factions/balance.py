from collections import defaultdict

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.mind import ValueAxis
from aerona.engine.body.customs import culture_of
from aerona.engine.context import TickContext
from aerona.engine.polity.book import Realm
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.stats import stat


async def power_balance(ctx: TickContext, realm: Realm) -> dict[int, int]:
    members = list(realm.members) or [-1]
    shares: dict[int, int] = defaultdict(int)
    statement = (
        select(FactionProfileRow, EntityRow).join(EntityRow, EntityRow.id == FactionProfileRow.faction_entity_id).where(EntityRow.status == EntityStatus.CANON)
    )
    for profile, faction in await ctx.session.execute(statement):
        weight = profile.influence_over.get(str(realm.entity.id), 0)
        if profile.home_entity_id in members:
            weight += stat(faction, "sway") or 0
        if weight > 0 and not profile.outlawed:
            shares[faction.id] += weight
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
