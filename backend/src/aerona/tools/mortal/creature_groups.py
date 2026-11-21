from typing import Any

from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.creature_groups import CreatureGroupRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.creature_groups import DriveMeans, GroupAim
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.creature_groups.groups import move_group
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail

HUNT_CUT = 20
APPEASED = 40


class DriveOffGroupInput(ToolInput):
    group_id: int
    means: DriveMeans


async def drive_off_group(call: MortalCall, args: DriveOffGroupInput) -> str:
    group = await call.session.get(CreatureGroupRow, args.group_id)
    atlas = await RegionAtlas.load(call.session)
    if group is None or atlas.top_region(call.me.id) != group.region_entity_id:
        fail(MortalResult.DRIVE_REFUSED, why="there is no such group in your land")
    if held(group.species_entity_id) or held(group.region_entity_id):
        fail(MortalResult.DRIVE_REFUSED, why="a god holds them unchanged")
    outcome = "they hold their ground"
    if args.means is DriveMeans.HUNT and "size" not in group.locked:
        group.size = group.size * (PERCENT - HUNT_CUT) // PERCENT
        outcome = "their numbers fall"
    elif args.means is DriveMeans.OFFERING and "hunger" not in group.locked:
        group.hunger = clamp_int(group.hunger - APPEASED, 0, PERCENT)
        group.aim, group.aim_until_epoch = GroupAim.GUARD, call.tick.epoch + call.rules.creature_groups.aim_epochs
        outcome = "they are appeased and leave your towns be"
    elif args.means in {DriveMeans.FIRE, DriveMeans.NOISE} and "region_entity_id" not in group.locked:
        options = [region for region in atlas.neighbours(group.region_entity_id) if not atlas.is_water(region) and not held(region)]
        if options:
            await move_group(call.tick, atlas, group, min(options))
            outcome = "they flee to the next land"
    call.target(group.species_entity_id)
    roles = {IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: group.species_entity_id}
    await call.record("beasts.group_driven", roles=roles, facts={"means": args.means})
    return result(MortalResult.GROUP_DRIVEN, means=spoken(args.means), outcome=outcome)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    return [
        ToolSpec(MortalToolId.DRIVE_OFF_GROUP, AgentKind.MORTAL, DriveOffGroupInput, ToolMeta(ActionKind.INFLUENCE, mortal_standard_action), drive_off_group)
    ]
