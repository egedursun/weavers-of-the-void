from sqlalchemy import select

from aerona.agents.context.cosmos_lines import cosmos_lines
from aerona.agents.context.entity_line import line_items
from aerona.agents.context.geography import geography_lines
from aerona.agents.context.language_lines import language_lines
from aerona.agents.context.location_tree import legends, location_tree
from aerona.agents.context.realm import realm_overview
from aerona.agents.context.recent_chronicle import recent_chronicle
from aerona.agents.context.scope import Scope
from aerona.agents.context.siblings import siblings
from aerona.agents.context.thread_lines import thread_lines
from aerona.agents.context.world_header import world_header
from aerona.agents.context.world_line import world_line
from aerona.catalog.domains import DOMAIN_LABELS
from aerona.db.tables.foreign_gods import ForeignGodPowerRow, ForeignGodRow
from aerona.db.tables.routes import RouteRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.foreign_god import ForeignGodStatus
from aerona.prompts import PromptId, render
from aerona.prompts.contexts.blocks import ForeignGodLine, RouteLine, SummarySection, WorldSummaryContext


async def foreign_god_lines(scope: Scope, world_id: int | None) -> list[ForeignGodLine]:
    if world_id is None:
        return []
    gods = list(
        await scope.session.scalars(
            select(ForeignGodRow)
            .where(ForeignGodRow.world_id == world_id, ForeignGodRow.status == ForeignGodStatus.AWAKE, ForeignGodRow.contacted.is_(True))
            .order_by(ForeignGodRow.id)
        )
    )
    lines = []
    for god in gods:
        powers = await scope.session.scalars(select(ForeignGodPowerRow.name).where(ForeignGodPowerRow.god_id == god.id).order_by(ForeignGodPowerRow.slot))
        domains = DOMAIN_LABELS[god.domain_primary] + (f"/{DOMAIN_LABELS[god.domain_secondary]}" if god.domain_secondary else "")
        lines.append(
            ForeignGodLine(
                id=god.id,
                name=god.name,
                title=god.title,
                domains=domains,
                power=god.power,
                attitude=god.stance,
                strength=god.strength,
                will=god.will,
                charisma=god.charisma,
                cunning=god.cunning,
                powers=list(powers),
            )
        )
    return lines


async def route_lines(scope: Scope) -> list[RouteLine]:
    routes = await scope.session.scalars(select(RouteRow).where(RouteRow.active.is_(True), RouteRow.known.is_(True)).order_by(RouteRow.id))
    return [
        RouteLine(
            id=route.id,
            world_a=scope.world_name(route.world_a_id),
            world_b=scope.world_name(route.world_b_id),
            method_label=route.method.value.replace("_", " "),
            duration=route.duration_epochs,
        )
        for route in routes
    ]


async def summary_header(scope: Scope, viewer: SonRow | None) -> str:
    if viewer is None:
        return await world_header(scope)
    world_id = viewer.current_world_id
    parts = [await world_header(scope, world_id), await world_line(scope, world_id)]
    return "\n".join(part for part in parts if part)


async def world_summary_context(scope: Scope, viewer: SonRow | None = None, section: SummarySection | None = None) -> WorldSummaryContext:
    context = scope.rules.context
    world_id = viewer.current_world_id if viewer is not None else None
    multiplier = context.read_tool_multiplier if section is not None else 1
    if viewer is not None:
        event_rows = (context.son_chronicle_lines + viewer.wisdom // context.son_chronicle_wisdom_step) * multiplier
        tree_rows = context.son_location_tree_lines + viewer.wisdom
    else:
        event_rows = context.fate_chronicle_lines * multiplier
        tree_rows = context.fate_location_tree_lines
    geography, total, cut = await location_tree(scope, world_id, tree_rows)
    legend_rows = await legends(scope, world_id, context.unlocated_rows)
    map_world = world_id if world_id is not None else scope.primary_world_id
    return WorldSummaryContext(
        rules=scope.rules,
        for_son=viewer is not None,
        section=section,
        header=await summary_header(scope, viewer),
        pantheon=await siblings(scope, viewer),
        threads=await thread_lines(scope, viewer),
        events=await recent_chronicle(scope, event_rows, world_id),
        multi_world=scope.multi_world,
        cosmos_lines=await cosmos_lines(scope, world_id),
        foreign_gods=await foreign_god_lines(scope, world_id) if viewer is not None else [],
        realms=await realm_overview(scope.session, world_id) if viewer is not None else [],
        routes=await route_lines(scope) if scope.multi_world else [],
        geography=geography,
        geography_total=total,
        geography_cut=cut,
        languages=await language_lines(scope, world_id, viewer),
        map=await geography_lines(scope, map_world),
        legends=await line_items(scope.session, legend_rows, with_location=False),
    )


async def world_summary(scope: Scope, viewer: SonRow | None = None, section: SummarySection | None = None) -> str:
    return render(PromptId.WORLD_SUMMARY, await world_summary_context(scope, viewer, section))
