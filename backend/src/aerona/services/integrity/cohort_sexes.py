from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.reproduction import sex_shares
from aerona.db.tables.demography import CohortRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.engine.demography.cohorts import sex_spec
from aerona.engine.primitives.numbers import apportion
from aerona.rules.registry import Rules


async def stray_cohort_sexes(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for community_id in sorted(set(await session.scalars(select(CohortRow.community_entity_id)))):
        community = await session.get(EntityRow, community_id)
        if community is None or held(community_id):
            continue
        sexes = set((await sex_spec(session, community)).sexes)
        kinds = set(await session.scalars(select(CohortRow.sex_kind).where(CohortRow.community_entity_id == community_id, CohortRow.count > 0)))
        if kinds - sexes:
            found.append(community_id)
    return found


async def resplit_cohort_sexes(session: AsyncSession, key: int) -> None:
    community = await session.get(EntityRow, key)
    if community is None:
        return
    spec = await sex_spec(session, community)
    shares = sex_shares(spec, Rules().cohorts.bearer_pct)
    rows = {
        (row.age_band, row.sex_kind, row.social_class, row.condition): row
        for row in await session.scalars(select(CohortRow).where(CohortRow.community_entity_id == key))
    }
    for (age, sex, social_class, condition), row in sorted(rows.items(), key=lambda item: tuple(part.value for part in item[0])):
        if sex in spec.sexes or row.count <= 0:
            continue
        moved, row.count = row.count, 0
        for kind, part in apportion(moved, {kind: share for kind, share in shares.items() if share > 0}).items():
            target = rows.get((age, kind, social_class, condition))
            if target is None:
                target = CohortRow(
                    community_entity_id=key,
                    age_band=age,
                    sex_kind=kind,
                    social_class=social_class,
                    condition=condition,
                    count=0,
                    generation_epoch=row.generation_epoch,
                )
                session.add(target)
                rows[(age, kind, social_class, condition)] = target
            target.count += part
    await session.flush()
