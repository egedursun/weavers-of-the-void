from sqlalchemy import select

from aerona.agents.context.cycle_lines import named
from aerona.agents.context.scope import Scope
from aerona.catalog.genesis import TECHNOLOGY_LABELS
from aerona.catalog.techniques import TECHNIQUES
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.eras import TechProgrammeRow
from aerona.db.tables.sons import SonRow
from aerona.engine.cycles.book import realm_of
from aerona.engine.eras.effects import era_of, era_techniques, world_start
from aerona.engine.eras.progress import LIVE

LIST_LINES = 3


def programme_line(row: TechProgrammeRow, realm: str) -> str:
    label = TECHNIQUES[row.technique].label.lower()
    return f"{realm} runs a programme toward {label} (programme {row.id}, {spoken(row.stage)}, {row.progress} of 100)"


async def mortal_era_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    home = me.location_id
    era = era_of(await era_techniques(session, me.id), await world_start(session))
    found = [f"the technology of your people: {TECHNOLOGY_LABELS[era].lower()}"]
    realm = await realm_of(session, home) if home is not None else None
    if realm is not None:
        for row in await session.scalars(
            select(TechProgrammeRow)
            .where(TechProgrammeRow.polity_entity_id == realm, TechProgrammeRow.stage.in_(LIVE))
            .order_by(TechProgrammeRow.id)
            .limit(LIST_LINES)
        ):
            found.append(programme_line(row, "your realm"))
    return found


async def son_era_lines(scope: Scope, son: SonRow) -> list[str]:
    if son.current_world_id is None:
        return []
    realms = select(EntityRow.id).where(EntityRow.world_id == son.current_world_id)
    found = []
    for row in await scope.session.scalars(
        select(TechProgrammeRow)
        .where(TechProgrammeRow.polity_entity_id.in_(realms), TechProgrammeRow.stage.in_(LIVE))
        .order_by(TechProgrammeRow.progress.desc(), TechProgrammeRow.id)
        .limit(LIST_LINES)
    ):
        found.append(programme_line(row, await named(scope, row.polity_entity_id)))
    return found
