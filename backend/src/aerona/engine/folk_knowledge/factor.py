from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.read_memo import memoized
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.folk_knowledge import FolkKnowledgeRow
from aerona.domain.enums.folk_knowledge import FolkDomain
from aerona.engine.body.customs import people_id_of
from aerona.rules.registry import Rules

HALF = PERCENT // 2


@memoized(FolkKnowledgeRow)
async def accuracies(session: AsyncSession) -> dict[tuple[int, FolkDomain], int]:
    return {
        (people, domain): accuracy
        for people, domain, accuracy in await session.execute(
            select(FolkKnowledgeRow.people_entity_id, FolkKnowledgeRow.domain, FolkKnowledgeRow.accuracy).order_by(FolkKnowledgeRow.id)
        )
    }


async def folk_factor(session: AsyncSession, rules: Rules, entity: EntityRow | None, domain: FolkDomain) -> float:
    people = await people_id_of(session, entity)
    if people is None:
        return 1.0
    accuracy = (await accuracies(session)).get((people, domain))
    if accuracy is None:
        return 1.0
    return 1 + (accuracy - HALF) / PERCENT * rules.folk_knowledge.accuracy_success_pct / PERCENT
