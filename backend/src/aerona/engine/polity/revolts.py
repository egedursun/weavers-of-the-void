from collections.abc import Mapping
from types import MappingProxyType

from sqlalchemy import select

from aerona.db.tables.military import WarAimRow
from aerona.db.tables.warfare import WarRow, WarSideRow
from aerona.domain.enums.military import WarAimKind
from aerona.domain.enums.polity import RevoltKind
from aerona.domain.enums.war import WarStatus
from aerona.engine.context import TickContext
from aerona.engine.military.aims import DEFENDER_AIMS, REGION_AIMS
from aerona.engine.primitives.distance import RegionAtlas

A = WarAimKind
REVOLT_AIMS: Mapping[RevoltKind, tuple[WarAimKind, ...]] = MappingProxyType(
    {
        RevoltKind.PEASANT: (A.LOOT, A.CHANGE_GOVERNMENT),
        RevoltKind.NOBLE: (A.CHANGE_GOVERNMENT, A.HUMILIATE),
        RevoltKind.RELIGIOUS: (A.CONVERT, A.CHANGE_GOVERNMENT),
        RevoltKind.SECESSION: (A.LIBERATE,),
        RevoltKind.SLAVE: (A.LIBERATE, A.LOOT),
    }
)


async def seed_aims(ctx: TickContext, attacker_id: int, defender_id: int, kinds: tuple[WarAimKind, ...]) -> int:
    war = await ctx.session.scalar(
        select(WarRow)
        .join(WarSideRow, WarSideRow.war_id == WarRow.id)
        .where(WarSideRow.entity_id == attacker_id, WarRow.status == WarStatus.ONGOING)
        .order_by(WarRow.id.desc())
        .limit(1)
    )
    if war is None or await ctx.session.scalar(select(WarAimRow.id).where(WarAimRow.war_id == war.id).limit(1)) is not None:
        return 0
    region = (await RegionAtlas.load(ctx.session)).top_region(defender_id)
    made = 0
    for side, enemy, wanted in ((attacker_id, defender_id, kinds), (defender_id, attacker_id, DEFENDER_AIMS)):
        for kind in wanted:
            target = region if kind in REGION_AIMS and side == attacker_id else enemy
            ctx.session.add(WarAimRow(war_id=war.id, side_entity_id=side, kind=kind, target_entity_id=target, params={}, achieved=0))
            made += 1
    return made
