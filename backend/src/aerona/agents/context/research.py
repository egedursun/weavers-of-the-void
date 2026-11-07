from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.civics import CAPABILITIES, TRIGGERS
from aerona.catalog.techniques import TECHNIQUES
from aerona.core.total import total
from aerona.db.tables.culture import InstitutionRow, ResearchBoostRow, ResearchFocusRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.culture import ResearchChooser
from aerona.engine.lore.research_depth import capabilities_of, research_choices, research_home
from aerona.prompts.contexts.mortal import ResearchLine

RECENT_BOOSTS = 3
CHOOSERS = total(ResearchChooser, {ResearchChooser.SCHOLARS: "the scholars themselves", ResearchChooser.AGENT: "you", ResearchChooser.GOD: "a god"})


async def research_for(session: AsyncSession, me: EntityRow) -> ResearchLine | None:
    home = await research_home(session, me)
    if home is None:
        return None
    focus = await session.get(ResearchFocusRow, home.id)
    choices = await research_choices(session, home.id)
    if focus is None and not choices:
        return None
    founded = await session.scalars(select(InstitutionRow).where(InstitutionRow.community_entity_id == home.id).order_by(InstitutionRow.technique))
    boosts = await session.scalars(
        select(ResearchBoostRow)
        .where(ResearchBoostRow.holder_entity_id == home.id)
        .order_by(ResearchBoostRow.epoch.desc(), ResearchBoostRow.id.desc())
        .limit(RECENT_BOOSTS)
    )
    return ResearchLine(
        community=home.name,
        current=TECHNIQUES[focus.technique].label if focus is not None else "",
        chooser=CHOOSERS[focus.chooser] if focus is not None else "",
        choices=[f"{item.value} ({TECHNIQUES[item].label})" for item in choices],
        institutions=[f"{TECHNIQUES[row.technique].label} ({'embraced' if row.embraced else 'refused'})" for row in founded],
        boosts=[f"{TECHNIQUES[row.technique].label} +{row.progress}% from {TRIGGERS[row.trigger].label.lower()}" for row in boosts],
        capabilities=[CAPABILITIES[item].label for item in await capabilities_of(session, home.id)],
    )
