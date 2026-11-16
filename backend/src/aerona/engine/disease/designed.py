from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.disease import DiseaseProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.engine.body.customs import people_of
from aerona.rules.registry import Rules


async def designed_aim(session: AsyncSession, rules: Rules, community: EntityRow, disease_id: int) -> float:
    profile = await session.get(DiseaseProfileRow, disease_id)
    if profile is None or profile.target_node_id is None:
        return 1.0
    table = rules.designed_disease
    folk = await people_of(session, community)
    aimed = profile.target_node_id in {community.id, community.affiliated_entity_id, folk.id if folk is not None else None}
    return (PERCENT + table.target_bonus_pct) / PERCENT if aimed else table.others_pct / PERCENT
