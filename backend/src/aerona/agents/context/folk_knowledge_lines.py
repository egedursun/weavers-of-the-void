from sqlalchemy import select

from aerona.agents.context.scope import Scope
from aerona.core.grammar import spoken
from aerona.db.tables.crafts import NumberSystemRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.folk_knowledge import FolkClassRow, FolkKnowledgeRow
from aerona.engine.body.customs import people_of


async def mortal_folk_knowledge_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    folk = await people_of(session, me)
    if folk is None:
        return []
    found: list[str] = []
    classes: dict[str, list[str]] = {}
    for cls in await session.scalars(select(FolkClassRow).where(FolkClassRow.people_entity_id == folk.id).order_by(FolkClassRow.id)):
        classes.setdefault(cls.domain.value, []).append(f"{cls.name} (class {cls.id}) taken for {spoken(cls.taken_as)}")
    for row in await session.scalars(select(FolkKnowledgeRow).where(FolkKnowledgeRow.people_entity_id == folk.id).order_by(FolkKnowledgeRow.id)):
        named = classes.get(row.domain.value, [])
        found.append(
            f"of {spoken(row.domain)} your people know to depth {row.depth} and accuracy {row.accuracy} of 100, "
            f"held by {spoken(row.holders)} and passed on by {spoken(row.transmission)}" + (f"; they name {', '.join(named)}" if named else "")
        )
    system = await session.get(NumberSystemRow, folk.id)
    if system is not None and system.numerology:
        readings = ", ".join(f"{number} as {reading.replace('_', ' ')}" for number, reading in sorted(system.numerology.items(), key=lambda item: int(item[0])))
        found.append(f"your people read the numbers {readings}; each epoch is read by its number counted in base {system.base}")
    return found
