from collections.abc import Awaitable, Callable

from sqlalchemy import select

from aerona.agents.context.ages_lines import son_ages_lines
from aerona.agents.context.agrarian_lines import son_agrarian_lines
from aerona.agents.context.arts_lines import son_arts_lines
from aerona.agents.context.belonging_lines import son_belonging_lines
from aerona.agents.context.biology_lines import son_biology_lines
from aerona.agents.context.climes_lines import son_climes_lines
from aerona.agents.context.collective_lines import son_collective_lines
from aerona.agents.context.crafts_lines import son_crafts_lines
from aerona.agents.context.customs_lines import son_customs_lines
from aerona.agents.context.cycle_lines import son_cycle_lines
from aerona.agents.context.dominion_lines import dominion_lines
from aerona.agents.context.era_lines import son_era_lines
from aerona.agents.context.evolution_lines import son_evolution_lines
from aerona.agents.context.folkways_lines import son_folkways_lines
from aerona.agents.context.kinds_lines import son_kinds_lines
from aerona.agents.context.lifecycle_lines import son_fossil_lines, son_lifecycle_lines, son_world_end_lines
from aerona.agents.context.living_lines import son_living_lines
from aerona.agents.context.means_lines import son_economy_lines
from aerona.agents.context.minds_lines import son_minds_lines
from aerona.agents.context.mythic_lines import mythic_lines
from aerona.agents.context.nature_lines import son_nature_lines
from aerona.agents.context.operations_lines import son_operations_lines
from aerona.agents.context.powers_lines import son_power_lines
from aerona.agents.context.regime_lines import son_regime_lines
from aerona.agents.context.sacred_lines import son_sacred_lines
from aerona.agents.context.scope import Scope
from aerona.agents.context.sky_weather_lines import son_sky_lines, son_water_lines
from aerona.agents.context.tongue_lines import son_tongue_lines
from aerona.agents.context.world_view_lines import son_world_lines
from aerona.catalog.domain_effects import ACTIVITY_LABELS, DOMAIN_EFFECTS, HOOKS, SYNERGY_OF
from aerona.catalog.domains import DOMAIN_LABELS
from aerona.constants.units import PERCENT
from aerona.core.grammar import several
from aerona.db.tables.divine import AvatarRow, CouncilRulingRow, DivineStandingRow, DivineWoundRow, DomainActivityRow, GodGoalRow, WorldAttentionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.divine import GoalState
from aerona.engine.divine.goals import GOAL_LABELS
from aerona.engine.divine.rulings import MOTION_LABELS
from aerona.engine.divine.wounds import WOUND_LABELS


async def name_of(scope: Scope, node_id: int | None) -> str | None:
    node = await scope.session.get(NodeRow, node_id) if node_id is not None else None
    return node.name if node is not None else None


async def goal_lines(scope: Scope, son: SonRow) -> list[str]:
    rows = await scope.session.scalars(select(GodGoalRow).where(GodGoalRow.god_node_id == son.id, GodGoalRow.state == GoalState.ACTIVE).order_by(GodGoalRow.id))
    found = []
    for row in rows:
        target = await name_of(scope, row.target_node_id) or scope.world_name(row.world_id) or (DOMAIN_LABELS[row.domain] if row.domain else "")
        tail = f" ({target})" if target else ""
        found.append(f"Your aim: {GOAL_LABELS[row.kind].lower()}{tail}, {row.progress}% reached")
    found.append("Your plan is written about one of your aims" if found else "You hold no aim yet; take one, then write your plan about it")
    return found


async def hook_lines(son: SonRow, severed: set[str]) -> list[str]:
    found = []
    living = [domain for domain in son.domains if domain.value not in severed]
    for domain in living:
        hooks = ", ".join(HOOKS[hook].label.lower() for hook in DOMAIN_EFFECTS[domain].hooks)
        found.append(f"{DOMAIN_LABELS[domain]} gives your faithful: {hooks}; it feeds on {ACTIVITY_LABELS[DOMAIN_EFFECTS[domain].activity].lower()}")
    synergy = SYNERGY_OF.get(frozenset(living)) if len(living) > 1 else None
    if synergy is not None:
        found.append(f"Your two domains together: {synergy.label.lower()}")
    return found


SON_BLOCKS: tuple[Callable[[Scope, SonRow], Awaitable[list[str]]], ...] = (
    dominion_lines,
    mythic_lines,
    son_tongue_lines,
    son_evolution_lines,
    son_collective_lines,
    son_cycle_lines,
    son_regime_lines,
    son_agrarian_lines,
    son_operations_lines,
    son_sacred_lines,
    son_arts_lines,
    son_minds_lines,
    son_power_lines,
    son_living_lines,
    son_ages_lines,
    son_folkways_lines,
    son_customs_lines,
    son_crafts_lines,
    son_kinds_lines,
    son_climes_lines,
    son_sky_lines,
    son_water_lines,
    son_belonging_lines,
    son_era_lines,
    son_nature_lines,
    son_economy_lines,
    son_world_lines,
    son_biology_lines,
    son_lifecycle_lines,
    son_world_end_lines,
    son_fossil_lines,
)


async def divine_lines(scope: Scope, son: SonRow) -> list[str]:
    session = scope.session
    lines = await goal_lines(scope, son)
    wounds = list(await session.scalars(select(DivineWoundRow).where(DivineWoundRow.god_node_id == son.id, DivineWoundRow.healed < PERCENT)))
    severed = {row.domain.value for row in wounds if row.domain is not None}
    lines.extend(await hook_lines(son, severed))
    for row in wounds:
        tail = f" ({DOMAIN_LABELS[row.domain]})" if row.domain is not None else ""
        lines.append(f"Divine wound #{row.id}: {WOUND_LABELS[row.kind].lower()}{tail}, {row.healed}% healed")
    activity = list(
        await session.scalars(
            select(DomainActivityRow).where(DomainActivityRow.god_node_id == son.id, DomainActivityRow.epoch >= scope.epoch - 1).order_by(DomainActivityRow.id)
        )
    )
    if activity:
        parts = ", ".join(f"{DOMAIN_LABELS[row.domain]} {row.essence}" for row in activity[-len(son.domains) :])
        lines.append(f"Essence from your domains last age: {parts}")
    standings = list(await session.scalars(select(DivineStandingRow).where(DivineStandingRow.god_node_id == son.id).order_by(DivineStandingRow.neglect.desc())))
    for regard in standings[: scope.rules.context.son_standing_lines]:
        place = await session.get(EntityRow, regard.community_entity_id)
        if place is not None:
            lines.append(f"{place.name} regards you: awe {regard.awe}, love {regard.love}, fear {regard.fear}, neglect {regard.neglect}")
    for avatar in await session.scalars(select(AvatarRow).where(AvatarRow.god_node_id == son.id)):
        lines.append(f"Your mortal form #{several(avatar.avatar_entity_id, 'walk', 'walks')} the world")
    attention = await session.get(WorldAttentionRow, son.current_world_id) if son.current_world_id is not None else None
    if attention is not None and attention.attention < scope.rules.creator.far_eye_below:
        lines.append("Your world is far from the Creator's eye")
    for ruling in await session.scalars(select(CouncilRulingRow).where(CouncilRulingRow.active.is_(True)).order_by(CouncilRulingRow.id)):
        target = await name_of(scope, ruling.target_node_id)
        lines.append(f"Council ruling in force: {MOTION_LABELS[ruling.motion].lower()}{f' ({target})' if target else ''}")
    for more in SON_BLOCKS:
        lines.extend(await more(scope, son))
    return lines
