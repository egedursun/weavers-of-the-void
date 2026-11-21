from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.creature_groups import DriveMeans, GroupAim

DRIVE_MEANS = total(
    DriveMeans,
    {
        DriveMeans.HUNT: Defined("Hunt", checked_by=("tools.mortal.creature_groups.drive_off_group",), used_by=()),
        DriveMeans.FIRE: Defined("Fire", checked_by=("tools.mortal.creature_groups.drive_off_group",), used_by=()),
        DriveMeans.NOISE: Defined("Noise", checked_by=("tools.mortal.creature_groups.drive_off_group",), used_by=()),
        DriveMeans.OFFERING: Defined("Offering", checked_by=("tools.mortal.creature_groups.drive_off_group",), used_by=()),
    },
)

GROUP_AIM = total(
    GroupAim,
    {
        GroupAim.RAID: Defined("Raid", checked_by=(), used_by=("engine.creature_groups.groups.follow_range",)),
        GroupAim.WITHDRAW: Defined("Withdraw", checked_by=(), used_by=("engine.creature_groups.groups.roam",)),
        GroupAim.GUARD: Defined("Guard", checked_by=(), used_by=("engine.creature_groups.groups.raid", "tools.mortal.creature_groups.drive_off_group")),
        GroupAim.GROW: Defined("Grow", checked_by=(), used_by=("engine.creature_groups.groups.follow_range",)),
    },
)
