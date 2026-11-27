from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.effect_packages import CURSE_PACKAGES, NEW_CURSE_KINDS
from aerona.db.fixups import fixup_due
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.culture import ItemProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.affliction import PackageKind, Transmission
from aerona.domain.enums.culture import CurseKind
from aerona.engine.body.afflictions import afflict
from aerona.engine.body.packages_w52 import Shape
from aerona.engine.context import TickContext
from aerona.engine.lore.items import owner_of
from aerona.engine.primitives.queries import living_entity

PACKAGES_FIXUP = "packages.w52"


async def curse_package(ctx: TickContext, item: EntityRow, bearer: EntityRow, curse: CurseKind, strength: int) -> None:
    package = CURSE_PACKAGES[curse]
    if package is None:
        return
    shape = Shape(fortune_sign=-1, fortune_strength=strength) if package is PackageKind.FORTUNE else None
    await afflict(ctx, bearer, package, Transmission.CURSE, source_node_id=item.id, shape=shape)


async def backfill_packages(ctx: TickContext, session: AsyncSession) -> int:
    if not await fixup_due(session, PACKAGES_FIXUP):
        return 0
    laid = 0
    rows = await session.scalars(select(ItemProfileRow).where(ItemProfileRow.curse.in_(NEW_CURSE_KINDS)).order_by(ItemProfileRow.item_entity_id))
    for row in list(rows):
        item = await living_entity(session, row.item_entity_id)
        owner = await owner_of(ctx, row.item_entity_id) if item is not None else None
        bearer = await living_entity(session, owner) if owner is not None else None
        if item is not None and bearer is not None:
            await curse_package(ctx, item, bearer, row.curse, 50)
            laid += 1
    session.add(AppliedFixupRow(key=PACKAGES_FIXUP, result={"afflictions": laid}))
    await session.flush()
    return laid
