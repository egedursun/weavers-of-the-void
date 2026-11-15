from sqlalchemy import select

from aerona.agents.context.cycle_lines import named, words
from aerona.agents.context.scope import Scope
from aerona.db.tables.ages import ArcFigureRow, ArcRow, IrregularSeasonRow, SetupRow, WinterForecastRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.ages import ArcOutcome, ArcStage, PayoffKind, SeasonSpell
from aerona.engine.body.customs import people_id_of
from aerona.engine.sacred.places import town_of

LIST_LINES = 3
STAGE_WORDS = {
    ArcStage.INCITING: "its beginning",
    ArcStage.RISING: "its rising",
    ArcStage.CRISIS: "its crisis",
    ArcStage.CLIMAX: "its climax",
    ArcStage.CALL: "the call",
    ArcStage.REFUSAL: "the refusal of the call",
    ArcStage.MENTOR: "the meeting with a mentor",
    ArcStage.THRESHOLD: "the crossing of the threshold",
    ArcStage.ORDEAL: "the ordeal",
    ArcStage.RETURN: "the return",
    ArcStage.RESOLUTION: "its end",
}


async def tale_lines(scope: Scope, node_id: int) -> list[str]:
    session = scope.session
    found: list[str] = []
    for arc in await session.scalars(
        select(ArcRow).where(ArcRow.subject_node_id == node_id, ArcRow.outcome == ArcOutcome.OPEN).order_by(ArcRow.id).limit(LIST_LINES)
    ):
        figures = list(await session.scalars(select(ArcFigureRow).where(ArcFigureRow.arc_id == arc.id).order_by(ArcFigureRow.node_id)))
        parts = [f"{await named(scope, figure.node_id)} as your {figure.role.value}" for figure in figures]
        cast = f", with {', '.join(parts)}" if parts else ""
        found.append(f"your life follows a tale of {words(arc.template.value)}, now at {STAGE_WORDS[arc.stage]}{cast}")
    for figure, arc in await session.execute(
        select(ArcFigureRow, ArcRow)
        .join(ArcRow, ArcRow.id == ArcFigureRow.arc_id)
        .where(ArcFigureRow.node_id == node_id, ArcRow.outcome == ArcOutcome.OPEN)
        .order_by(ArcRow.id)
        .limit(LIST_LINES)
    ):
        found.append(f"in the tale of {words(arc.template.value)} of {await named(scope, arc.subject_node_id)} your part is {figure.role.value}")
    return found


async def season_lines(scope: Scope, me: EntityRow) -> list[str]:
    if me.world_id is None:
        return []
    row = await scope.session.get(IrregularSeasonRow, me.world_id)
    if row is None:
        return []
    spell = "a long winter" if row.spell is SeasonSpell.WINTER else "a long summer"
    found = [f"the seasons of your world run irregular; {spell} holds since epoch {row.spell_started_epoch}"]
    folk = await people_id_of(scope.session, await town_of(scope.session, me))
    if folk is not None:
        forecast = await scope.session.scalar(
            select(WinterForecastRow).where(WinterForecastRow.world_id == me.world_id, WinterForecastRow.people_entity_id == folk)
        )
        if forecast is not None:
            heeded = "your people heeded it and stored food" if forecast.heeded else "your people paid it little mind"
            found.append(f"your people's scholars say it turns by epoch {forecast.predicted_end_epoch}; {heeded}")
    return found


async def mortal_ages_lines(scope: Scope, me: EntityRow) -> list[str]:
    return [*await tale_lines(scope, me.id), *await season_lines(scope, me)]


async def son_ages_lines(scope: Scope, son: SonRow) -> list[str]:
    session = scope.session
    found: list[str] = []
    if son.current_world_id is None:
        return found
    world = son.current_world_id
    row = await session.get(IrregularSeasonRow, world)
    if row is not None:
        spell = "a long winter" if row.spell is SeasonSpell.WINTER else "a long summer"
        found.append(f"the seasons of your world run irregular: {spell}, severity {row.severity}")
    subjects = select(EntityRow.id).where(EntityRow.world_id == world)
    for arc in await session.scalars(
        select(ArcRow).where(ArcRow.subject_node_id.in_(subjects), ArcRow.outcome == ArcOutcome.OPEN).order_by(ArcRow.drama.desc(), ArcRow.id).limit(LIST_LINES)
    ):
        subject = await named(scope, arc.subject_node_id)
        found.append(f"tale {arc.id}: {subject} follows a tale of {words(arc.template.value)} at {STAGE_WORDS[arc.stage]}, drama {arc.drama}")
    for setup in await session.scalars(
        select(SetupRow).where(SetupRow.subject_node_id.in_(subjects), SetupRow.payoff == PayoffKind.OPEN).order_by(SetupRow.id).limit(LIST_LINES)
    ):
        about = await named(scope, setup.subject_node_id) if setup.subject_node_id is not None else "no one"
        found.append(f"what was set up in epoch {setup.opened_epoch} ({setup.kind.value}) about {about} waits to be paid off")
    return found
