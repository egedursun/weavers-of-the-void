from sqlalchemy import select

from aerona.agents.context.dominion_lines import dominion_lines
from aerona.agents.context.scope import Scope
from aerona.catalog.domain_effects import ACTIVITY_LABELS, DOMAIN_EFFECTS, HOOKS, SYNERGY_OF
from aerona.catalog.domains import DOMAIN_LABELS
from aerona.constants.units import PERCENT
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
        lines.append(f"Your mortal form #{avatar.avatar_entity_id} walks the world")
    attention = await session.get(WorldAttentionRow, son.current_world_id) if son.current_world_id is not None else None
    if attention is not None and attention.attention < scope.rules.creator.far_eye_below:
        lines.append("Your world is far from the Creator's eye")
    for ruling in await session.scalars(select(CouncilRulingRow).where(CouncilRulingRow.active.is_(True)).order_by(CouncilRulingRow.id)):
        target = await name_of(scope, ruling.target_node_id)
        lines.append(f"Council ruling in force: {MOTION_LABELS[ruling.motion].lower()}{f' ({target})' if target else ''}")
    lines.extend(await dominion_lines(scope, son))
    return lines
