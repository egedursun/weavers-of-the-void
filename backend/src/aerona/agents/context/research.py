from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.civics import CAPABILITIES, TRIGGERS
from aerona.catalog.discovery import AGES, FIELDS, INCIDENTS
from aerona.catalog.techniques import TECHNIQUES
from aerona.core.total import total
from aerona.db.tables.culture import InstitutionRow, ResearchBoostRow, ResearchFocusRow
from aerona.db.tables.discovery import BlueprintRow, GreatPersonRow, PolityEraRow, ResearchIncidentRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.culture import ResearchChooser
from aerona.domain.enums.entity import EntityStatus
from aerona.engine.lore.learning import realm_of
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
        great_people=await great_lines(session, home.id),
        age=await age_line(session, home.id),
        incidents=[
            f"{INCIDENTS[row.kind].lower()} (age {row.epoch}{f', {row.dead} dead' if row.dead else ''})"
            for row in await session.scalars(
                select(ResearchIncidentRow)
                .where(ResearchIncidentRow.holder_entity_id == home.id)
                .order_by(ResearchIncidentRow.epoch.desc(), ResearchIncidentRow.id.desc())
                .limit(RECENT_BOOSTS)
            )
        ],
        designs=[row.name for row in await session.scalars(select(BlueprintRow).where(BlueprintRow.holder_node_id == home.id).order_by(BlueprintRow.id))],
    )


async def great_lines(session: AsyncSession, home_id: int) -> list[str]:
    rows = await session.execute(
        select(EntityRow.name, GreatPersonRow.field)
        .join(GreatPersonRow, GreatPersonRow.mortal_entity_id == EntityRow.id)
        .where(GreatPersonRow.holder_entity_id == home_id, EntityRow.status == EntityStatus.CANON)
        .order_by(GreatPersonRow.promoted_epoch)
    )
    return [f"{name} ({FIELDS[field].label.lower()})" for name, field in rows.all()]


async def age_line(session: AsyncSession, home_id: int) -> str:
    realm = await realm_of(session, home_id)
    row = await session.get(PolityEraRow, realm) if realm is not None else None
    return f"{AGES[row.age].lower()}, era score {row.score}" if row is not None else ""
