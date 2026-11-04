from collections import Counter

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.happenings import EventCasualtyRow, EventFootprintRow, EventProfileRow
from aerona.domain.enums.happening import EventPhase

PHASE_WORDS = {EventPhase.ONSET: "beginning", EventPhase.PEAK: "at its height", EventPhase.AFTERMATH: "in its aftermath"}


async def event_phase_lines(session: AsyncSession, epoch: int) -> list[str]:
    profiles = list(
        await session.scalars(
            select(EventProfileRow)
            .where(or_(EventProfileRow.end_epoch.is_(None), EventProfileRow.end_epoch == epoch), EventProfileRow.start_epoch <= epoch)
            .where(or_(EventProfileRow.phase_epoch == epoch, EventProfileRow.phase != EventPhase.AFTERMATH, EventProfileRow.end_epoch == epoch))
            .order_by(EventProfileRow.entity_id)
        )
    )
    lines: list[str] = []
    for profile in profiles:
        event = await session.get(EntityRow, profile.entity_id)
        if event is None or event.engine_kind is None:
            continue
        tolls: Counter[str] = Counter()
        for row in await session.scalars(select(EventCasualtyRow).where(EventCasualtyRow.event_entity_id == event.id)):
            tolls[row.age_band.value] += row.count
        reach = len(list(await session.scalars(select(EventFootprintRow.region_entity_id).where(EventFootprintRow.event_entity_id == event.id))))
        state = "over this age" if profile.end_epoch == epoch else PHASE_WORDS[profile.phase]
        turned = " (turned this age)" if profile.phase_epoch == epoch and profile.start_epoch != epoch else ""
        dead = sum(tolls.values())
        toll = f"; {dead} dead ({', '.join(f'{band} {count}' for band, count in sorted(tolls.items()))})" if dead else ""
        where = f"; reaches {reach} lands" if reach > 1 else ""
        years = f" since the year {profile.start_year}" if profile.start_year is not None else ""
        lines.append(f"{event.name} ({event.engine_kind.value.replace('_', ' ')}{years}): {state}{turned}{toll}{where}")
    return lines
