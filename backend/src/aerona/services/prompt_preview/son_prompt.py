from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.context.scope import load_scope
from aerona.agents.context.son_turn import son_system_context, son_user_context
from aerona.agents.context.world_summary import world_summary_context
from aerona.agents.grounding import grounded, world_ground
from aerona.agents.son import turn_points
from aerona.agents.turns.state import turn_row
from aerona.db.tables.sons import SonPowerRow
from aerona.prompts import PromptId, render
from aerona.rules.registry import Rules
from aerona.services.prompt_preview.blocks import estimate_tokens, require_son
from aerona.services.prompt_preview.models import SectionBudget, SonPromptPreview
from aerona.tools.framework.runtime import ToolCatalogue


def section_limits(rules: Rules) -> dict[str, int | None]:
    context = rules.context
    return {
        "header": None,
        "pantheon": None,
        "threads": None,
        "events": context.son_chronicle_chars,
        "cosmos": context.son_cosmos_chars,
        "geography": context.son_geography_chars,
        "languages": context.son_language_chars,
        "map": context.son_map_chars,
        "legends": context.son_unlocated_chars,
    }


async def preview_son_prompt(session: AsyncSession, rules: Rules, son_id: int, catalogue: ToolCatalogue) -> SonPromptPreview:
    son = await require_son(session, son_id)
    scope = await load_scope(session, rules)
    row = await turn_row(session, son.id)
    powers = list(await session.scalars(select(SonPowerRow).where(SonPowerRow.son_id == son.id)))
    resumed = row is not None and row.epoch == scope.epoch and not row.finished
    points = row.action_points_left if resumed and row is not None and row.action_points_left is not None else turn_points(rules, son, powers)
    system = grounded(await world_ground(session), render(PromptId.SON_TURN_SYSTEM, await son_system_context(scope, son, points, catalogue)))
    user_context = await son_user_context(scope, son, points, catalogue, resumed=resumed)
    user = render(PromptId.SON_TURN_USER, user_context)
    summary = await world_summary_context(scope, son)
    limits = section_limits(rules)
    raw = {
        "header": len(summary.header),
        "pantheon": len(summary.pantheon),
        "threads": len(summary.threads),
        "events": len(summary.events),
        "cosmos": len(summary.cosmos_lines),
        "geography": len(summary.geography),
        "languages": len(summary.languages),
        "map": len(summary.map),
        "legends": sum(len(item.name) for item in summary.legends),
    }
    total = len(system) + len(user)
    prompt_limit = rules.context.son_prompt_chars
    return SonPromptPreview(
        son_id=son.id,
        son_name=son.name,
        epoch=scope.epoch,
        action_points=points,
        system_prompt=system,
        user_prompt=user,
        system_characters=len(system),
        user_characters=len(user),
        total_characters=total,
        token_estimate=estimate_tokens(total),
        prompt_limit=prompt_limit,
        over_limit=total > prompt_limit,
        paid_tools=catalogue.paid,
        free_tools=catalogue.free,
        summary_sections=[SectionBudget(section=name, characters=count, limit=limits[name]) for name, count in raw.items()],
        summary_characters=len(user_context.world_summary),
        summary_limit=rules.context.son_summary_chars,
        memory_characters=len(user_context.memory),
        memory_limit=rules.context.son_memory_chars,
    )
