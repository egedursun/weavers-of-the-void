from sqlalchemy import select

from aerona.agents.context.cycle_lines import named
from aerona.agents.context.scope import Scope
from aerona.core.grammar import spoken
from aerona.db.tables.creature_groups import CreatureGroupRow
from aerona.db.tables.entities import EntityRow
from aerona.engine.primitives.distance import RegionAtlas


async def mortal_group_lines(scope: Scope, me: EntityRow) -> list[str]:
    region = (await RegionAtlas.load(scope.session)).top_region(me.id)
    if region is None:
        return []
    found: list[str] = []
    for group in await scope.session.scalars(select(CreatureGroupRow).where(CreatureGroupRow.region_entity_id == region).order_by(CreatureGroupRow.id)):
        leader = f", led by {await named(scope, group.leader_node_id)}" if group.leader_node_id is not None else ""
        aim = f", turned to {spoken(group.aim)}" if group.aim is not None and group.aim_until_epoch >= scope.epoch else ""
        found.append(
            f"group {group.id}: {await named(scope, group.species_entity_id)} as {spoken(group.form)} of {group.size}, hunger {group.hunger}{leader}{aim}"
        )
    return found
