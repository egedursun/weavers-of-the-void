from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.grammar import an, several
from aerona.db.tables.collective import AccountRow
from aerona.db.tables.couplings import SignOriginRow, SociolectRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.collective import AccountKind


async def register_lines(session: AsyncSession, me: EntityRow) -> list[str]:
    circle = [me.id, *[node for node in (me.location_id, me.affiliated_entity_id) if node is not None]]
    lines: list[str] = []
    for row, language in await session.execute(
        select(SociolectRow, EntityRow.name)
        .join(EntityRow, EntityRow.id == SociolectRow.language_entity_id)
        .where(SociolectRow.holder_entity_id.in_(circle), SociolectRow.faded_epoch.is_(None))
        .order_by(SociolectRow.id)
    ):
        secret = ", kept secret from outsiders" if row.secret else ""
        lines.append(f"{an(row.kind.value)} way of speaking {language}, prestige {row.prestige}{secret}")
    for name in await session.scalars(
        select(EntityRow.name).join(SignOriginRow, SignOriginRow.language_entity_id == EntityRow.id).where(SignOriginRow.community_entity_id.in_(circle))
    ):
        lines.append(f"the signed language {name}")
    remembered = await session.scalar(
        select(func.count()).select_from(AccountRow).where(AccountRow.holder_entity_id == me.id, AccountRow.kind == AccountKind.ELDER_MEMORY)
    )
    if remembered:
        lines.append(f"you remember {several(remembered, 'happening', 'happenings')} of your age as no one else does, and can teach or sell that memory")
    return lines
