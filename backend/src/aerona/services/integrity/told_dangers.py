from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.records import IncidentFactRow
from aerona.domain.enums.region import DangerSource, TerrainHazard

TOLD_FIXUP = "incidents.w52_dangers"
RETOLD = (("hazard", "hazard.struck", TerrainHazard), ("danger", "danger.harm", DangerSource))


async def retell_dangers(session: AsyncSession) -> int:
    if await session.get(AppliedFixupRow, TOLD_FIXUP) is not None:
        return 0
    changed = 0
    for family, kind, enum in RETOLD:
        old = {f"{family}.{value.value}": value for value in enum}
        for row in await session.scalars(select(IncidentRow).where(IncidentRow.kind.in_(sorted(old))).order_by(IncidentRow.id)):
            value = old[row.kind]
            row.kind = kind
            session.add(IncidentFactRow(incident_id=row.id, key=family if family == "hazard" else "source", enum_name=enum.__name__, enum_value=value.value))
            changed += 1
    session.add(AppliedFixupRow(key=TOLD_FIXUP, result={"incidents": changed}))
    await session.flush()
    return changed
